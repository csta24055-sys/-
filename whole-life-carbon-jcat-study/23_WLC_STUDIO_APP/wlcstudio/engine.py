"""Connection to the existing app and engine (12_APP_BASE `lcaapp` -> 10_TRANSFORM_STUDY unified System).

Nothing of the 70-unit system is re-implemented here. We call lcaapp.service.Service, which converts the
document, prepares System(scenario) once per input version and evaluates System.at(T) per study period
(an in-process cache: changing only T re-uses the prepared system).

Thread safety: lcaapp's Store is bound to the thread that opened it and System.at() mutates shared state,
so an Engine must be used from one thread only (the WLC Studio server is single-threaded; Engine also holds
a lock so that an accidental second thread waits instead of corrupting a run).
"""
from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]          # whole-life-carbon-jcat-study/
APP_BASE = ROOT / "12_APP_BASE"
if str(APP_BASE) not in sys.path:
    sys.path.insert(0, str(APP_BASE))

from lcaapp import binding as _binding  # noqa: E402
from lcaapp import service as _service  # noqa: E402
from lcaapp import store as _store  # noqa: E402

FICTIONAL_REFSET = APP_BASE / "samples" / "refset_fictional.json"


class Engine:
    def __init__(self, path: str | Path, refset_path: str | Path | None = None):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.store = _store.Store(str(path))
        self.svc = _service.Service(self.store, _binding.default())
        self.lock = threading.Lock()
        self.refset_path = Path(refset_path) if refset_path else FICTIONAL_REFSET
        self.set_id, self.refset = self._ensure_refset()

    def _ensure_refset(self) -> tuple[int, dict]:
        ref = json.loads(self.refset_path.read_text(encoding="utf-8"))
        sid = self.store.find_refset(ref["name"], ref["version"])
        if sid is None:
            sid = self.svc.register_refset(ref)["reference_set_id"]
        full = self.store.get_refset(sid)
        return sid, full

    def refset_dict(self) -> dict:
        """The registered set in the format bridge.factor_profile reads."""
        r = self.refset
        return {"name": r.get("name"), "version": r.get("version"), "data_kind": r.get("data_kind"),
                "licence_status": r.get("licence_status"), "data": r["data"],
                **({"wlcstudio_profile": r["wlcstudio_profile"]} if "wlcstudio_profile" in r else {})}

    def run(self, doc: dict, lca_project_id: int | None, period: float, name: str = "WLC Studio") -> dict:
        """Import the document as a new input version (or the same version when unchanged) and calculate at T."""
        with self.lock:
            t0 = time.perf_counter()
            if lca_project_id is not None:
                # the same document (same SHA-256 as the store computes it) re-uses its input version, so that the
                # prepared System(scenario) is found in the Service cache and only System.at(T) runs again
                sha = hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
                vid = next((v["id"] for v in reversed(self.store.list_inputs(lca_project_id)) if v["sha256"] == sha), None)
                if vid is not None:
                    imp = {"project_id": lca_project_id, "input_version_id": vid, "issues": [], "unsupported": [], "reused": True}
                else:
                    imp = self.svc.import_document(doc, project_id=lca_project_id)
            else:
                imp = self.svc.import_document(doc, name=name)
            pid, vid = imp["project_id"], imp["input_version_id"]
            t1 = time.perf_counter()
            run = self.svc.calculate(pid, period, input_version_id=vid, reference_set_id=self.set_id)
            t2 = time.perf_counter()
            full = self.store.get_run(run["id"], with_results=True)
            return {"lca_project_id": pid, "input_version_id": vid, "run": run, "results": full.get("results"),
                    "reused_input_version": bool(imp.get("reused")),
                    "import_issues": imp.get("issues", [])[:20], "unsupported": imp.get("unsupported", [])[:20],
                    "timing_ms": {"import": round((t1 - t0) * 1000, 1), "calculate": round((t2 - t1) * 1000, 1)},
                    "prepared_systems": self.svc.prepared}

    def close(self):
        self.store.close()
