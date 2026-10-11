"""Provisional installer primitives for the PoC (Track B).

PROVISIONAL: a fixture-level prototype to validate D3 primitives.
It is NOT the final D3/P6a installer contract and NOT a production installer.

Stdlib only. Frontmatter is parsed line-wise for scalar fields only
(a documented PoC simplification; formal frontmatter handling is P4/P6a).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from typing import Optional

MARK_BEGIN = "<!-- BEGIN {block_id} -->"
MARK_END = "<!-- END {block_id} -->"


class InstallerError(Exception):
    pass


class CrashSimulated(InstallerError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def parse_frontmatter(text: str) -> dict:
    """Minimal scalar frontmatter parser (PoC). Handles 'key: value' scalars only."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k.strip()] = v.strip()
    return out


def render_frontmatter(fm: dict, body: str) -> str:
    lines = ["---"]
    for k in sorted(fm.keys()):
        lines.append(f"{k}: {fm[k]}")
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
        return entry["desired"].encode()
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
        b = MARK_BEGIN.format(block_id=entry.get("blockId", "pi-pipeline-setup"))
        e = MARK_END.format(block_id=entry.get("blockId", "pi-pipeline-setup"))
        if b in text and e in text:
            return text.split(b, 1)[1].split(e, 1)[0].strip("\n").encode()
        return b""
    if kind == "frontmatter-fields":
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fm = parse_frontmatter(text)
        keys = sorted(entry["desired"].keys())
        return canonical_json({k: fm[k] for k in keys if k in fm})
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
        block_id = entry.get("blockId", "pi-pipeline-setup")
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
        fm = parse_frontmatter(text)
        fm.update(entry["desired"])
        body = text[text.find("\n---", 3) + 4:] if text.startswith("---") and "\n---" in text[3:] else text
        return render_frontmatter(fm, body)
    raise InstallerError(f"unknown ownership type: {kind!r}")


def detect_unsafe_path(entry: dict, target_root: str) -> Optional[str]:
    """Return a reason string if the managed path (or any existing ancestor) is unsafe."""
    rel = os.path.normpath(entry["path"])
    if rel.startswith("..") or os.path.isabs(rel):
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
        valid_ownership = ("whole-file", "json-keys", "marked-block", "frontmatter-fields")
        for e in self.entries:
            if not isinstance(e.get("path"), str) or not e.get("path"):
                raise InstallerError("manifest entry missing 'path'")
            if e.get("ownership") not in valid_ownership:
                raise InstallerError(f"unknown ownership type: {e.get('ownership')!r}")
            if "desired" not in e:
                raise InstallerError(f"manifest entry missing 'desired': {e.get('path')!r}")
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

        txid = f"tx-{os.getpid()}-{len(os.listdir(self.journal_dir)) if os.path.isdir(self.journal_dir) else 0}"
        self._append_journal(txid, {"op": "transaction-start", "txid": txid})
        # back up the applied-state file so recovery can revert it too
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
            staged = os.path.join(self.staging_dir, txid, e["path"].replace("/", "__"))
            os.makedirs(os.path.dirname(staged), exist_ok=True)
            with open(staged, "w", encoding="utf-8") as f:
                f.write(rendered)
            step()

            # 2. backup current target (if exists)
            backup = None
            if os.path.exists(path):
                backup = os.path.join(self.backup_dir, txid, e["path"].replace("/", "__"))
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.copy2(path, backup)
            step()

            # 3. write-ahead journal intent (BEFORE mutating the target)
            self._append_journal(txid, {"op": "entry", "path": e["path"],
                                        "backup": backup, "created": backup is None})
            step()

            # 4. write target from staging
            os.makedirs(os.path.dirname(path), exist_ok=True)
            shutil.copy2(staged, path)
            step()

        # 5. commit state (fixed last)
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
            # revert applied-state file first
            sb = next((r for r in records if r.get("op") == "state-backup"), None)
            if sb:
                if sb.get("existed") and sb.get("backup") and os.path.exists(sb["backup"]):
                    os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
                    shutil.copy2(sb["backup"], self.state_path)
                elif not sb.get("existed"):
                    if os.path.exists(self.state_path):
                        os.remove(self.state_path)
            for r in reversed([r for r in records if r.get("op") == "entry"]):
                target = os.path.join(self.target_root, r["path"])
                if r.get("backup") and os.path.exists(r["backup"]):
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy2(r["backup"], target)
                elif r.get("created"):
                    if os.path.exists(target):
                        os.remove(target)
            with open(os.path.join(self.journal_dir, name), "a", encoding="utf-8") as f:
                f.write(json.dumps({"op": "rolled-back"}) + "\n")
            return {"ok": True, "recovered": True, "txid": records[0].get("txid")}
        return {"ok": True, "recovered": False, "reason": "no unfinished transaction"}
