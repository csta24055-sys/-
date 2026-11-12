"""Math IR 0.1 / Phase 2: Python-native precise & approximate handoff.

SymPy -> exact Fraction -> NumPy float64 / mpmath decimal / SciPy numerical
-> DuckDB VARCHAR-backed structured records -> validator. Synthetic data only.
Does not require unsafe evaluation of mathematical expressions.
"""
from __future__ import annotations

import copy
from decimal import Decimal
from fractions import Fraction
import json
import math
import shutil
from pathlib import Path
import sys
import tempfile

import duckdb
import mpmath
import numpy as np
import scipy
from scipy.integrate import quad
import sympy

from phase1 import (SCHEMA, canonical, check_envelope, digest,
                    exact_fields, exact_rational, make_cases,
                    rat_node, require, sympy_eval)

HANDOFF_SCHEMA = "math-handoff/0.1"
WORK_DPS = 95
OUTPUT_DIGITS = 80


def fraction_of(node):
    a, b = exact_rational(node)
    return Fraction(a, b)


def fraction_node(f):
    return rat_node(f.numerator, f.denominator)


def from_float_hex(s):
    require(type(s) is str and len(s) < 32, "Invalid float64 encoding")
    try:
        x = float.fromhex(s)
    except (ValueError, OverflowError):
        raise ValueError("Malformed float64 hex") from None
    require(math.isfinite(x), "NaN/Infinity forbidden")
    return x


def numpy_repr(f):
    # This conversion is deliberate. The exact Fraction is retained separately.
    try:
        x = np.float64(float(f))
    except (ValueError, OverflowError):
        raise ValueError("Cannot represent input as finite float64") from None
    require(np.isfinite(x), "Nonfinite float64 forbidden")
    rounded = Fraction.from_float(float(x))
    return {
        "dtype": "float64",
        "hex": float(x).hex(),
        "difference_from_exact": fraction_node(rounded - f),
        "error_kind": "measured_against_known_exact_value",
        "certified_error_bound": False,
    }


def mpmath_repr(f):
    with mpmath.workdps(WORK_DPS):
        n = mpmath.mpf(f.numerator)
        d = mpmath.mpf(f.denominator)
        approximation = n / d
        dec = mpmath.nstr(approximation, OUTPUT_DIGITS)
    # This is the precise rational value denoted by the *decimal output*,
    # not an assertion that the algorithm has a rigorously certified error.
    represented = Fraction(Decimal(dec))
    return {
        "working_decimal_digits": WORK_DPS,
        "output_significant_digits": OUTPUT_DIGITS,
        "decimal": dec,
        "difference_from_exact": fraction_node(represented - f),
        "error_kind": "reported_decimal_vs_known_exact_value",
        "certified_error_bound": False,
    }


def case_record(case):
    check_envelope(case)
    exact_node = sympy_eval(case)
    exact_value = fraction_of(exact_node)
    return {
        "case_id": case["case_id"],
        "source_sha256": digest(case),
        "exact": exact_node,
        "unit": case["unit"],
        "assumptions": copy.deepcopy(case["symbols"]),
        "numpy": numpy_repr(exact_value),
        "mpmath": mpmath_repr(exact_value),
    }


def scipy_record():
    # Integrate x² on [0, 1]. Reference 1/3 is exact via SymPy.
    x = sympy.Symbol("x", real=True)
    ref_sym = sympy.integrate(x**2, (x, 0, 1))
    reference = Fraction(int(ref_sym.p), int(ref_sym.q))
    value, reported_error = quad(lambda x: x * x, 0, 1,
                                 epsabs=1e-12, epsrel=1e-12)
    require(math.isfinite(value) and math.isfinite(reported_error),
            "Nonfinite quadrature output")
    difference = Fraction.from_float(value) - reference
    return {
        "operation": "integrate_x_squared_0_to_1",
        "reference_exact": fraction_node(reference),
        "engine": "scipy.integrate.quad",
        "numerical_value_hex": value.hex(),
        "observed_difference_exact": fraction_node(difference),
        "quadpack_estimated_absolute_error_hex": reported_error.hex(),
        "requested_absolute_tolerance": "1e-12",
        "requested_relative_tolerance": "1e-12",
        "error_estimate_is_proven_bound": False,
        "unit": "1",
    }


