"""Failure-injection tests for research-only statistical routing."""
import csv
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "market_stat_router.py"
spec = importlib.util.spec_from_file_location("market_stat_router", PATH)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)

HEADER = [
    "result_id", "metric", "segment", "geography", "period", "estimate", "unit",
    "ci_lower", "ci_upper", "sample_n", "source_ids", "model_id",
    "evidence_category", "selection_bias", "limitations"
]

def row(result_id, estimate, unit, category, sample_n="", model_id="", source="S001"):
    return dict(zip(HEADER, [
        result_id, "test metric", "students", "Japan", "2026",
        estimate, unit, "", "", sample_n, source, model_id,
        category, "convenience sample", "test only"
    ]))

class TestRouter(unittest.TestCase):
    def test_wilson_only_known_eligible_sample(self):
        r = router.classify(row("R1", "68.2", "%", "OBSERVED", "11590", "M_WILSON95"))
        self.assertIn("approximate_Wilson_check_from_rounded_percent", r["allowed_methods"])
        self.assertEqual(r["engines_actually_run"], [])

    def test_no_false_binomial_when_n_is_apps(self):
        r = router.classify(row("R2", "2.1", "%", "OBSERVED", "115000", ""))
        self.assertNotIn("approximate_Wilson_check_from_rounded_percent", r["allowed_methods"])
        self.assertIn("binomial_interval_without_verified_unit_and_denominator", r["blocked_methods"])

    def test_nonidentifiable_stays_unknown(self):
        r = router.classify(row("R3", "NON_IDENTIFIABLE", "—", "NON_IDENTIFIABLE"))
        self.assertEqual(r["route_state"], "NON_IDENTIFIABLE")
        self.assertIn("Bayesian_posterior", r["blocked_methods"])

    def test_ordinal_not_empirical_probability(self):
        r = router.classify(row("R4", "E=1;B=3", "ordinal", "ASSUMPTION_ONLY"))
        self.assertIn("present_as_success_probability", r["blocked_methods"])

    def test_only_reported_median_not_recomputed(self):
        r = router.classify(row("R5", "3.4", "USD/month", "OBSERVED"))
        self.assertNotIn("NumPy", r["candidate_engines"])

    def test_invalid_rates_never_classify_valid(self):
        r = router.classify(row("R6", "127", "%", "OBSERVED", "100", "M_WILSON95"))
        self.assertEqual(r["route_state"], "OBSERVED_POINT_OR_SUMMARY")
        self.assertNotIn("SciPy", r["candidate_engines"])

    def test_duplicate_id_fails_closed_and_shared_source_is_marked(self):
        with tempfile.TemporaryDirectory() as t:
            p = pathlib.Path(t) / "q.csv"
            with p.open("w", newline="", encoding="utf8") as f:
                w = csv.DictWriter(f, fieldnames=HEADER)
                w.writeheader()
                w.writerow(row("R1", "22", "%", "OBSERVED", "100"))
                w.writerow(row("R1", "40", "%", "OBSERVED", "200"))
            with self.assertRaisesRegex(ValueError, "duplicate result_id"):
                router.route(p)
            with p.open("w", newline="", encoding="utf8") as f:
                w = csv.DictWriter(f, fieldnames=HEADER)
                w.writeheader()
                w.writerow(row("R1", "22", "%", "OBSERVED", "100", source="S026"))
                w.writerow(row("R2", "40", "%", "OBSERVED", "200", source="S026"))
            result = router.route(p)
            self.assertEqual(result["shared_source_ids"]["S026"], ["R1", "R2"])
            self.assertFalse(result["research_gate_modified"])

if __name__ == "__main__":
    unittest.main()
