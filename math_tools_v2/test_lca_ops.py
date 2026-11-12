"""Public fixture tests for bounded general integrals, time, masks, spectrum."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lca_ops as op

FIXTURE = Path(__file__).parent / "examples/lca_ops_demo.json"
FIXTURE_DOC = json.loads(FIXTURE.read_text(encoding="utf8"))


def byid(doc):
    return {row["id"]: row["value"] for row in doc["tasks"]}


def exact(value):
    obj = value["value"]
    return (int(obj["numerator"]), int(obj["denominator"]))


class LcaOperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = op.execute(FIXTURE_DOC)
        cls.result = byid(cls.doc)

    def test_integrals(self):
        self.assertEqual(exact(self.result["integral_polynomial"]["result"]), (9, 1))
        self.assertEqual(self.result["integral_trigonometric"]["result"]["kind"],
                         "exact_symbolic")
        self.assertEqual(self.result["integral_nonlinear"]["result"]["kind"],
                         "exact_symbolic")

    def test_time_piecewise_and_boundary(self):
        self.assertEqual(exact(self.result["time_piecewise"]["integral"]), (50, 1))
        samples = self.result["time_piecewise"]["samples"]
        self.assertEqual(exact(samples[0]["rate"]), (2, 1))
        self.assertEqual(exact(samples[1]["rate"]), (3, 1))
        self.assertEqual(exact(samples[2]["rate"]), (3, 1))

    def test_masked_sum_exact(self):
        c = self.result["inputs"]["coefficients"]
        self.assertEqual(c["initial"]["value"], {"numerator": "4", "denominator": "1"})
        self.assertEqual(c["replacement"]["value"], {"numerator": "4", "denominator": "1"})
        self.assertEqual(c["operation_rate"]["value"], {"numerator": "2", "denominator": "1"})

    def test_spectrum_events_and_rate(self):
        open_case = self.result["spectrum_open"]
        closed = self.result["spectrum_closed"]
        self.assertEqual(exact(open_case["total"]), (48, 1))
        self.assertEqual(exact(closed["total"]), (52, 1))
        self.assertEqual(len(open_case["events"]), 2)
        self.assertEqual(len(closed["events"]), 3)
        self.assertTrue(open_case["endpoint_policy"]["start_included"])
        self.assertFalse(open_case["endpoint_policy"]["end_included"])

    def test_recompute_and_verification(self):
        with TemporaryDirectory() as temp:
            out = Path(temp)/"result.json"
            op.run(FIXTURE, out)
            op.verify(FIXTURE, out)
            data = json.loads(out.read_text(encoding="utf8"))
            data["tasks"][-1]["value"]["total"]["value"]["numerator"] = "999"
            data["result_sha256"] = op.digest({k:v for k,v in data.items()
                                                if k != "result_sha256"})
            out.write_text(json.dumps(data), encoding="utf8")
            with self.assertRaises(ValueError):
                op.verify(FIXTURE, out)

    def test_fail_closed_negative_cases(self):
        def reject(change):
            data = copy.deepcopy(FIXTURE_DOC)
            change(data)
            with self.assertRaises((ValueError, KeyError, TypeError)):
                op.execute(data)

        reject(lambda d: d["tasks"][0]["expression"].update(op="arbitrary_python"))
        reject(lambda d: d["tasks"][0]["expression"].update(op="div", args=[
            {"op":"integer","value":"1"},{"op":"integer","value":"0"}]))
        reject(lambda d: d["tasks"][0].update(result_unit="kg"))
        reject(lambda d: d["tasks"][3]["segments"][1].update(start="11"))
        reject(lambda d: d["tasks"][4]["groups"][0]["terms"][0].update(mask=2))
        reject(lambda d: d["tasks"][4]["groups"][0]["terms"][0]["factors"][0].update(unit="year"))
        reject(lambda d: d["tasks"][5]["periodic"][0].update(period="0"))
        reject(lambda d: d["tasks"][5]["events"][0]["coefficient"].update(group="not_found"))
        reject(lambda d: d["tasks"][5].update(include_end="yes"))
        reject(lambda d: d["tasks"][0]["bounds"].update(end="0"))
        reject(lambda d: d["tasks"][0].update(untrusted_command="print(123)"))

    def test_singularity_rejection(self):
        bad = copy.deepcopy(FIXTURE_DOC)
        bad["tasks"][0]["expression"] = {
            "op":"div",
            "args":[{"op":"integer","value":"1"},
                    {"op":"sub","args":[{"op":"symbol","name":"t"},
                                         {"op":"integer","value":"1"}]}]}
        with self.assertRaises(ValueError):
            op.execute(bad)

    def test_masked_coefficients_not_back_fitted(self):
        changed = copy.deepcopy(FIXTURE_DOC)
        changed["tasks"][4]["groups"][0]["terms"][0]["factors"][0]["value"] = "15"
        result = byid(op.execute(changed))
        self.assertEqual(result["inputs"]["coefficients"]["initial"]["value"],
                         {"numerator":"5","denominator":"1"})
        self.assertEqual(exact(result["spectrum_open"]["total"]), (49, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