def numpy_cancellation():
    # Exact sum is 1, while sequential binary64 addition loses the unit.
    original = [Fraction(10**20), Fraction(1), Fraction(-10**20)]
    arr = np.array([float(v) for v in original], dtype=np.float64)
    answer = float(np.sum(arr, dtype=np.float64))
    expected = sum(original)
    return {
        "exact_inputs": [fraction_node(v) for v in original],
        "dtype": "float64",
        "numpy_result_hex": answer.hex(),
        "exact_sum": fraction_node(expected),
        "observed_difference_exact": fraction_node(Fraction.from_float(answer) - expected),
        "unit": "1",
        "error_kind": "measured_against_known_exact_value",
    }


def produce_document():
    bundle = make_cases()
    records = [case_record(case) for case in bundle["cases"]]
    return {
        "schema": HANDOFF_SCHEMA,
        "source": bundle,
        "source_sha256": digest(bundle),
        "engines": {
            "SymPy": sympy.__version__,
            "NumPy": np.__version__,
            "SciPy": scipy.__version__,
            "mpmath": mpmath.__version__,
            "DuckDB": duckdb.__version__,
        },
        "precision_policy": {
            "source": "exact rational (no implicit decimal approximation)",
            "numpy": "IEEE-754 binary64 with exact observed conversion error",
            "mpmath": "95 decimal working digits; 80-digit display; no certified bound",
            "scipy": "quadpack estimate, explicitly not certified",
            "duckdb": "exact strings in VARCHAR; no DOUBLE/DECIMAL coercion",
        },
        "records": records,
        "scipy": scipy_record(),
        "numpy_cancellation": numpy_cancellation(),
    }


def verify_document(document):
    exact_fields(document, {"schema", "source", "source_sha256", "engines",
                            "precision_policy", "records", "scipy", "numpy_cancellation"}, "document")
    require(document["schema"] == HANDOFF_SCHEMA, "Unknown handoff schema")
    require(type(document["source"]) is dict and set(document["source"]) == {"schema", "cases"}, "Bad source")
    require(document["source"]["schema"] == SCHEMA, "Wrong math IR schema")
    require(document["source_sha256"] == digest(document["source"]), "Source checksum mismatch")
    # For this controlled synthetic benchmark the exact source is specified.
    require(document["source"] == make_cases(), "Synthetic reference changed")
    require(type(document["engines"]) is dict and set(document["engines"]) == {"SymPy", "NumPy", "SciPy", "mpmath", "DuckDB"}, "Missing engine")
    require(type(document["precision_policy"]) is dict and set(document["precision_policy"]) == {"source", "numpy", "mpmath", "scipy", "duckdb"}, "Missing precision policy")
    require(document["precision_policy"] == produce_document_precision_policy(), "Altered precision policy")
    require(type(document["records"]) is list and len(document["records"]) == len(document["source"]["cases"]), "Missing or extra records")
    for case, record in zip(document["source"]["cases"], document["records"]):
        check_envelope(case)
        exact_fields(record, {"case_id", "source_sha256", "exact", "unit", "assumptions", "numpy", "mpmath"}, "record")
        require(record["case_id"] == case["case_id"] and record["source_sha256"] == digest(case), "Record lineage changed")
        require(record["unit"] == case["unit"] and record["assumptions"] == case["symbols"], "Metadata changed")
        require(record["exact"] == sympy_eval(case), "Exact rational changed")
        exact = fraction_of(record["exact"])
        nr = record["numpy"]
        exact_fields(nr, {"dtype", "hex", "difference_from_exact", "error_kind", "certified_error_bound"}, "NumPy record")
        require(nr["dtype"] == "float64" and nr["certified_error_bound"] is False and nr["error_kind"] == "measured_against_known_exact_value", "Invalid NumPy claims")
        floatval = from_float_hex(nr["hex"])
        require(nr["difference_from_exact"] == fraction_node(Fraction.from_float(floatval) - exact), "Incorrect float error")
        require(nr == numpy_repr(exact), "NumPy value changed")
        mp = record["mpmath"]
        exact_fields(mp, {"working_decimal_digits", "output_significant_digits", "decimal", "difference_from_exact", "error_kind", "certified_error_bound"}, "mpmath record")
        require(mp["working_decimal_digits"] == WORK_DPS and mp["output_significant_digits"] == OUTPUT_DIGITS and mp["certified_error_bound"] is False, "Invalid precision claim")
        require(type(mp["decimal"]) is str and len(mp["decimal"]) <= 128, "Invalid decimal")
        require(mp["difference_from_exact"] == fraction_node(Fraction(Decimal(mp["decimal"])) - exact), "Incorrect decimal error")
        require(mp == mpmath_repr(exact), "mpmath result modified")
    require(document["scipy"] == scipy_record(), "SciPy test record altered")
    require(document["numpy_cancellation"] == numpy_cancellation(), "NumPy cancellation record altered")
    require(fraction_of(document["numpy_cancellation"]["exact_sum"]) == 1, "Exact cancellation test invalid")
    require(fraction_of(document["numpy_cancellation"]["observed_difference_exact"]) != 0,
            "Cancellation test did not reveal any float64 error")
    require(abs(fraction_of(document["scipy"]["observed_difference_exact"])) < Fraction(1, 10**12),
            "SciPy integration exceeds requested tolerance on known reference")
    third = document["records"][0]
    require(abs(fraction_of(third["mpmath"]["difference_from_exact"])) <
            abs(fraction_of(third["numpy"]["difference_from_exact"])), "High precision not better for 1/3")
    return len(document["records"])


