"""The three systems working together: input -> common format -> engine -> storage -> display.

``Service`` is what the command line and the web screen both call. It never lets a bad input
end the program: a calculation that cannot be done is stored as ``blocked`` (the input lacks
something required) or ``failed`` (the engine could not evaluate it), with the reason.
"""
from __future__ import annotations

import collections
import math
import time
import traceback
import warnings
from typing import Any

from . import APP_VERSION, common, convert, enginepath, refdata, view
from . import binding as binding_mod
from .store import Store, StoreError, json_safe

CACHE_SIZE = 4


def plain(doc: Any) -> Any:
    """Copy of a parsed document in which non-finite numbers are text, so that it can be stored."""
    if isinstance(doc, float) and not math.isfinite(doc):
        return "NaN" if math.isnan(doc) else ("Infinity" if doc > 0 else "-Infinity")
    if isinstance(doc, dict):
        return {str(k): plain(v) for k, v in doc.items()}
    if isinstance(doc, (list, tuple)):
        return [plain(v) for v in doc]
    return doc


class Service:
    def __init__(self, store: Store, binding: binding_mod.Binding | None = None):
        self.store = store
        self.binding = binding or binding_mod.provisional()
        self._systems: collections.OrderedDict = collections.OrderedDict()      # prepared engines, reused
        self.prepared = 0                                                        # how many were built

    # ---- reference data --------------------------------------------------------------------------
    def register_refset(self, refset: Any) -> dict:
        checked, left_out = refdata.check(refset)
        set_id = self.store.add_refset(checked)
        return {"reference_set_id": set_id, "name": checked["name"], "version": checked["version"],
                "n_factors": len(checked["data"]["factors"]), "left_out": left_out}

    def _refset_id(self, declared: Any, explicit: int | None) -> int | None:
        if explicit is not None:
            return explicit
        if isinstance(declared, dict) and isinstance(declared.get("name"), str) and isinstance(declared.get("version"), str):
            found = self.store.find_refset(declared["name"], declared["version"])
            if found is not None:
                return found
        sets = self.store.list_refsets()
        return sets[0]["id"] if len(sets) == 1 else None

    # ---- inputs -----------------------------------------------------------------------------------
    def import_document(self, doc: Any, project_id: int | None = None, name: str | None = None) -> dict:
        """Read an input document, turn it into the common format and store both as a new version."""
        doc = plain(doc)
        if not isinstance(doc, dict):
            raise common.InputError("入力文書は JSON オブジェクトでなければならない")
        units = {}
        set_id = self._refset_id(doc.get("reference_set"), None)
        if set_id is not None:
            units = common.unit_table(self.store.get_refset(set_id)["data"]["unit_conversions"])
        data = common.build(doc, self.binding, units)
        if set_id is None:
            data["issues"].append({"level": "info", "code": "no_unit_table", "path": "",
                                   "message": "参照データが決まらないので、単位の換算表なしで読んだ"})
            data["n_issues"] += 1
        summary = common.summary(data)
        if project_id is None:
            title = name or data["title"] or "（名称なし）"
            project_id = self.store.create_project(title, data["data_kind"])
        elif name:
            self.store.update_project(project_id, name=name)
        version_id = self.store.save_input(project_id, doc, data, summary)
        return {"project_id": project_id, "input_version_id": version_id, "summary": summary,
                "issues": data["issues"][:50], "unsupported": data["unsupported"][:50], "n_others": len(data["others"])}

    # ---- calculation ------------------------------------------------------------------------------
    def _prepared(self, key: tuple, build) -> dict:
        """Conversion and engine preparation of one input, done once and reused for later calculations."""
        if key in self._systems:
            self._systems.move_to_end(key)
            return self._systems[key]
        entry = build()
        self.prepared += 1
        self._systems[key] = entry
        while len(self._systems) > CACHE_SIZE:
            self._systems.popitem(last=False)
        return entry

    def versions(self, version: dict, refset: dict | None) -> dict:
        out = {"app": APP_VERSION, "input_sha256": version["sha256"], "binding": version["binding"]}
        out.update(enginepath.fingerprint())
        if refset is not None:
            out["reference_set"] = {k: refset[k] for k in ("id", "name", "version", "data_kind", "licence_status", "sha256")}
        return out

    def calculate(self, project_id: int, study_period: Any, input_version_id: int | None = None,
                  reference_set_id: int | None = None, baseline_input_version_id: int | None = None,
                  name: str = "") -> dict:
        """Run the existing engine on a stored input and store the outcome. Returns the stored run."""
        started = time.perf_counter()
        self.store.get_project(project_id)
        if input_version_id is None:
            input_version_id = self.store.latest_input_id(project_id)
            if input_version_id is None:
                raise StoreError("この建物プロジェクトには入力がまだない")
        version = self.store.get_input(input_version_id, with_data=False)
        if version["project_id"] != project_id:
            raise StoreError("入力の版 %s は建物プロジェクト %s のものではない" % (input_version_id, project_id))
        set_id = self._refset_id(version["summary"].get("declared", {}).get("reference_set"), reference_set_id)
        try:
            refset = None if set_id is None else self.store.get_refset(set_id)
        except StoreError:
            refset, set_id = None, None
        base_version = None
        if baseline_input_version_id is not None:
            try:
                base_version = self.store.get_input(baseline_input_version_id, with_data=False)
            except StoreError:
                baseline_input_version_id = None
        period = study_period
        if isinstance(period, str):
            try:
                period = float(period.strip())
            except ValueError:
                period = None
        valid_period = isinstance(period, (int, float)) and not isinstance(period, bool) and math.isfinite(period) and period > 0
        condition_id = self.store.save_condition(project_id, float(period) if valid_period else study_period, set_id,
                                                 baseline_input_version_id, name)
        versions = self.versions(version, refset)
        report: dict[str, Any] = {"input_summary": version["summary"]}

        def finish(status: str, message: str, results=None, shown=None) -> dict:
            run_id = self.store.save_run(project_id, input_version_id, condition_id, status, message, versions,
                                         results, shown, report, (time.perf_counter() - started) * 1000.0)
            return self.store.get_run(run_id)

        if not valid_period:
            return finish("blocked", "評価期間は正の数値（年）で指定する（指定された値：%r）" % (study_period,))
        period = float(period)
        if refset is None:
            return finish("blocked", "原単位などの参照データが決まらない。参照データを登録するか、計算条件で指定する")
        scenario_id = "P%d-V%d" % (project_id, version["version_no"])
        base_id = None if base_version is None else "P%d-V%d-BASE" % (base_version["project_id"], base_version["version_no"])
        key = (input_version_id, set_id, baseline_input_version_id, period if base_version is not None else None)

        def build() -> dict:
            data = self.store.get_input(input_version_id)["common"]
            model_dict, conv = convert.to_model(data, refset, scenario_id, period, base_id)
            boundary = model_dict.get("boundary") or {}
            entry = {"conv": conv, "system": None, "context": {
                "data_kind": data["data_kind"],
                "refset": {k: refset[k] for k in ("name", "version", "data_kind")},
                "included_stages": boundary.get("included_lifecycle_stages"),
                "study_start_year": boundary.get("study_start_year"),
                "not_passed_counts": conv["not_passed_counts"],
                "n_others": len(data["others"]), "n_unsupported": len(data["unsupported"]),
                "n_unbound": data["stats"].get("unbound", 0), "conversion_notes": conv["notes"]}}
            if conv["blocking"]:
                return entry
            scn = convert.build_scenario(model_dict)
            baselines = None
            if base_version is not None:
                base_data = self.store.get_input(baseline_input_version_id)["common"]
                base_dict, base_conv = convert.to_model(base_data, refset, base_id, period, None)
                entry["baseline_conversion"] = {"blocking": base_conv["blocking"],
                                                "not_passed_counts": base_conv["not_passed_counts"]}
                if base_conv["blocking"]:
                    raise convert.ConversionError("基準案の入力に必須項目が足りない（%d 件）" % len(base_conv["blocking"]))
                baselines = {base_id: convert.build_scenario(base_dict)}
            system = entry["system"] = enginepath.unified().System(scn, baselines=baselines)
            tabs = system.tabs                                    # what the engine made of the input: column tables
            entry["engine_tables"] = {
                "n_tables": len(tabs.rows), "n_columns": sum(len(cols) for cols in tabs.data.values()),
                "rows": {name: int(tabs.rows[name]) for name in ("materials", "equipment", "refrigerants", "factors",
                                                                 "operation.grid.table") if name in tabs.rows},
                "n_knot_spectra": len(system.K), "n_knots": int(system.n_knots)}
            return entry

        caught: list = []
        try:
            with warnings.catch_warnings(record=True) as caught:  # numerical warnings become a note, not console noise
                warnings.simplefilter("always")
                entry = self._prepared(key, build)
                conv = report["conversion"] = entry["conv"]
                if "engine_tables" in entry:
                    report["engine_tables"] = entry["engine_tables"]
                if "baseline_conversion" in entry:
                    report["baseline_conversion"] = entry["baseline_conversion"]
                if conv["blocking"]:
                    return finish("blocked", "必須項目が足りないので計算していない（%d 件。例：%s）"
                                  % (len(conv["blocking"]), "、".join(b["path"] for b in conv["blocking"][:5])))
                system = entry["system"]
                if math.ceil(period) > system.H:
                    return finish("blocked", "評価期間 %g 年は、年次表の長さ（%d 年）を超えている" % (period, int(system.H)))
                results = system.at(period)
        except convert.ConversionError as exc:
            return finish("failed", str(exc))
        except Exception as exc:                                  # the engine says why it cannot evaluate
            report["traceback"] = traceback.format_exc()[-2000:]
            reason = "入力がエンジンの評価できる範囲の外にある" if type(exc).__name__ == "Unusable" else "計算中にエラーが起きた"
            return finish("failed", "%s（%s: %s）" % (reason, type(exc).__name__, exc))
        results, n_replaced = json_safe(results)
        entry.setdefault("warnings", set()).update(str(w.message) for w in caught if issubclass(w.category, RuntimeWarning))
        numeric = sorted(entry["warnings"])                       # also those of the preparation, when it is reused
        if numeric:
            report["engine_warnings"] = numeric
        shown = view.build(results, period, dict(entry["context"], n_replaced=n_replaced, engine_warnings=numeric))
        return finish("ok", "", results, shown)

    # ---- reading back ----------------------------------------------------------------------------
    def run_page(self, run_id: int) -> dict:
        """Everything the result screen needs, read from storage (nothing is recomputed)."""
        run = self.store.get_run(run_id)
        version = self.store.get_input(run["input_version_id"], with_data=False)
        return {"run": run, "project": self.store.get_project(run["project_id"]), "input": version,
                "condition": self.store.get_condition(run["condition_id"]),
                "others": self.store.list_others(run["input_version_id"])}
