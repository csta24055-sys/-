"""The existing engine and the earlier research are used as they are (run last)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from lcaapp import enginepath

REPO = os.path.normpath(os.path.join(enginepath.STUDY_ROOT, ".."))
RESEARCH = ["whole-life-carbon-jcat-study/%s" % name for name in
            ("01_COMPLIANCE", "02_SOURCES", "03_INPUTS", "04_FORMULAS", "05_OUTPUTS", "06_LINEAGE", "07_AUDIT", "08_BUILD_PLAN",
             "09_APPROX_STUDY", "10_TRANSFORM_STUDY")]


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, check=True).stdout


class EngineUntouchedTest(unittest.TestCase):
    def test_research_folders_are_unchanged(self):
        self.assertEqual(git("status", "--porcelain", "--", *RESEARCH), "")              # nothing modified, nothing added
        for name in ("09_APPROX_STUDY", "10_TRANSFORM_STUDY"):
            for folder, dirs, _ in os.walk(os.path.join(enginepath.STUDY_ROOT, name)):
                self.assertNotIn("__pycache__", dirs, folder)

    def test_engine_is_the_verified_version(self):
        fp = enginepath.fingerprint()
        self.assertEqual(fp["engine_source_sha256"], enginepath.VERIFIED_ENGINE_SHA256)
        self.assertEqual(fp["model_source_sha256"], enginepath.VERIFIED_MODEL_SHA256)
        self.assertTrue(fp["engine_is_verified_version"])
        self.assertEqual(fp["steps"], {"P1": 1528, "TIME": 95, "AGG": 166})
        enginepath.setup()
        from tstudy import baseline
        baseline.assert_frozen()                                                          # the frozen baseline folders

    def test_existing_verification_of_the_70_units_still_passes(self):
        with tempfile.TemporaryDirectory() as out:
            code = ("import sys; import checks.check_unified as c; c.OUT_DIR = sys.argv[1]; sys.exit(c.main(['--quick']))")
            done = subprocess.run([sys.executable, "-B", "-c", code, out], cwd=enginepath.ENGINE_CODE, capture_output=True,
                                  text=True, timeout=900, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertIn("TOTAL mismatches + failures: 0", done.stdout)
            with open(os.path.join(out, "verification_quick.json"), encoding="utf-8") as fh:
                res = json.load(fh)
            self.assertEqual((res["n_units"], res["n_keys"], res["n_mismatch"], res["n_failed"]), (70, 190, 0, 0))
            self.assertGreater(res["n_values"], 50000)


if __name__ == "__main__":
    unittest.main()