def produce_document_precision_policy():
    return {
        "source": "exact rational (no implicit decimal approximation)",
        "numpy": "IEEE-754 binary64 with exact observed conversion error",
        "mpmath": "95 decimal working digits; 80-digit display; no certified bound",
        "scipy": "quadpack estimate, explicitly not certified",
        "duckdb": "exact strings in VARCHAR; no DOUBLE/DECIMAL coercion",
    }


def database_roundtrip(document, path):
    """Store exact integers as VARCHAR and roundtrip full structured objects."""
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TABLE records (case_id VARCHAR PRIMARY KEY, numerator VARCHAR NOT NULL, denominator VARCHAR NOT NULL, unit VARCHAR NOT NULL, source_hash VARCHAR NOT NULL, record_json VARCHAR NOT NULL, record_hash VARCHAR NOT NULL)")
        con.execute("CREATE TABLE bundle_meta (document_sha256 VARCHAR NOT NULL)")
        con.execute("INSERT INTO bundle_meta VALUES (?)", [digest(document)])
        for record in document["records"]:
            val = record["exact"]
            con.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [record["case_id"], val["numerator"], val["denominator"],
                         record["unit"], record["source_sha256"], canonical(record), digest(record)])
        stored = con.execute("SELECT case_id,numerator,denominator,unit,source_hash,record_json,record_hash FROM records ORDER BY case_id").fetchall()
        require(len(stored) == len(document["records"]), "DuckDB row loss")
        by_id = {r["case_id"]: r for r in document["records"]}
        for ident, num, den, unit, source_hash, payload, check in stored:
            record = by_id[ident]
            require(num == record["exact"]["numerator"] and den == record["exact"]["denominator"], "DuckDB integer loss")
            require(unit == record["unit"] and source_hash == record["source_sha256"], "DuckDB metadata loss")
            require(json.loads(payload) == record and digest(json.loads(payload)) == check, "DuckDB payload loss")
        by_unit = con.execute("SELECT unit, COUNT(*) FROM records GROUP BY unit ORDER BY unit").fetchall()
        require(sum(count for _, count in by_unit) == len(document["records"]), "DuckDB group count error")
        print(f"PASS DuckDB VARCHAR exact storage and retrieval: {len(stored)} rows; groups={by_unit}")
    finally:
        con.close()


