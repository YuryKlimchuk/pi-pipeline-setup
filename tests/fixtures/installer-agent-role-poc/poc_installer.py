"""Provisional installer primitives for the PoC (Track B).

PROVISIONAL: a fixture-level prototype to validate D3 primitives.
It is NOT the final D3/P6a installer contract and NOT a production installer.

Stdlib only. Frontmatter is parsed conservatively for scalar fields only
(a documented PoC simplification; formal frontmatter handling is P4/P6a).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from typing import Optional, Tuple

MARK_BEGIN = "<!-- BEGIN {block_id} -->"
MARK_END = "<!-- END {block_id} -->"
VALID_OWNERSHIP = ("whole-file", "json-keys", "marked-block", "frontmatter-fields")


class InstallerError(Exception):
    pass


class CrashSimulated(InstallerError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def parse_frontmatter(text: str) -> Tuple[dict, str, bool]:
    """Conservative frontmatter parser.

    Returns (fields, body, has_valid_frontmatter). Only treats a document as
    frontmatter-bearing when line 0 is exactly `---` and a later line is exactly
    `---`. Otherwise the whole text is returned as body (nothing is discarded),
    which avoids misreading Markdown horizontal rules (`---`) as frontmatter.
    """
    if not text.startswith("---"):
        return {}, text, False
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, False
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return {}, text, False
    fields = {}
    for line in lines[1:close]:
        line = line.rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ": " in line:
            k, v = line.split(": ", 1)
            fields[k.strip()] = v.strip()
    body = "\n".join(lines[close + 1:])
    return fields, body, True


def render_frontmatter(fields: dict, body: str) -> str:
    lines = ["---"]
    for k in sorted(fields.keys()):
        lines.append(f"{k}: {fields[k]}")
    lines.append("---")
    text = "\n".join(lines) + "\n"
    if body.strip():
        text += "\n" + body.lstrip("\n")
    return text


def desired_canonical(entry: dict) -> bytes:
    kind = entry["ownership"]
    if kind == "whole-file":
        return entry["desired"].encode()
    if kind in ("json-keys", "frontmatter-fields"):
        return canonical_json(entry["desired"])
    if kind == "marked-block":
        return entry["desired"].strip().encode()
    raise InstallerError(f"unknown ownership type: {kind!r}")


def current_canonical(entry: dict, target_root: str) -> Optional[bytes]:
    """Canonical bytes of the managed part currently on disk (None if target absent)."""
    path = os.path.join(target_root, entry["path"])
    if not os.path.exists(path):
        return None
    kind = entry["ownership"]
    if kind == "whole-file":
        with open(path, "rb") as f:
            return f.read()
    if kind == "json-keys":
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        keys = sorted(entry["desired"].keys())
        return canonical_json({k: doc[k] for k in keys if k in doc})
    if kind == "marked-block":
        with open(path, encoding="utf-8") as f:
            text = f.read()
        b = MARK_BEGIN.format(block_id=entry["blockId"])
        e = MARK_END.format(block_id=entry["blockId"])
        if b in text and e in text:
            return text.split(b, 1)[1].split(e, 1)[0].strip().encode()
        return b""
    if kind == "frontmatter-fields":
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fields, _body, has_valid = parse_frontmatter(text)
        if not has_valid:
            return canonical_json({})
        keys = sorted(entry["desired"].keys())
        return canonical_json({k: fields[k] for k in keys if k in fields})
    raise InstallerError(f"unknown ownership type: {kind!r}")


def render(entry: dict, target_root: str) -> str:
    """Return the full new text of the managed file (preserving unmanaged parts)."""
    path = os.path.join(target_root, entry["path"])
    kind = entry["ownership"]
    if kind == "whole-file":
        return entry["desired"]
    if kind == "json-keys":
        doc = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        doc.update(entry["desired"])
        return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if kind == "marked-block":
        block_id = entry["blockId"]
        b = MARK_BEGIN.format(block_id=block_id)
        e = MARK_END.format(block_id=block_id)
        text = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                text = f.read()
        block = f"{b}\n{entry['desired']}\n{e}\n"
        if b in text and e in text:
            return text.split(b, 1)[0] + block + text.split(e, 1)[1]
        return (text.rstrip("\n") + "\n\n" if text.strip() else "") + block
    if kind == "frontmatter-fields":
        text = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                text = f.read()
        fields, body, has_valid = parse_frontmatter(text)
        merged = dict(fields)
        merged.update(entry["desired"])
        if has_valid:
            return render_frontmatter(merged, body)
        # no valid frontmatter: prepend, preserve the entire original text as body
        return render_frontmatter(merged, text)
    raise InstallerError(f"unknown ownership type: {kind!r}")


def detect_unsafe_path(entry: dict, target_root: str) -> Optional[str]:
    """Return a reason string if the managed path (or any existing ancestor) is unsafe."""
    rel = os.path.normpath(entry["path"])
    if os.path.isabs(rel) or rel == ".." or rel.startswith(".." + os.sep):
        return "path escapes target root"
    cur = target_root
    for part in rel.split(os.sep):
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            return f"symlink in managed path: {part}"
        if os.path.exists(cur) and not os.path.isdir(cur):
            if os.lstat(cur).st_nlink > 1:
                return f"hardlink in managed path: {part}"
    return None


class Installer:
    def __init__(self, manifest: dict, target_root: str):
        self.target_root = target_root
        self.manifest = manifest
        self.state_path = os.path.join(target_root, ".pi/blueprint/state.json")
        self.journal_dir = os.path.join(target_root, ".pi/blueprint/journal")
        self.backup_dir = os.path.join(target_root, ".pi/blueprint/backups")
        self.staging_dir = os.path.join(target_root, ".pi/blueprint/staging")
        self.entries = manifest.get("entries", [])
        for e in self.entries:
            if not isinstance(e.get("path"), str) or not e.get("path"):
                raise InstallerError("manifest entry missing 'path'")
            if e.get("ownership") not in VALID_OWNERSHIP:
                raise InstallerError(f"unknown ownership type: {e.get('ownership')!r}")
            if "desired" not in e:
                raise InstallerError(f"manifest entry missing 'desired': {e.get('path')!r}")
            kind = e["ownership"]
            desired = e["desired"]
            if kind in ("whole-file", "marked-block"):
                if not isinstance(desired, str):
                    raise InstallerError(f"{kind} entry 'desired' must be a string: {e['path']!r}")
            else:
                if not isinstance(desired, dict):
                    raise InstallerError(f"{kind} entry 'desired' must be an object: {e['path']!r}")
                if kind == "frontmatter-fields":
                    for k, v in desired.items():
                        if not isinstance(k, str) or not isinstance(v, str):
                            raise InstallerError(f"frontmatter-fields keys/values must be strings: {e['path']!r}")
            if kind == "marked-block":
                if not isinstance(e.get("blockId"), str) or not e.get("blockId"):
                    raise InstallerError(f"marked-block entry missing 'blockId': {e['path']!r}")
            if not isinstance(e.get("sha256"), str) or len(e.get("sha256", "")) != 64:
                raise InstallerError(f"manifest entry missing/invalid 'sha256': {e['path']!r}")
            if e["sha256"].lower() != sha256(desired_canonical(e)):
                raise InstallerError(f"manifest sha256 mismatch for {e['path']!r}")
        paths = [e["path"] for e in self.entries]
        if len(paths) != len(set(paths)):
            raise InstallerError("duplicate managed path in manifest (collision)")

    def load_state(self) -> dict:
        if os.path.exists(self.state_path):
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        return {"entries": {}, "last_transaction": None}

    def _journal_path(self, txid: str) -> str:
        return os.path.join(self.journal_dir, f"{txid}.jsonl")

    def _append_journal(self, txid: str, record: dict) -> None:
        os.makedirs(self.journal_dir, exist_ok=True)
        with open(self._journal_path(txid), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def plan(self) -> list:
        state = self.load_state()
        steps = []
        for e in self.entries:
            reason = detect_unsafe_path(e, self.target_root)
            if reason:
                steps.append({"action": "reject", "path": e["path"], "reason": reason})
                continue
            d = desired_canonical(e)
            dhash = sha256(d)
            cur = current_canonical(e, self.target_root)
            last = state["entries"].get(e["path"])
            if cur is None:
                steps.append({"action": "create", "path": e["path"], "hash": dhash})
            elif sha256(cur) == dhash:
                steps.append({"action": "noop", "path": e["path"], "hash": dhash})
            elif last is not None and sha256(cur) == last:
                steps.append({"action": "update", "path": e["path"], "hash": dhash})
            else:
                steps.append({"action": "conflict", "path": e["path"],
                              "reason": "managed content changed by user (drift)"})
        return steps

    def apply(self, crash_after: Optional[int] = None) -> dict:
        if self.has_unfinished_transaction():
            return {"ok": False, "error": "unfinished transaction; run recover() first"}
        state = self.load_state()
        steps = self.plan()
        rejects = [s for s in steps if s["action"] == "reject"]
        conflicts = [s for s in steps if s["action"] == "conflict"]
        if rejects:
            return {"ok": False, "error": "rejected", "rejects": rejects}
        if conflicts:
            return {"ok": False, "error": "conflict", "conflicts": conflicts}

        actionable = [s for s in steps if s["action"] in ("create", "update")]
        if not actionable:
            return {"ok": True, "applied": [], "txid": None}

        txid = f"tx-{uuid.uuid4().hex}"
        self._append_journal(txid, {"op": "transaction-start", "txid": txid})
        state_backup = None
        state_existed = os.path.exists(self.state_path)
        if state_existed:
            state_backup = os.path.join(self.backup_dir, txid, "state.json.bak")
            os.makedirs(os.path.dirname(state_backup), exist_ok=True)
            shutil.copy2(self.state_path, state_backup)
        self._append_journal(txid, {"op": "state-backup", "existed": state_existed, "backup": state_backup})
        ops = 0

        def step():
            nonlocal ops
            ops += 1
            if crash_after is not None and ops > crash_after:
                raise CrashSimulated(f"simulated crash after {ops} operations")

        for s in actionable:
            e = next(e for e in self.entries if e["path"] == s["path"])
            path = os.path.join(self.target_root, e["path"])

            # 1. stage rendered content
            rendered = render(e, self.target_root)
            post_hash = sha256(rendered.encode())
            staged = os.path.join(self.staging_dir, txid, e["path"].replace("/", "__"))
            os.makedirs(os.path.dirname(staged), exist_ok=True)
            with open(staged, "w", encoding="utf-8") as f:
                f.write(rendered)
            step()

            # 2. re-validate safety immediately before backup (TOCTOU)
            reason = detect_unsafe_path(e, self.target_root)
            if reason:
                raise InstallerError(f"unsafe path before backup: {reason}")

            # 3. backup current target (if exists)
            backup = None
            if os.path.exists(path):
                backup = os.path.join(self.backup_dir, txid, e["path"].replace("/", "__"))
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.copy2(path, backup)
            step()

            # 4. re-validate safety immediately before target mutation (TOCTOU)
            reason = detect_unsafe_path(e, self.target_root)
            if reason:
                raise InstallerError(f"unsafe path before write: {reason}")

            # 5. write-ahead journal intent (BEFORE mutating the target)
            self._append_journal(txid, {"op": "entry", "path": e["path"],
                                        "backup": backup, "created": backup is None,
                                        "post_hash": post_hash})
            step()

            # 6. write target from staging
            os.makedirs(os.path.dirname(path), exist_ok=True)
            shutil.copy2(staged, path)
            step()

        # commit state (fixed last)
        new_entries = dict(state["entries"])
        for s in actionable:
            new_entries[s["path"]] = s["hash"]
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump({"entries": new_entries, "last_transaction": txid}, f, indent=2)
            f.write("\n")
        step()
        self._append_journal(txid, {"op": "transaction-complete", "txid": txid})
        return {"ok": True, "txid": txid, "applied": [s["path"] for s in actionable]}

    def has_unfinished_transaction(self) -> bool:
        if not os.path.isdir(self.journal_dir):
            return False
        for name in os.listdir(self.journal_dir):
            records = self._read_journal(name)
            if records and records[0].get("op") == "transaction-start":
                done = any(r.get("op") in ("transaction-complete", "rolled-back") for r in records)
                if not done:
                    return True
        return False

    def _read_journal(self, name: str) -> list:
        path = os.path.join(self.journal_dir, name)
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def recover(self) -> dict:
        if not os.path.isdir(self.journal_dir):
            return {"ok": True, "recovered": False, "reason": "no journal"}
        for name in sorted(os.listdir(self.journal_dir)):
            records = self._read_journal(name)
            if not records or records[0].get("op") != "transaction-start":
                continue
            if any(r.get("op") in ("transaction-complete", "rolled-back") for r in records):
                continue
            entries = [r for r in records if r.get("op") == "entry"]
            # First detect post-crash user changes (atomic all-or-nothing rollback).
            conflicts = []
            rollback = []  # (action, target, record)
            for r in entries:
                target = os.path.join(self.target_root, r["path"])
                cur = None
                if os.path.exists(target):
                    with open(target, "rb") as f:
                        cur = sha256(f.read())
                post = r.get("post_hash")
                if r.get("created"):
                    if cur is None:
                        continue  # never written
                    if cur == post:
                        rollback.append(("remove", target, r))
                    else:
                        conflicts.append(r["path"])
                else:
                    backup = r.get("backup")
                    bhash = None
                    if backup and os.path.exists(backup):
                        with open(backup, "rb") as f:
                            bhash = sha256(f.read())
                    if cur is None:
                        conflicts.append(r["path"])
                    elif cur == post:
                        rollback.append(("restore", target, r))
                    elif bhash is not None and cur == bhash:
                        continue  # already original
                    else:
                        conflicts.append(r["path"])
            if conflicts:
                return {"ok": False, "error": "conflict", "conflicts": conflicts,
                        "reason": "post-crash changes detected; recovery stopped to preserve user edits"}
            # revert applied-state file
            sb = next((r for r in records if r.get("op") == "state-backup"), None)
            if sb:
                if sb.get("existed") and sb.get("backup") and os.path.exists(sb["backup"]):
                    os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
                    shutil.copy2(sb["backup"], self.state_path)
                elif not sb.get("existed"):
                    if os.path.exists(self.state_path):
                        os.remove(self.state_path)
            # perform rollback (reverse order)
            for action, target, r in reversed(rollback):
                if action == "remove":
                    if os.path.exists(target):
                        os.remove(target)
                else:
                    backup = r.get("backup")
                    if backup and os.path.exists(backup):
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        shutil.copy2(backup, target)
            with open(os.path.join(self.journal_dir, name), "a", encoding="utf-8") as f:
                f.write(json.dumps({"op": "rolled-back"}) + "\n")
            return {"ok": True, "recovered": True, "txid": records[0].get("txid")}
        return {"ok": True, "recovered": False, "reason": "no unfinished transaction"}
