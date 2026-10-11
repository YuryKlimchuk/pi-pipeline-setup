"""Offline tests for the provisional installer primitives (PoC Track B).

Covers authorized tasks 0.2, 3.1–3.10 plus regression tests for the
independently confirmed findings H1, H2, M1, M2, M3, L1, L2, L3, L4.
Stdlib unittest; no dependencies installed; writes only inside a temp disposable root.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poc_installer as pi
from poc_installer import CrashSimulated, Installer, InstallerError, sha256


def mk_entry(path, ownership, desired, block_id=None):
    e = {"path": path, "ownership": ownership, "desired": desired}
    if block_id is not None:
        e["blockId"] = block_id
    e["sha256"] = sha256(pi.desired_canonical(e))
    return e


def make_manifest():
    entries = [
        mk_entry("config/app.json", "json-keys",
                 {"defaultProvider": "example", "defaultModel": "example/model:1"}),
        mk_entry("AGENTS.md", "marked-block",
                 "# Managed block\nRead docs/workflow.md before changes.", "pi-pipeline-setup"),
        mk_entry(".pi/agents/developer.md", "frontmatter-fields", {"model": "example/dev:1"}),
        mk_entry("rules/README.md", "whole-file", "Synthetic rule file.\n"),
    ]
    return {"schemaVersion": 1, "provisional": True, "entries": entries}


def collect_baseline(root: str) -> dict:
    out = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            with open(p, "rb") as f:
                data = f.read()
            out[rel] = {"size": len(data), "sha256": sha256(data)}
    return out


SECRET_MARKERS = ("api_key", "apikey", "sk-", "-----BEGIN", "Bearer ", "password")


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pi-poc-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def inst(self, manifest=None):
        return Installer(manifest or make_manifest(), self.root)


# --------------------------------------------------------------------------
# authorized tasks
# --------------------------------------------------------------------------

class TestBaseline(Base):  # 0.2
    def test_baseline_collection_no_secrets(self):
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        with open(os.path.join(self.root, "config", "app.json"), "w") as f:
            json.dump({"name": "fixture"}, f)
        baseline = collect_baseline(self.root)
        self.assertIn("config/app.json", baseline)
        blob = json.dumps(baseline).lower()
        for marker in SECRET_MARKERS:
            self.assertNotIn(marker, blob)


class TestManifest(Base):  # 3.1
    def test_manifest_has_ownership_and_hashes(self):
        m = make_manifest()
        self.assertEqual({"json-keys", "marked-block", "frontmatter-fields", "whole-file"},
                         {e["ownership"] for e in m["entries"]})
        for e in m["entries"]:
            self.assertEqual(e["sha256"], sha256(pi.desired_canonical(e)))

    def test_duplicate_path_collision(self):
        m = make_manifest()
        m["entries"].append(dict(m["entries"][0]))
        with self.assertRaises(InstallerError):
            Installer(m, self.root)


class TestPlanAndApply(Base):  # 3.2, 3.3
    def test_plan_is_read_only(self):
        before = collect_baseline(self.root)
        self.inst().plan()
        after = collect_baseline(self.root)
        self.assertEqual(before, after)

    def test_apply_creates_all_files(self):
        r = self.inst().apply()
        self.assertTrue(r["ok"], r)
        self.assertTrue(os.path.exists(os.path.join(self.root, "config", "app.json")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "AGENTS.md")))
        self.assertTrue(os.path.exists(os.path.join(self.root, ".pi/agents/developer.md")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "rules/README.md")))
        with open(os.path.join(self.root, ".pi/blueprint/state.json")) as f:
            state = json.load(f)
        self.assertEqual(4, len(state["entries"]))

    def test_reconciliation_noop_update_conflict(self):
        inst = self.inst()
        self.assertTrue(inst.apply()["ok"])
        steps = inst.plan()
        self.assertTrue(all(s["action"] == "noop" for s in steps), steps)
        m = make_manifest()
        for e in m["entries"]:
            if e["path"] == "rules/README.md":
                e["desired"] = "Synthetic rule file (v2).\n"
                e["sha256"] = sha256(pi.desired_canonical(e))
        inst2 = Installer(m, self.root)
        acts = {s["path"]: s["action"] for s in inst2.plan()}
        self.assertEqual("update", acts["rules/README.md"], acts)
        self.assertEqual("noop", acts["config/app.json"], acts)
        with open(os.path.join(self.root, "rules/README.md"), "w") as f:
            f.write("user changed this\n")
        acts = {s["path"]: s["action"] for s in inst2.plan()}
        self.assertEqual("conflict", acts["rules/README.md"], acts)

    def test_json_keys_preserves_unknown_keys(self):
        self.inst().apply()
        with open(os.path.join(self.root, "config", "app.json")) as f:
            doc = json.load(f)
        doc["userKey"] = "keep-me"
        with open(os.path.join(self.root, "config", "app.json"), "w") as f:
            json.dump(doc, f)
        m = make_manifest()
        for e in m["entries"]:
            if e["path"] == "config/app.json":
                e["desired"] = {"defaultProvider": "example2", "defaultModel": "example/model:2"}
                e["sha256"] = sha256(pi.desired_canonical(e))
        Installer(m, self.root).apply()
        with open(os.path.join(self.root, "config", "app.json")) as f:
            doc2 = json.load(f)
        self.assertEqual("keep-me", doc2["userKey"])
        self.assertEqual("example2", doc2["defaultProvider"])


class TestIdempotency(Base):  # 3.4
    def test_repeat_apply_noop_no_duplicate_block(self):
        inst = self.inst()
        self.assertTrue(inst.apply()["ok"])
        self.assertTrue(inst.apply()["ok"])
        with open(os.path.join(self.root, "AGENTS.md")) as f:
            text = f.read()
        self.assertEqual(1, text.count("<!-- BEGIN pi-pipeline-setup -->"))


class TestCrashRecovery(Base):  # 3.5
    def test_crash_between_each_step_recovers(self):
        entry = mk_entry("rules/README.md", "whole-file", "v1\n")
        m = {"schemaVersion": 1, "provisional": True, "entries": [entry]}
        crash_points = 0
        for crash in range(12):
            root2 = tempfile.mkdtemp(prefix="pi-crash-")
            try:
                inst = Installer(m, root2)
                try:
                    inst.apply(crash_after=crash)
                    break  # no crash => all crash points exhausted
                except CrashSimulated:
                    crash_points += 1
                self.assertTrue(inst.has_unfinished_transaction())
                self.assertTrue(inst.recover()["recovered"])
                self.assertFalse(inst.has_unfinished_transaction())
                self.assertFalse(os.path.exists(os.path.join(root2, "rules", "README.md")))
            finally:
                shutil.rmtree(root2, ignore_errors=True)
        self.assertGreaterEqual(crash_points, 4)


class TestDrift(Base):  # 3.6
    def test_drift_preserves_user_change(self):
        inst = self.inst()
        inst.apply()
        p = os.path.join(self.root, "rules/README.md")
        with open(p, "w") as f:
            f.write("user edit\n")
        acts = {s["path"]: s["action"] for s in inst.plan()}
        self.assertEqual("conflict", acts["rules/README.md"])
        r = inst.apply()
        self.assertFalse(r["ok"])
        self.assertEqual("conflict", r["error"])
        with open(p) as f:
            self.assertEqual("user edit\n", f.read())


class TestPartialCompletion(Base):  # 3.7
    def test_unfinished_transaction_blocks_until_recover(self):
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("rules/README.md", "whole-file", "x\n")]}
        inst = Installer(m, self.root)
        try:
            inst.apply(crash_after=2)
        except CrashSimulated:
            pass
        self.assertTrue(inst.has_unfinished_transaction())
        r = inst.apply()
        self.assertFalse(r["ok"])
        self.assertEqual("unfinished transaction; run recover() first", r["error"])
        self.assertTrue(inst.recover()["recovered"])
        self.assertFalse(inst.has_unfinished_transaction())
        self.assertTrue(inst.apply()["ok"])


class TestSymlinkHardlink(Base):  # 3.8, 3.2
    def test_symlink_escape_rejected(self):
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        outside = tempfile.mktemp()
        os.symlink(outside, os.path.join(self.root, "config", "app.json"))
        s = next(s for s in self.inst().plan() if s["path"] == "config/app.json")
        self.assertEqual("reject", s["action"])
        self.assertIn("symlink", s["reason"])

    def test_hardlink_rejected(self):
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        a = os.path.join(self.root, "config", "app.json")
        b = os.path.join(self.root, "config", "other.json")
        with open(a, "w") as f:
            f.write("{}")
        os.link(a, b)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("config/other.json", "json-keys", {})]}
        steps = Installer(m, self.root).plan()
        self.assertEqual("reject", steps[0]["action"])
        self.assertIn("hardlink", steps[0]["reason"])


class TestPermission(Base):  # 3.9
    def test_permission_failure_no_partial_apply(self):
        ro = os.path.join(self.root, "readonly")
        os.makedirs(ro)
        os.chmod(ro, 0o555)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("readonly/new.txt", "whole-file", "x\n")]}
        inst = Installer(m, self.root)
        with self.assertRaises(PermissionError):
            inst.apply()
        self.assertFalse(os.path.exists(os.path.join(self.root, "readonly", "new.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".pi/blueprint/state.json")))
        os.chmod(ro, 0o755)


class TestNegatives(Base):  # 3.10
    def test_no_git_works(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, ".git")))
        self.assertTrue(self.inst().apply()["ok"])

    def test_corrupt_manifest(self):
        with self.assertRaises(InstallerError):
            Installer({"entries": [{"path": "x", "ownership": "bogus", "desired": "x"}]}, self.root)
        with self.assertRaises(InstallerError):
            Installer({"entries": [{"path": "a"}, {"path": "a"}]}, self.root)


# --------------------------------------------------------------------------
# regression tests for confirmed findings
# --------------------------------------------------------------------------

class TestH1MarkedBlockConvergence(Base):
    def test_marked_block_trailing_newline_converges_to_noop(self):
        e = mk_entry("AGENTS.md", "marked-block", "# Block\n", "pi-pipeline-setup")
        m = {"schemaVersion": 1, "provisional": True, "entries": [e]}
        inst = Installer(m, self.root)
        self.assertTrue(inst.apply()["ok"])
        steps = inst.plan()
        self.assertEqual("noop", steps[0]["action"], steps)


class TestH2RecoveryPreservesPostCrashEdit(Base):
    def test_post_crash_user_edit_not_clobbered(self):
        os.makedirs(os.path.join(self.root, "rules"), exist_ok=True)
        os.makedirs(os.path.join(self.root, ".pi/blueprint"), exist_ok=True)
        p = os.path.join(self.root, "rules", "README.md")
        with open(p, "w") as f:
            f.write("original\n")
        with open(os.path.join(self.root, ".pi/blueprint/state.json"), "w") as f:
            json.dump({"entries": {"rules/README.md": sha256(b"original\n")},
                       "last_transaction": None}, f)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("rules/README.md", "whole-file", "v1\n")]}
        inst = Installer(m, self.root)
        try:
            inst.apply(crash_after=3)  # crash after target write, before state commit
        except CrashSimulated:
            pass
        # user edits after the crash
        with open(p, "w") as f:
            f.write("user edit after crash\n")
        r = inst.recover()
        self.assertFalse(r["ok"], r)
        self.assertEqual("conflict", r["error"])
        self.assertIn("rules/README.md", r["conflicts"])
        with open(p) as f:
            self.assertEqual("user edit after crash\n", f.read())


class TestM1Sha256Verified(Base):
    def test_sha256_mismatch_rejected(self):
        e = mk_entry("rules/README.md", "whole-file", "x\n")
        e["sha256"] = "0" * 64
        m = {"schemaVersion": 1, "provisional": True, "entries": [e]}
        with self.assertRaises(InstallerError):
            Installer(m, self.root)

    def test_sha256_missing_rejected(self):
        e = mk_entry("rules/README.md", "whole-file", "x\n")
        del e["sha256"]
        m = {"schemaVersion": 1, "provisional": True, "entries": [e]}
        with self.assertRaises(InstallerError):
            Installer(m, self.root)


class TestM2DesiredTypeValidation(Base):
    def test_whole_file_desired_must_be_str(self):
        e = {"path": "x", "ownership": "whole-file", "desired": {"a": 1}}
        with self.assertRaises(InstallerError):
            Installer({"entries": [e]}, self.root)

    def test_json_keys_desired_must_be_object(self):
        e = {"path": "x", "ownership": "json-keys", "desired": "not-a-dict"}
        with self.assertRaises(InstallerError):
            Installer({"entries": [e]}, self.root)

    def test_frontmatter_values_must_be_strings(self):
        e = {"path": "x.md", "ownership": "frontmatter-fields", "desired": {"model": 123}}
        with self.assertRaises(InstallerError):
            Installer({"entries": [e]}, self.root)

    def test_marked_block_requires_block_id(self):
        e = mk_entry("AGENTS.md", "marked-block", "body", "pi-pipeline-setup")
        del e["blockId"]
        with self.assertRaises(InstallerError):
            Installer({"entries": [e]}, self.root)


class TestM3ConservativeFrontmatter(Base):
    def test_no_frontmatter_file_treated_as_conflict(self):
        # plain Markdown with a horizontal rule, no real frontmatter
        original = "# Heading\n\n---\n\nBody text.\n"
        p = os.path.join(self.root, "role.md")
        with open(p, "w") as f:
            f.write(original)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("role.md", "frontmatter-fields", {"model": "example/dev:1"})]}
        inst = Installer(m, self.root)
        # conservative: cannot unambiguously identify frontmatter => conflict, do not touch
        self.assertEqual("conflict", inst.plan()[0]["action"])
        r = inst.apply()
        self.assertFalse(r["ok"])
        with open(p) as f:
            self.assertEqual(original, f.read())  # nothing discarded or modified

    def test_render_preserves_body_when_no_frontmatter(self):
        # direct render check: even when we would add frontmatter, body is preserved
        original = "# Heading\n\nBody text.\n"
        p = os.path.join(self.root, "role.md")
        with open(p, "w") as f:
            f.write(original)
        e = mk_entry("role.md", "frontmatter-fields", {"model": "example/dev:1"})
        out = pi.render(e, self.root)
        self.assertIn("model: example/dev:1", out)
        self.assertIn("Body text.", out)  # body preserved, not discarded


class TestL1BenignDotDotNames(Base):
    def test_benign_names_not_rejected(self):
        for name in ("..config", "...", "..foo"):
            e = mk_entry(name, "whole-file", "x\n")
            m = {"schemaVersion": 1, "provisional": True, "entries": [e]}
            steps = Installer(m, self.root).plan()
            self.assertNotEqual("reject", steps[0]["action"], (name, steps))

    def test_real_traversal_still_rejected(self):
        e = mk_entry("../escape.txt", "whole-file", "x\n")
        m = {"schemaVersion": 1, "provisional": True, "entries": [e]}
        steps = Installer(m, self.root).plan()
        self.assertEqual("reject", steps[0]["action"])
        self.assertIn("escapes", steps[0]["reason"])


class TestL2RevalidateBeforeMutation(Base):
    def test_apply_rechecks_safety_before_mutation(self):
        # The safety check is repeated inside apply() immediately before mutation:
        # stub detect_unsafe_path so the first call (plan) passes and the later
        # calls (before backup / before write) fail, simulating a TOCTOU swap.
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("config/app.json", "json-keys", {"a": "b"})]}
        inst = Installer(m, self.root)
        calls = {"n": 0}

        def flaky(entry, root):
            calls["n"] += 1
            if calls["n"] == 1:
                return None  # plan passes
            return "symlink injected after plan"

        with mock.patch("poc_installer.detect_unsafe_path", side_effect=flaky):
            with self.assertRaises(InstallerError):
                inst.apply()
        self.assertGreater(calls["n"], 1)  # re-check actually happened


class TestL3TxidAndRecoverableState(Base):
    def test_txids_are_unique(self):
        r1 = self.inst().apply()
        root2 = tempfile.mkdtemp(prefix="pi-tx-")
        try:
            r2 = Installer(make_manifest(), root2).apply()
            self.assertNotEqual(r1["txid"], r2["txid"])
        finally:
            shutil.rmtree(root2, ignore_errors=True)

    def test_error_leaves_recoverable_state(self):
        ro = os.path.join(self.root, "readonly")
        os.makedirs(ro)
        os.chmod(ro, 0o555)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("readonly/new.txt", "whole-file", "x\n")]}
        inst = Installer(m, self.root)
        with self.assertRaises(PermissionError):
            inst.apply()
        self.assertTrue(inst.has_unfinished_transaction())
        self.assertTrue(inst.recover()["recovered"])
        self.assertFalse(inst.has_unfinished_transaction())
        os.chmod(ro, 0o755)


class TestL4Coverage(Base):
    def test_crash_recovery_multi_entry_all_types(self):
        # update path (existing file) + create path + all ownership types, single crash
        os.makedirs(os.path.join(self.root, "rules"), exist_ok=True)
        with open(os.path.join(self.root, "rules", "README.md"), "w") as f:
            f.write("old whole-file\n")
        m = make_manifest()
        inst = Installer(m, self.root)
        # seed state so whole-file is 'update' and others are 'create'
        os.makedirs(os.path.join(self.root, ".pi/blueprint"), exist_ok=True)
        with open(os.path.join(self.root, ".pi/blueprint/state.json"), "w") as f:
            json.dump({"entries": {"rules/README.md": sha256(b"old whole-file\n")},
                       "last_transaction": None}, f)
        try:
            inst.apply(crash_after=7)
        except CrashSimulated:
            pass
        self.assertTrue(inst.recover()["recovered"])
        # after recovery: whole-file restored to original, created files absent
        with open(os.path.join(self.root, "rules", "README.md")) as f:
            self.assertEqual("old whole-file\n", f.read())
        self.assertFalse(os.path.exists(os.path.join(self.root, "config", "app.json")))

    def test_drift_marked_block_and_frontmatter(self):
        inst = self.inst()
        inst.apply()
        # drift on marked-block
        p = os.path.join(self.root, "AGENTS.md")
        with open(p) as f:
            t = f.read()
        with open(p, "w") as f:
            f.write(t.replace("Read docs/workflow.md", "USER EDITED"))
        acts = {s["path"]: s["action"] for s in inst.plan()}
        self.assertEqual("conflict", acts["AGENTS.md"], acts)
        # drift on frontmatter-fields
        p2 = os.path.join(self.root, ".pi/agents/developer.md")
        with open(p2) as f:
            t2 = f.read()
        with open(p2, "w") as f:
            f.write(t2.replace("example/dev:1", "user/model:9"))
        acts = {s["path"]: s["action"] for s in inst.plan()}
        self.assertEqual("conflict", acts[".pi/agents/developer.md"], acts)

    def test_permission_failure_update_path(self):
        # existing managed file; update would overwrite it but the FILE is read-only
        os.makedirs(os.path.join(self.root, "rules"), exist_ok=True)
        p = os.path.join(self.root, "rules", "README.md")
        with open(p, "w") as f:
            f.write("original\n")
        os.chmod(p, 0o444)  # read-only file => overwrite fails
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [mk_entry("rules/README.md", "whole-file", "v1\n")]}
        inst = Installer(m, self.root)
        # no state => plan is 'conflict'; seed state for 'update'
        os.makedirs(os.path.join(self.root, ".pi/blueprint"), exist_ok=True)
        with open(os.path.join(self.root, ".pi/blueprint/state.json"), "w") as f:
            json.dump({"entries": {"rules/README.md": sha256(b"original\n")},
                       "last_transaction": None}, f)
        self.assertEqual("update", inst.plan()[0]["action"])
        with self.assertRaises((PermissionError, InstallerError)):
            inst.apply()
        os.chmod(p, 0o644)  # restore writability for cleanup
        with open(p) as f:
            self.assertEqual("original\n", f.read())  # unchanged


if __name__ == "__main__":
    unittest.main(verbosity=2)