def verify_saved(document_path, database_path):
    """Read both artifacts anew; detect source, exact values and metadata changes."""
    document = json.loads(Path(document_path).read_text(encoding="utf-8"))
    n = verify_document(document)
    con = duckdb.connect(str(database_path), read_only=True)
    try:
        digest_rows = con.execute("SELECT document_sha256 FROM bundle_meta").fetchall()
        require(digest_rows == [(digest(document),)], "Stored document digest mismatch")
        data = con.execute("SELECT case_id,numerator,denominator,unit,source_hash,record_json,record_hash FROM records ORDER BY case_id").fetchall()
        require(len(data) == n, "Stored case count mismatch")
        expected = {r["case_id"]: r for r in document["records"]}
        for ident, numerator, denominator, unit, source_hash, payload, hash_value in data:
            require(ident in expected, "Unknown DuckDB case")
            record = expected[ident]
            require((numerator, denominator) == (record["exact"]["numerator"], record["exact"]["denominator"]), "Database exact rational altered")
            require(unit == record["unit"] and source_hash == record["source_sha256"], "Database metadata altered")
            require(json.loads(payload) == record and hash_value == digest(record), "Database JSON/hash altered")
    finally:
        con.close()
    print(f"PASS independently reopened DuckDB and JSON: {n} exact records")
    return document


def database_tamper_test(document_path, database_path):
    """Ensure a separately reopened database cannot silently change data."""
    with tempfile.TemporaryDirectory() as d:
        candidate = Path(d) / "tampered.duckdb"
        for label, sql in {
            "db_exact_value": "UPDATE records SET numerator='888' WHERE case_id='third_exact'",
            "db_unit": "UPDATE records SET unit='1' WHERE case_id='third_exact'",
            "db_bundle_digest": "UPDATE bundle_meta SET document_sha256='bad'",
        }.items():
            shutil.copyfile(database_path, candidate)
            con = duckdb.connect(str(candidate))
            try:
                con.execute(sql)
            finally:
                con.close()
            try:
                verify_saved(document_path, candidate)
            except (ValueError, KeyError, TypeError):
                print(f"PASS database tamper detected: {label}")
            else:
                raise AssertionError(f"Database tamper accepted: {label}")


def tamper_test(original):
    modifications = {
        "unit": lambda d: d["records"][0].update(unit="1"),
        "exact_numerator": lambda d: d["records"][0]["exact"].update(numerator="2"),
        "assumption": lambda d: d["records"][2].update(assumptions=[]),
        "float_error": lambda d: d["records"][0]["numpy"].update(difference_from_exact=rat_node(0)),
        "float_nonfinite": lambda d: d["records"][0]["numpy"].update(hex="inf"),
        "mpmath_precision": lambda d: d["records"][0]["mpmath"].update(working_decimal_digits=200),
        "mpmath_decimal": lambda d: d["records"][0]["mpmath"].update(decimal="0.3333333"),
        "precision_policy": lambda d: d["precision_policy"].update(numpy="exact"),
        "source_digest": lambda d: d.update(source_sha256="0" * 64),
    }
    for label, modify in modifications.items():
        bad = copy.deepcopy(original)
        modify(bad)
        try:
            verify_document(bad)
        except (ValueError, KeyError, TypeError, ArithmeticError):
            print(f"PASS rejection: {label}")
        else:
            raise AssertionError(f"Corrupt data accepted: {label}")


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "run":
        out_json, out_database = map(Path, sys.argv[2:])
        require(not out_json.exists() and not out_database.exists(), "Outputs must be new files")
        doc = produce_document()
        passed = verify_document(doc)
        database_roundtrip(doc, out_database)
        tamper_test(doc)
        out_json.write_text(canonical(doc) + "\n", encoding="utf-8")
        loaded = verify_saved(out_json, out_database)
        require(verify_document(loaded) == passed, "JSON roundtrip failed")
        print(f"PHASE 2: PASS {passed} exact->NumPy/mpmath cases, SciPy quad, NumPy cancellation, DuckDB, 9 tamper tests")
    elif len(sys.argv) == 4 and sys.argv[1] == "verify":
        verify_saved(sys.argv[2], sys.argv[3])
        database_tamper_test(sys.argv[2], sys.argv[3])
        print("PHASE 2 INDEPENDENT PROCESS: PASS with 3 database tamper tests")
    else:
        raise ValueError("Usage: phase2.py {run|verify} OUTPUT_JSON OUTPUT_DUCKDB")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        print(f"MATH_HANDOFF_ERROR: {exc}", file=sys.stderr)
        sys.exit(2)