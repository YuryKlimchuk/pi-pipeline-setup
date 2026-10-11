"""Offline tests for the provisional installer primitives (PoC Track B).

Covers authorized tasks: 0.2 (baseline), 3.1–3.10.
Stdlib unittest; no dependencies installed; writes only inside a temp disposable root.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poc_installer as pi
from poc_installer import CrashSimulated, Installer, InstallerError, sha256


def make_manifest():
    """A synthetic manifest exercising all four ownership types."""
    entries = [
        {"path": "config/app.json", "ownership": "json-keys",
         "desired": {"defaultProvider": "example", "defaultModel": "example/model:1"}},
        {"path": "AGENTS.md", "ownership": "marked-block", "blockId": "pi-pipeline-setup",
         "desired": "# Managed block\nRead docs/workflow.md before changes."},
        {"path": ".pi/agents/developer.md", "ownership": "frontmatter-fields",
         "desired": {"model": "example/dev:1"}},
        {"path": "rules/README.md", "ownership": "whole-file",
         "desired": "Synthetic rule file.\n"},
    ]
    for e in entries:
        e["sha256"] = sha256(pi.desired_canonical(e))
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


class TestBaseline(Base):  # task 0.2
    def test_baseline_collection_no_secrets(self):
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        with open(os.path.join(self.root, "config", "app.json"), "w") as f:
            json.dump({"name": "fixture"}, f)
        baseline = collect_baseline(self.root)
        self.assertIn("config/app.json", baseline)
        blob = json.dumps(baseline).lower()
        for marker in SECRET_MARKERS:
            self.assertNotIn(marker, blob)


class TestManifest(Base):  # task 3.1
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


class TestPlanAndApply(Base):  # tasks 3.2, 3.3
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
        # state committed
        with open(os.path.join(self.root, ".pi/blueprint/state.json")) as f:
            state = json.load(f)
        self.assertEqual(4, len(state["entries"]))

    def test_reconciliation_noop_update_conflict(self):
        inst = self.inst()
        self.assertTrue(inst.apply()["ok"])
        # no-op on second apply
        steps = inst.plan()
        self.assertTrue(all(s["action"] == "noop" for s in steps), steps)
        # update: change whole-file desired
        m = make_manifest()
        for e in m["entries"]:
            if e["path"] == "rules/README.md":
                e["desired"] = "Synthetic rule file (v2).\n"
                e["sha256"] = sha256(pi.desired_canonical(e))
        inst2 = Installer(m, self.root)
        steps = inst2.plan()
        acts = {s["path"]: s["action"] for s in steps}
        self.assertEqual("update", acts["rules/README.md"], acts)
        self.assertEqual("noop", acts["config/app.json"], acts)
        # drift: user modifies a managed file
        with open(os.path.join(self.root, "rules/README.md"), "w") as f:
            f.write("user changed this\n")
        steps = inst2.plan()
        acts = {s["path"]: s["action"] for s in steps}
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


class TestIdempotency(Base):  # task 3.4
    def test_repeat_apply_noop_no_duplicate_block(self):
        inst = self.inst()
        self.assertTrue(inst.apply()["ok"])
        self.assertTrue(inst.apply()["ok"])
        with open(os.path.join(self.root, "AGENTS.md")) as f:
            text = f.read()
        self.assertEqual(1, text.count("<!-- BEGIN pi-pipeline-setup -->"))


class TestCrashRecovery(Base):  # task 3.5
    def test_crash_between_each_step_recovers(self):
        entry = {"path": "rules/README.md", "ownership": "whole-file", "desired": "v1\n"}
        entry["sha256"] = sha256(pi.desired_canonical(entry))
        m = {"schemaVersion": 1, "provisional": True, "entries": [entry]}
        crash_points = 0
        for crash in range(10):
            root2 = tempfile.mkdtemp(prefix="pi-crash-")
            try:
                inst = Installer(m, root2)
                try:
                    inst.apply(crash_after=crash)
                    # no crash raised => all crash points exhausted
                    break
                except CrashSimulated:
                    crash_points += 1
                self.assertTrue(inst.has_unfinished_transaction(), f"no unfinished tx at {crash}")
                self.assertTrue(inst.recover()["recovered"])
                self.assertFalse(inst.has_unfinished_transaction())
                self.assertFalse(os.path.exists(os.path.join(root2, "rules", "README.md")),
                                 "target not rolled back after crash")
            finally:
                shutil.rmtree(root2, ignore_errors=True)
        self.assertGreaterEqual(crash_points, 4, f"only {crash_points} crash points exercised")


class TestDrift(Base):  # task 3.6
    def test_drift_preserves_user_change(self):
        inst = self.inst()
        inst.apply()
        p = os.path.join(self.root, "rules/README.md")
        with open(p, "w") as f:
            f.write("user edit\n")
        steps = inst.plan()
        acts = {s["path"]: s["action"] for s in steps}
        self.assertEqual("conflict", acts["rules/README.md"])
        r = inst.apply()
        self.assertFalse(r["ok"])
        self.assertEqual("conflict", r["error"])
        with open(p) as f:
            self.assertEqual("user edit\n", f.read())


class TestPartialCompletion(Base):  # task 3.7
    def test_unfinished_transaction_blocks_until_recover(self):
        m = make_manifest()
        m["entries"] = [{"path": "rules/README.md", "ownership": "whole-file", "desired": "x\n"}]
        m["entries"][0]["sha256"] = sha256(pi.desired_canonical(m["entries"][0]))
        inst = Installer(m, self.root)
        try:
            inst.apply(crash_after=3)
        except CrashSimulated:
            pass
        self.assertTrue(inst.has_unfinished_transaction())
        r = inst.apply()
        self.assertFalse(r["ok"])
        self.assertEqual("unfinished transaction; run recover() first", r["error"])
        self.assertTrue(inst.recover()["recovered"])
        self.assertFalse(inst.has_unfinished_transaction())
        self.assertTrue(inst.apply()["ok"])


class TestSymlinkHardlink(Base):  # tasks 3.8, 3.2
    def test_symlink_escape_rejected(self):
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        outside = tempfile.mktemp()
        os.symlink(outside, os.path.join(self.root, "config", "app.json"))
        steps = self.inst().plan()
        s = next(s for s in steps if s["path"] == "config/app.json")
        self.assertEqual("reject", s["action"])
        self.assertIn("symlink", s["reason"])

    def test_hardlink_rejected(self):
        os.makedirs(os.path.join(self.root, "config"), exist_ok=True)
        a = os.path.join(self.root, "config", "app.json")
        b = os.path.join(self.root, "config", "other.json")
        with open(a, "w") as f:
            f.write("{}")
        os.link(a, b)
        m = make_manifest()
        m["entries"] = [{"path": "config/other.json", "ownership": "json-keys", "desired": {}}]
        steps = Installer(m, self.root).plan()
        self.assertEqual("reject", steps[0]["action"])
        self.assertIn("hardlink", steps[0]["reason"])


class TestPermission(Base):  # task 3.9
    def test_permission_failure_no_partial_apply(self):
        ro = os.path.join(self.root, "readonly")
        os.makedirs(ro)
        os.chmod(ro, 0o555)
        m = {"schemaVersion": 1, "provisional": True,
             "entries": [{"path": "readonly/new.txt", "ownership": "whole-file", "desired": "x\n"}]}
        m["entries"][0]["sha256"] = sha256(pi.desired_canonical(m["entries"][0]))
        inst = Installer(m, self.root)
        with self.assertRaises(PermissionError):
            inst.apply()
        self.assertFalse(os.path.exists(os.path.join(self.root, "readonly", "new.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.root, ".pi/blueprint/state.json")))
        os.chmod(ro, 0o755)


class TestNegatives(Base):  # task 3.10
    def test_no_git_works(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, ".git")))
        self.assertTrue(self.inst().apply()["ok"])

    def test_corrupt_manifest(self):
        with self.assertRaises(InstallerError):
            Installer({"entries": [{"path": "x", "ownership": "bogus", "desired": "x"}]}, self.root)
        with self.assertRaises(InstallerError):
            Installer({"entries": [{"path": "a"}, {"path": "a"}]}, self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
