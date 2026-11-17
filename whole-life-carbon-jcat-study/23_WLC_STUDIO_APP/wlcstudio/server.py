"""Local HTTP server of WLC Studio: the PWA (web/) and its JSON API (/api/...), standard library only.

Security model (see docs/security.md): a single user on this machine. The server binds to a loopback
address only and refuses anything else; there is no authentication, so it must not be exposed to a network.
Every request must carry a Host header naming the loopback address and port (blocks DNS rebinding); a
state-changing request must be JSON and, when an Origin header is present, come from the same origin.
Responses carry a strict CSP, no framing, no referrer, no caching of API answers. Threads: each connection is
read in its own thread (so an idle or slow client blocks only itself), and every API call is handed to ONE worker
thread that owns the App, its SQLite connections and the engine (they are bound to one thread, and System.at()
mutates shared state), so calls never run concurrently.
"""
from __future__ import annotations

import base64
import dataclasses
import ipaddress
import json
import os
import mimetypes
import re
import sys
import time
import traceback
import urllib.parse
import queue
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

from . import APP_NAME, APP_VERSION
from . import bridge, documents, estimate, research
from . import fields as FL
from .engine import Engine
from .project import ProjectError, Projects, parse_number
from .provenance import LABEL, STATES, ProvenanceError, Uncertainty, Value
from .sources import gsi, plateau
from .sources.net import SourceError

WEB = Path(__file__).resolve().parents[1] / "web"
MAX_BODY = 40 * 1024 * 1024
# Public demo (WLCSTUDIO_PUBLIC_DEMO=1, for a hosted demo such as Render): accept the host's name instead of loopback
# only, keep the same-origin check for writes, and refuse document uploads and address lookups (no private files
# or personal data come in). Every visitor shares the same data, which a restart wipes: fictional buildings only.
PUBLIC_DEMO = os.environ.get("WLCSTUDIO_PUBLIC_DEMO") == "1"
PUBLIC_REFUSED = re.compile(r"^/api/projects/\d+/(documents|research)(/|$)")
PUBLIC_REFUSED_MSG = ("公開デモでは資料の読み込みと住所の調査は使えない（非公開の資料や個人の情報を受け取らないため）。"
                      "値は画面で入力するか、自動概算を使う")
USER_STATES = ("confirmed", "assumption", "not_applicable", "not_obtained", "not_computable")
NA_CONTEXT = tuple(f for f, F_ in FL.FIELDS.items() if F_.get("na_context"))   # 適用外 only where the value cannot act
DISCLAIMER = ("WLC Studio は研究用の試作です。計算の核は独立に作った概念モデル（70 評価単位）で、J-CAT の複製・認定品・互換品ではありません。"
              "いま登録されている原単位は架空（研究用）なので、表示される排出量は実在の建物の値ではありません。")
PRIVACY = ("入力・資料・住所はこの端末の中（var/）にだけ保存します。住所は検索のときだけ国土地理院に、座標は市区町村を調べるときだけ国土地理院に送り、"
           "端末のキャッシュには残しません（PLATEAU・統計のファイルは cache/ に残ります）。資料の原本は、起動時に残すと決めたときだけ保存します。"
           "プロジェクトを削除すると、その入力・候補・資料の記録と、計算用に変換した入力・計算の記録も消えます（削除した部分は上書きされます）。")
ATTRIBUTION = ("住所検索・逆ジオコーダ：国土地理院（地理院地図の住所検索・逆ジオコーダ）をもとに WLC Studio が加工。"
               "建物の属性：国土交通省 PLATEAU（3D 都市モデル、著作権は各地方公共団体）をもとに加工。"
               "材料の統計：国土交通省「建設資材・労働力需要実態調査」（e-Stat）をもとに作成；RASMI（Fishman ほか 2024, CC BY 4.0）。"
               "参考値：経済産業省「エネルギー消費統計調査」（e-Stat）。地盤：国土地盤情報検索サイト KuniJiban へのリンクのみ。")


METHOD_LABEL = {
    "user_entered": "手入力", "structure_card": "構造の選択画面", "initial_setting": "初期設定", "fictional_sample": "架空デモの値",
    "plateau_attribute": "PLATEAU の属性", "plateau_roof_x_storeys": "PLATEAU の屋根面積×地上階数（仮定）",
    "plateau_usage_hint": "PLATEAU の用途からの対応", "rasmi_mi_x_gfa": "RASMI の kg/m2 × 延床面積",
    "mlit_area_unit_x_gfa": "国交省の面積原単位 × 延床面積", "csv_quantity_sum": "数量表（CSV）の行の合計",
    "xlsx_quantity_sum": "数量表（Excel）の行の合計", "ifc_quantity_sum": "IFC の数量セットの合計", "pdf_text_line": "PDF の 1 行（要確認）"}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class App:
    """The API without sockets (used by the HTTP handler and by the tests)."""

    def __init__(self, var: str | Path, keep_uploads: bool = False):
        var = Path(var)
        var.mkdir(parents=True, exist_ok=True)
        self.projects = Projects(var / "projects.sqlite3", upload_dir=var / "uploads", keep_uploads=keep_uploads)
        self.engine = Engine(var / "engine.sqlite3")
        self.refset = self.engine.refset_dict()

    def close(self):
        self.projects.close()
        self.engine.close()

    # ------------------------------------------------------------------ helpers
    def _project_view(self, pid: int) -> dict:
        p = self.projects.get(pid)
        vals = self.projects.values(pid)
        later = self.projects.later(pid)
        cands = {}
        for c in self.projects.candidates(pid):
            cands.setdefault(c["field_id"], []).append(c)
        fields = {}
        for fid in FL.FIELDS:
            v = vals.get(fid)
            fields[fid] = {"value": v.to_json() if v else None,
                           "history": [h.to_json() for h in self.projects.history(pid, fid)] if v else [],
                           "candidates": cands.get(fid, []), "later": fid in later}
        label = next(s["label"] for s in FL.STRUCTURES if s["id"] == p["structure"])
        return {"id": pid, "name": p["name"], "structure": p["structure"], "structure_label": label, "data_kind": p["data_kind"],
                "created_at": p["created_at"],
                "fields": fields, "progress": self.projects.progress(pid), "last_period": p["last_period"],
                "documents": [{k: d[k] for k in ("id", "name", "kind", "size", "kept", "created_at")} for d in self.projects.documents(pid)],
                "research": self.projects.research(pid)[-20:]}

    # ------------------------------------------------------------------ routes
    def handle(self, method: str, path: str, body: dict | None) -> tuple[int, dict | list]:
        parts = [urllib.parse.unquote(p) for p in path.strip("/").split("/")][1:]       # drop "api"
        b = body or {}
        if method == "GET" and parts == ["meta"]:
            return 200, self.meta()
        if method == "GET" and parts == ["sources"]:
            return 200, estimate.registry()
        if parts[:1] == ["projects"]:
            if len(parts) == 1:
                if method == "GET":
                    return 200, [{"id": p["id"], "name": p["name"], "data_kind": p["data_kind"],
                                  "structure_label": next(s["label"] for s in FL.STRUCTURES if s["id"] == p["structure"]),
                                  "progress": self.projects.progress(p["id"])} for p in self.projects.list()]
                if method == "POST":
                    return 201, {"id": self.projects.create(str(b.get("name") or ""), str(b.get("structure") or ""))}
            pid = _int(parts[1]) if len(parts) > 1 else None
            if pid is None:
                raise ApiError(404, "そのページは無い")
            self.projects.get(pid)
            rest = parts[2:]
            if not rest:
                if method == "GET":
                    return 200, self._project_view(pid)
                if method == "DELETE":
                    # the engine copy first: if that fails the project is still there and the delete can be retried
                    lca = self.projects.get(pid)["lca_project_id"]
                    eng = self.engine.delete_project(lca)
                    out = self.projects.delete(pid)
                    out["engine"] = eng
                    return 200, out
            if rest[:1] == ["fields"] and len(rest) >= 2:
                fid = rest[1]
                if fid not in FL.FIELDS:
                    raise ApiError(404, "項目 %s は無い" % fid)
                if len(rest) == 2 and method == "PUT":
                    return 200, self.put_field(pid, fid, b)
                if rest[2:] == ["later"] and method == "POST":
                    self.projects.set_later(pid, fid, bool(b.get("later")))
                    return 200, {"ok": True}
                if rest[2:] == ["accept"] and method == "POST":
                    # by the candidate's id (a position can point at another candidate after a repeat tap)
                    cid = b.get("id")
                    if cid is not None and (not isinstance(cid, int) or isinstance(cid, bool)):
                        raise ApiError(400, "候補の番号が正しくない")
                    # adopting a candidate stores a value like a PUT: it says the same warnings (a stored 適用外 that it
                    # makes unusable)
                    before = self._na_before(pid, fid)
                    stored = self.projects.accept(pid, fid, _int(b.get("index"), 0), cid=cid)
                    return 200, self._with_na_warnings(fid, before, stored, stored.to_json())
            if rest == ["research", "address"] and method == "POST":
                return 200, self.research_address(pid, b)
            if rest == ["research", "plateau"] and method == "POST":
                return 200, self.research_plateau(pid, b)
            if rest == ["research", "plateau", "select"] and method == "POST":
                return 200, self.research_select(pid, b)
            if rest == ["estimate"] and method == "POST":
                return 200, self.estimate(pid, b)
            if rest == ["documents"] and method == "POST":
                return 200, self.document(pid, b)
            if rest == ["calculate"] and method == "POST":
                return 200, self.calculate(pid, b.get("period"))
            if rest == ["result"] and method == "GET":
                last = self.projects.last_run(pid) or {}
                if last:
                    # rebuilt for the period of that run: the document depends on T (a replacement inside T or not), so a
                    # rebuild without it would make a fresh result look stale
                    _, rep_now = bridge.build(self.projects.values(pid), self.refset, title="WLC Studio #%d" % pid,
                                              period=_float(last.get("period")))
                    last["stale"] = rep_now["input_hash"][:16] != (last.get("trace") or {}).get("入力の指紋（SHA-256 の先頭）")
                return 200, last
            if rest == ["ledger"] and method == "GET":
                # the reflection for the period of the last calculation, as GET /result (the same rows as that calculation,
                # also when it was blocked and the engine did not run); the stored period only without any run
                last = self.projects.last_run(pid) or {}
                T_ = _float(last.get("period")) if last else _float(self.projects.get(pid)["last_period"])
                doc, rep = bridge.build(self.projects.values(pid), self.refset, period=T_)
                return 200, {"fields": bridge.reflection_table(rep), "unconnected": rep["unconnected"],
                             "missing_required": rep["missing_required"], "binding_coverage": bridge.binding_coverage()}
        if method == "POST" and parts == ["demo"]:
            from .demo import create_demo
            return 201, {"id": create_demo(self.projects)}
        raise ApiError(404, "そのページは無い")

    def meta(self) -> dict:
        return {"app_name": APP_NAME, "version": APP_VERSION, "disclaimer": DISCLAIMER, "privacy": PRIVACY,
                "attribution": ATTRIBUTION, "states": LABEL, "state_order": list(STATES),
                "screens": [{"id": s["id"], "label": s["label"], "groups": s["groups"]} for s in FL.SCREENS],
                "fields": FL.meta_fields(), "structures": FL.STRUCTURES, "priority": FL.PRIORITY,
                "hero": _hero(), "methods": METHOD_LABEL,
                "refset": {"name": self.refset["name"], "version": self.refset["version"], "data_kind": self.refset["data_kind"]}}

    def put_field(self, pid: int, fid: str, b: dict) -> dict:
        state = b.get("state") or "confirmed"
        if state not in USER_STATES:
            raise ApiError(400, "手で入れられる状態は %s。統計推定・図面からの計算は候補を採用して入れる" % "・".join(LABEL[s] for s in USER_STATES))
        F = FL.FIELDS[fid]
        value = b.get("value")
        if state in ("confirmed", "assumption") and (value is None or value == ""):
            raise ApiError(400, "空欄は保存しない（未取得のまま。0 にはしない）")
        cur = self.projects.current(pid, fid)
        unit = str(b.get("unit") if b.get("unit") is not None else F.get("unit", ""))
        if cur is not None and state in ("confirmed", "assumption") and cur.state in ("confirmed", "from_drawing", "statistical", "assumption"):
            if F["type"] in ("number", "integer"):
                same = _same_value(F, value, cur.value)
            else:
                same = str(value) == str(cur.value)
            same_unit = F["type"] not in ("number", "integer") or not cur.unit or unit == cur.unit
            from_source = cur.state in ("statistical", "from_drawing") or \
                cur.method not in ("user_entered", "initial_setting", "structure_card")
            if same and same_unit and from_source:
                # an unchanged save must not turn an adopted estimate / drawing value into a typed value: that would drop
                # its source, its range and its whole-building scope (and with it the double-counting guard)
                raise ApiError(400, "値が同じなので保存しない（%sの出典・範囲を消さないため）。違う値を入れるときだけ保存する" % LABEL[cur.state])
            if same and not same_unit and from_source:
                raise ApiError(400, "%sの値の単位は付け直さない（出典の単位を変えると数値の意味が変わる）。候補を採用し直すか、"
                                    "「未取得に戻す」のあと入れ直す" % LABEL[cur.state])
            if same and not same_unit and not b.get("relabel"):
                raise ApiError(400, "数値を変えずに単位だけ変えることはしない（%s → %s）。単位の付け間違いを直すときは、"
                                    "画面の確認に答えて「単位の付け直し」として保存する" % (cur.unit, unit))
        if state == "not_applicable" and F.get("na_never"):
            raise ApiError(400, "「%s」は「適用外」にできない（無いということが無い項目）。分からないときは「未取得」のままにする" % F["label"])
        raw_scope = str(b.get("scope") or "")
        explicit = raw_scope != ""                     # "field_only" = the value covers just this field (drops a scope)
        scope = "" if raw_scope == "field_only" else raw_scope
        depends, unc, note_extra, src = {}, None, "", ""
        carry = {}                                     # provenance kept from the current value (source detail, version …)
        if cur is not None and cur.state in ("confirmed", "from_drawing", "statistical", "assumption") and state in ("confirmed", "assumption"):
            same_v = _same_value(F, value, cur.value)
            if same_v:
                # a state-only change or a relabel keeps what the value covers, its premises, its source and the fact
                # that its range is unknown (dropping them would silently drop the double-counting guard or the range note)
                if not explicit:
                    scope = cur.scope or ""
                depends = dict(cur.depends or {})
                if cur.uncertainty.kind == "unknown":
                    unc = dataclasses.replace(cur.uncertainty)
                src = cur.source_id
                carry = {"source_detail": cur.source_detail, "factor_version": cur.factor_version,
                         "retrieved_at": cur.retrieved_at, "permission": cur.permission, "note": cur.note}
            carries_estimate = cur.state == "statistical" or bool(cur.depends) or \
                (cur.uncertainty.kind == "unknown" and bool(cur.source_id))
            if b.get("from_estimate") and carries_estimate:
                # the user corrected an estimate: same quantity, same premises; its statistical range no longer applies
                if not explicit:
                    scope = cur.scope or ""
                depends = dict(cur.depends or {})
                unc = Uncertainty("unknown", basis="推定（%s）を手で直した値：元の範囲は使わない" % cur.source_id)
                note_extra = ("推定 %s %s（%s）を手で直した。" % (cur.value, cur.unit, cur.source_id)) if cur.state == "statistical" \
                    else (cur.note or "") + "（さらに %s %s から直した）" % (cur.value, cur.unit)
                src = cur.source_id
                carry = {"source_detail": cur.source_detail, "factor_version": cur.factor_version,
                         "retrieved_at": cur.retrieved_at, "permission": cur.permission}
            elif cur.scope and not explicit and not same_v:
                raise ApiError(400, "今の値は「%s」の範囲（%s）を含む。新しい値がどこまでを含むかを指定して保存する"
                                    "（同じ範囲なら scope=%s、この欄だけなら scope=field_only）"
                               % (F["label"], SCOPE_LABEL.get(cur.scope, cur.scope), cur.scope))
        if scope and not ((fid == "m_concrete" and scope == "whole_building") or (fid in ("m_rebar", "m_steel") and scope == "all_steel")):
            raise ApiError(400, "この項目にその範囲（%s）は付けられない" % scope)
        v = Value(fid, state, value if state in ("confirmed", "assumption") else None,
                  str(b.get("unit") if b.get("unit") is not None else F.get("unit", "")) if state in ("confirmed", "assumption") else "",
                  method=str(b.get("method") or "user_entered"), source_id=str(b.get("source_id") or ""),
                  source_detail=str(b.get("source_detail") or ""), note=(note_extra + str(b.get("note") or ""))[:300], updated_by="user",
                  scope=scope if state in ("confirmed", "assumption") else "",
                  depends=depends if state in ("confirmed", "assumption") else {})
        if unc is not None and state in ("confirmed", "assumption"):
            v.uncertainty = unc
        if state in ("confirmed", "assumption"):
            v.source_id = v.source_id or src
            for k, x in carry.items():
                if x and not getattr(v, k):
                    setattr(v, k, x)
        if state == "not_applicable" and F.get("na_context"):
            # 適用外 of a field that the calculation needs only in some projects (the grid factors, the route): refused here
            # when the calculation would refuse it with the other inputs as they are, with the bridge's reason; accepted
            # (and filled by the bridge) where it cannot act. A later change of the other inputs is explained by the
            # calculation in the same words
            trial = dict(self.projects.values(pid), **{fid: v})
            _, rep_ = bridge.build(trial, self.refset, title="WLC Studio #%d" % pid)
            why = (rep_.get("na_refused") or {}).get(fid)
            if why:
                raise ApiError(400, "「%s」は、いまの入力では「適用外」にできない（%s）。分からないときは「未取得」のままにする"
                               % (F["label"], why))
        before = self._na_before(pid, fid)
        stored = self.projects.put(pid, v)
        out = stored.to_json()
        if fid in ("m_concrete_fdn", "m_rebar", "m_steel"):
            self.projects.withdraw_whole_candidates(pid)
        if fid == "b_structure" and state in ("confirmed", "assumption"):
            # the project's structure follows the field (estimates, PLATEAU checks and field order use it)
            self.projects.touch(pid, structure=str(value))
        return self._with_na_warnings(fid, before, stored, out)

    def _na_before(self, pid: int, fid: str) -> tuple:
        """Before a save of `fid`: (the project's values, the 適用外 stored on the other na_context fields that the
        calculation refuses with them: field -> the bridge's reason). (None, {}) when no other na_context field holds a
        stored 適用外 — a save of `fid` cannot change that — so that nothing is built and a save stays cheap."""
        if not any(f != fid and getattr(self.projects.current(pid, f), "state", None) == "not_applicable" for f in NA_CONTEXT):
            return None, {}
        vals = self.projects.values(pid)
        return vals, self._na_refused(fid, vals)

    def _na_refused(self, fid: str, vals: dict) -> dict:
        """The 適用外 stored on the na_context fields other than `fid` (accepted when saved because it could not act) that
        the calculation refuses with these values (the bridge's na_refused): field -> reason."""
        na = [f for f in NA_CONTEXT if f != fid and getattr(vals.get(f), "state", None) == "not_applicable"]
        if not na:
            return {}
        _, rep_ = bridge.build(vals, self.refset)
        refused = rep_.get("na_refused") or {}
        return {f: refused[f] for f in na if refused.get(f)}

    def _with_na_warnings(self, fid: str, before: tuple, stored: Value, out: dict) -> dict:
        """Every save that stores a value for the user (PUT, adopting a candidate) says, in the calculation's words, a
        stored 適用外 of another na_context field that THIS save made unusable (a purchase 0 → 1000 needs the grid
        factor; a boundary set at last can need the route), instead of only when the next calculation stops. One that
        was unusable already before the save is not said again (it was said by the save that made it so, and the
        calculation says it). `before`: _na_before; the values after the save are those values with `stored` (the
        value the save stored) for `fid`, so the history is read once. No such 適用外: no `warnings` key.
        `warning_fields`: the field each sentence is about, in the same order (the screen drops a sentence whose field
        has been given another state since: a value saved later in the same 保存して戻る, 未取得に戻す); present exactly
        when `warnings` is."""
        vals, refused_before = before
        if vals is None:
            return out
        now = self._na_refused(fid, dict(vals, **{fid: Value.from_json(stored.to_json())}))
        said = [(f, "「%s」の「適用外」は、いまの入力では使えない（%s）。計算は止まる。値を入れるか「未取得」に戻す"
                 % (FL.FIELDS[f]["label"], why)) for f, why in now.items() if f not in refused_before]
        if said:
            out["warnings"] = [w for _, w in said]
            out["warning_fields"] = [f for f, _ in said]
        return out

    def research_address(self, pid: int, b: dict) -> dict:
        q = str(b.get("query") or "").strip()
        if not q:
            raise ApiError(400, "住所を入れる")
        r = gsi.geocode(q)
        self.projects.log(pid, "gsi_address_search", {"n": len(r["candidates"]), "source_id": r["source_id"], "fetched_at": r["fetched_at"]})
        return r

    def research_plateau(self, pid: int, b: dict) -> dict:
        lat, lon = _float(b.get("lat")), _float(b.get("lon"))
        if lat is None or lon is None or not (20 <= lat <= 46 and 122 <= lon <= 154):
            raise ApiError(400, "日本の範囲の緯度・経度を指定する")
        r = plateau.nearby(lat, lon)
        self.projects.log(pid, "plateau_nearby", {"city_code": r.get("city_code"), "dataset": (r.get("dataset") or {}).get("id"),
                                                  "n": len(r["candidates"]), "source_id": "plateau"})
        return r

    def research_select(self, pid: int, b: dict) -> dict:
        c = b.get("candidate") or {}
        if not isinstance(c, dict):
            raise ApiError(400, "建物の候補が無い")
        p = self.projects.get(pid)
        props, notes = research.plateau_proposals(c, p["structure"])
        good = []
        for v in props:                           # all checked first: one bad attribute must not leave a half selection
            try:
                good.append(self.projects.validate(v))
            except (ProjectError, ProvenanceError) as e:
                notes.append("「%s」は候補にしなかった：%s" % (FL.FIELDS[v.field_id]["label"], e))
        for v in good:
            self.projects.propose(pid, v, "plateau")
        n = len(good)
        self.projects.touch(pid, location_json=json.dumps({"lat": _float(b.get("lat")), "lon": _float(b.get("lon")),
                                                           "plateau_building_id": c.get("plateau_building_id")}))
        self.projects.log(pid, "plateau_select", {"plateau_building_id": c.get("plateau_building_id"), "n_proposals": n, "notes": notes})
        return {"n_proposals": n, "notes": notes}

    def estimate(self, pid: int, b: dict) -> dict:
        p = self.projects.get(pid)
        vals = self.projects.values(pid)
        sv = vals.get("b_structure")
        field = b.get("field")
        if field is not None and (not isinstance(field, str) or field not in FL.FIELDS):
            raise ApiError(400, "項目 %r は無い" % field)
        screen = b.get("screen")
        if screen is not None and not isinstance(screen, str):
            raise ApiError(400, "画面の指定が正しくない")
        target = FL.FIELDS[field]["screen"] if field else screen
        has_structure = sv is not None and sv.state in ("confirmed", "assumption", "statistical", "from_drawing")
        if target == "material" and not has_structure:
            raise ApiError(400, "構造が未取得なので材料は概算しない（基本情報で構造を入れる）")
        res = estimate.run(vals, sv.value if has_structure else None, screen=b.get("screen"), field=field,
                           demo=p["data_kind"] == "fictional_demo")
        for v in res["proposals"]:
            self.projects.propose(pid, v, "estimate:" + v.method)
        if target == "material":
            gone = self.projects.withdraw_whole_candidates(pid)
            if gone:
                res["messages"].append("前の全体量の候補（%s）は、もう一方の欄に値があるので取り下げた（二重計上を防ぐ）"
                                       % "、".join(dict.fromkeys(FL.FIELDS[f]["label"] for f in gone)))
        self.projects.log(pid, "estimate", {"screen": b.get("screen"), "field": b.get("field"), "n": len(res["proposals"]),
                                            "sources": sorted({v.source_id for v in res["proposals"]})})
        return {"n_proposals": len(res["proposals"]), "message": res["message"], "messages": res["messages"]}

    def document(self, pid: int, b: dict) -> dict:
        name = str(b.get("name") or "document")[:200]
        data_b64 = b.get("data_b64")
        if not isinstance(data_b64, str) or not data_b64:
            raise ApiError(400, "ファイルが空")
        doc_id = "doc%d-%s" % (pid, re.sub(r"[^\w.\-]", "_", name)[:40])
        r = documents.read(name, data_b64, doc_id)
        if any(d["sha256"] == r["sha256"] for d in self.projects.documents(pid)):
            raise ApiError(409, "同じ資料はもう読み込んである（二重計上を防ぐため、もう一度は読まない）")
        # every candidate is checked BEFORE anything is stored: a bad row is reported as not used instead of leaving
        # a half-imported document behind (which would also block a corrected re-upload of the same file)
        good = []
        for v in r["proposals"]:
            try:
                good.append(self.projects.validate(v))
            except (ProjectError, ProvenanceError) as e:
                r["unused"].append({"trace": v.source_detail[:80], "name": FL.FIELDS[v.field_id]["label"], "reason": str(e)})
        r["proposals"] = good
        self.projects.add_document(pid, name, r["kind"], base64.b64decode(data_b64),
                                   {"parsed": r["parsed_summary"], "n_proposals": len(good), "unused": r["unused"][:200],
                                    "warnings": r["warnings"]})
        for v in good:
            self.projects.propose(pid, v, "document:" + doc_id, extra=(r.get("evidence") or {}).get(v.field_id))
        summary = "「%s」（%s）から %d 件の候補を作った。使わなかった行 %d 件。" % (name, r["kind"], len(r["proposals"]), len(r["unused"]))
        maybe = sum((r.get("evidence") or {}).get(v.field_id, {}).get("n_maybe", 0) for v in good)
        if maybe:
            summary += "足さなかった行のうち %d 行は、足すべき行かもしれない（各候補の「足さなかった行」で理由を確かめる）。" % maybe
        # a field that got no candidate although rows of its material were left out: said, so that an empty field is
        # not taken for "nothing of that material in the file"
        lost = [(f, x) for f, x in (r.get("left_out") or {}).items() if f in FL.FIELDS and x.get("n_maybe")]
        if lost:
            summary += "候補にならなかったが、足すべきかもしれない行がある材料：%s（「使わなかった行」で理由を確かめる）。" % "、".join(
                "「%s」%d 行" % (FL.FIELDS[f]["label"], x["n_maybe"]) for f, x in lost[:8]) + ("ほか" if len(lost) > 8 else "")
        shown = r["unused"][:200]
        unused = ["%s：%s（%s）" % (u["trace"], u["name"], u["reason"]) for u in shown]
        if len(r["unused"]) > len(shown):
            unused.append("ほか %d 行（記録は最初の %d 行まで）" % (len(r["unused"]) - len(shown), len(shown)))
        return {"summary": summary, "warnings": r["warnings"], "unused": unused, "n_unused": len(r["unused"]),
                "n_proposals": len(r["proposals"])}

    def _range(self, vals: dict, T: float, lca_pid: int, pid: int, rep: dict | None = None,
               base_total: float | None = None) -> dict | None:
        """Low / high totals with every value that has a range set to the end that lowers / raises the total (two more
        engine runs): a quantity, a rate or a factor at its low end lowers it; a life, a cycle or a recovery rate at its
        HIGH end lowers it, and so does the waste rate unless the quantities are design quantities (bridge.decreasing).
        Which values are moved comes from the base report, whose partner rules already use the end of a deciding
        input's range (a cycle or a life whose range reaches below T keeps the share / loss rate). The computed total is
        always inside the range shown.
        This is a scenario width, not a probability interval; ranges that are not calibrated stay 「仮の範囲」."""
        reflected = {f["field"] for f in (rep or {}).get("fields") or [] if f.get("reflected")} if rep else None
        # only values that reach the calculation are moved to their ends and counted (a dropped foundation row, a
        # cycle without a rebuild …); inputs that cannot change the total are not counted as unknown widths
        lo_vals, n = _with(vals, "low", reflected)
        # the waste rate is moved like a life when the quantities are not design quantities (said in the note)
        waste_dec = lo_vals.get("m_waste_rate") is not vals.get("m_waste_rate") and bridge.decreasing("m_waste_rate", vals)
        # estimates whose range is not known: only statistical values and assumptions, the same set that the summary counts
        # as estimates (a confirmed value that corrected an estimate keeps the note 「元の範囲は使わない」 = kind unknown,
        # but it is not an estimate any more)
        unknown = [f for f, v in vals.items()
                   if f in FL.FIELDS and FL.FIELDS[f]["type"] in ("number", "integer") and isinstance(v.value, (int, float))
                   and (reflected is None or f in reflected) and f not in TOTAL_NEUTRAL
                   and v.state in ("assumption", "statistical") and v.uncertainty.kind in ("unknown", "none")]
        n_unknown = len(unknown)
        names = "、".join(FL.FIELDS[f]["label"] for f in sorted(unknown, key=lambda f: (f != "o_grid_value", f))[:6]) + \
            ("ほか" if n_unknown > 6 else "")
        unk_note = ("範囲が不明な推定・仮定 %d 項目（%s）の幅は含まれていない。" % (n_unknown, names)) if n_unknown else ""
        if n == 0:
            if n_unknown:
                return {"low_t": None, "high_t": None, "n_values_with_range": 0, "n_values_range_unknown": n_unknown,
                        "unknown_fields": unknown,
                        "note": "範囲が不明な推定・仮定 %d 項目（%s）があり、合計の幅は示せない。" % (n_unknown, names)}
            return None
        hi_vals, _ = _with(vals, "high", reflected)
        tot, end_gaps = {}, []
        base_omitted = {m["field"] for m in (rep or {}).get("omitted_inputs") or []}
        # gaps that are in the total but computed with an assumption, or whose split is not determined: one that appears
        # only at an end (the per-quantity delivery factor at the upper end of a 0 km range …) is said for that end too
        base_assumed = {(m["field"], m.get("gap")) for m in (rep or {}).get("missing_inputs") or []
                        if m.get("gap") in ("assumed", "split")}
        ex = (rep or {}).get("expand") or {}
        mode_unknown = bridge._never("m_transport_mode", vals.get("m_transport_mode"))
        for side, vv in (("low", lo_vals), ("high", hi_vals)):
            doc, rep_ = bridge.build(vv, self.refset, title="WLC Studio #%d (%s)" % (pid, side), period=T)
            if rep_["missing_required"]:
                # say which end and why, instead of silently showing no range
                return {"low_t": None, "high_t": None, "n_values_with_range": n, "n_values_range_unknown": n_unknown,
                        "unknown_fields": unknown,
                        "note": "範囲のある %d 項目を%s端にすると計算できない（%s）ので、合計の幅は示せない。%s"
                                % (n, "下" if side == "low" else "上", "、".join(rep_["missing_required"]), unk_note)}
            new = [m for m in rep_.get("omitted_inputs") or [] if m["field"] not in base_omitted]
            if new:
                # an end where inputs become necessary that are missing: that end is a lower bound, and it is said
                end_gaps.append("%s端では「%s」が要るが未取得（その端は下限）" % ("下" if side == "low" else "上",
                                                                      "」「".join(m["label"] for m in new[:4])))
            for m in rep_.get("missing_inputs") or []:
                if m.get("gap") not in ("assumed", "split") or (m["field"], m.get("gap")) in base_assumed:
                    continue
                g = "%s端では%s：%s" % ("下" if side == "low" else "上",
                                       "仮定で計算した分がある" if m["gap"] == "assumed" else "段階の内訳が決まらない分がある",
                                       m["reason"])
                if m["field"] == "a4_delivery_fallback" and ex.get("dist_at0") and ex.get("tkm_beyond0") and mode_unknown:
                    # the value is 0 km (A4 = 0, the mode cannot act there); above 0 km the rows whose ordered mass is known
                    # would be carried by tonne-km if the mode were given
                    g += "。運搬手段が未取得（入れると、この端の質量の分かる行は運搬距離×手段のトンキロで計算する）"
                end_gaps.append(g)
            r = self.engine.run(doc, lca_pid, T)
            res = r["results"] or {}
            tot[side] = ((res.get("SUM-03") or {}).get("value"))
        if tot["low"] is None or tot["high"] is None:
            return None
        a, b = sorted((tot["low"] / 1000.0, tot["high"] / 1000.0))
        widened = ""
        if base_total is not None and not a - 1e-9 <= base_total / 1000.0 <= b + 1e-9:
            # (a step in a life or a cycle can move against its end): the range always holds the computed total
            a, b = min(a, base_total / 1000.0), max(b, base_total / 1000.0)
            widened = "端の組み合わせが今の合計を挟まなかったので、今の合計を含むように広げた。"
        return {"low_t": a, "high_t": b, "n_values_with_range": n, "n_values_range_unknown": n_unknown, "unknown_fields": unknown,
                "end_gaps": end_gaps,
                "note": "範囲のある %d 項目を、合計を小さくする端・大きくする端にそろえたときの合計（2 回の追加計算。寿命・周期・回収率%sは"
                        "大きいほど合計が小さい）。確率の区間ではなく、校正していない範囲を含む。"
                        % (n, "・廃棄率（数量の基準が設計数量でないとき）" if waste_dec else "")
                        + widened + unk_note + ("".join(g + "。" for g in end_gaps))}

    def calculate(self, pid: int, period) -> dict:
        T = _float(period)
        if T is None or not (0 < T <= 130):
            raise ApiError(400, "評価期間は 0 より大きく 130 年以下で入れる（エンジンの年表の長さが 130 年）")
        p = self.projects.get(pid)
        vals = self.projects.values(pid)
        doc, rep = bridge.build(vals, self.refset, title="WLC Studio #%d" % pid, period=T)
        trace = {"評価期間（年）": T, "参照セット": "%s / %s（%s）" % (self.refset["name"], self.refset["version"], self.refset["data_kind"]),
                 "入力の指紋（SHA-256 の先頭）": rep["input_hash"][:16]}
        base = {"period": T, "reflection": {"summary": rep["summary"], "by_state": rep["by_state"]},
                "unconnected": rep["unconnected"], "missing_required": rep["missing_required"],
                "missing_materials": rep["missing_materials"], "missing_inputs": rep["missing_inputs"],
                "omitted_inputs": rep.get("omitted_inputs") or [],
                "assumed_inputs": [m for m in rep["missing_inputs"] if m.get("gap") in ("assumed", "split")],
                "inconsistent_inputs": rep.get("inconsistent_inputs") or [],
                "fields": bridge.reflection_table(rep),
                "factor_note": _factor_note(self.refset), "notes": rep["notes"], "double_count": rep["double_count"],
                "stale_estimates": rep.get("stale_estimates") or []}
        if rep["missing_required"]:
            out = dict(base, status="blocked", message="計算に必須の入力が足りないので計算していない（%s）" % "、".join(rep["missing_required"]),
                       summary=None, trace=trace)
            self.projects.save_run(pid, None, rep["input_hash"], T, "blocked", out)
            # the period of the last calculation, blocked or not (the screen shows it again after a reload, as it does
            # right after the calculation)
            self.projects.touch(pid, last_period=T)
            return out
        r = self.engine.run(doc, p["lca_project_id"], T, name="WLC Studio #%d" % pid)
        if p["lca_project_id"] != r["lca_project_id"]:
            self.projects.touch(pid, lca_project_id=r["lca_project_id"])
        self.projects.touch(pid, last_period=T)
        run = r["run"]
        trace.update({"エンジンの計算番号": run["id"], "入力の版": r["input_version_id"],
                      "取り込み・計算の時間（ms）": "%s / %s" % (r["timing_ms"]["import"], r["timing_ms"]["calculate"]),
                      "準備済みの計算（使い回し）": r["prepared_systems"],
                      "エンジンの版の確認": (run.get("versions") or {}).get("engine_is_verified_version")})
        if run["status"] != "ok":
            out = dict(base, status=run["status"], message=run["message"], summary=None, trace=trace)
        else:
            out = dict(base, status="ok", message="", summary=_summary(r["results"], run.get("view") or {}, rep), trace=trace,
                       checks=_checks(r["results"]))
            base_total = ((r["results"] or {}).get("SUM-03") or {}).get("value")
            out["range"] = None if out["summary"]["nothing_counted"] else \
                self._range(vals, T, r["lca_project_id"], pid, rep, base_total)
            if out["range"] and out["summary"]["lower_bound"]:
                out["range"]["lower_bound"] = True
                # with ends shown, the screen labels them 「範囲（両端とも下限）」: the note says only what the label does not.
                # With no ends (no stated range, or an end that cannot be computed) there are no ends to speak of
                out["range"]["note"] += "入っていない入力があるので、%s。" % (
                    "合計は下限" if out["range"]["low_t"] is None else "本当の合計は上端より大きいことがある")
        self.projects.save_run(pid, run["id"], rep["input_hash"], T, out["status"], out)
        return out


SCOPE_LABEL = {"whole_building": "基礎を含む建物全体", "all_steel": "鉄筋と鉄骨の全量"}


def _same_value(F: dict, value, cur_value) -> bool:
    """Is a typed value the same as the stored one? Numbers compare as numbers (a comma only as a thousands separator)."""
    if F["type"] in ("number", "integer"):
        try:
            return parse_number(value) == float(cur_value)
        except (TypeError, ValueError, OverflowError):
            return False
    return str(value) == str(cur_value)


def _hero() -> dict:
    """The home-screen photo: the user's own akabeko photo if one was placed in web/assets, else the placeholder.
    The app never pretends a photo exists (implementation directive 1)."""
    for name in ("akabeko.jpg", "akabeko.jpeg", "akabeko.png", "akabeko.webp"):
        if (WEB / "assets" / name).is_file():
            return {"src": "assets/" + name, "alt": "赤べこの写真", "placeholder": False}
    return {"src": "assets/akabeko-placeholder.svg", "alt": "赤べこの写真の差し替え用の絵（プレースホルダー）", "placeholder": True}


TOTAL_NEUTRAL = bridge.TOTAL_NEUTRAL      # cannot change the total (the split, the purchase decides, per-area values)


def _with(vals: dict, side: str, only: set | None = None) -> tuple[dict, int]:
    """The values with every numeric interval/scenario replaced by its low or high end (the others unchanged); with
    `only`, just those fields (the ones that reach the calculation)."""
    out, n = {}, 0
    for fid, v in vals.items():
        u = v.uncertainty
        if (only is None or fid in only) and fid not in TOTAL_NEUTRAL and \
                v.state in ("statistical", "assumption", "from_drawing") and u.kind in ("interval", "scenario") \
                and isinstance(v.value, (int, float)) and not isinstance(v.value, bool):
            w = Value.from_json(v.to_json())
            low_end = (side == "low") != bridge.decreasing(fid, vals)     # a longer life lowers the total
            w.value = float(u.low if low_end else u.high)
            if FL.FIELDS[fid]["type"] == "integer":
                w.value = int(round(w.value))
            out[fid] = w
            n += 1
        else:
            out[fid] = v
    return out, n


def _factor_note(refset: dict) -> str:
    if refset.get("data_kind") == "fictional":
        return ("原単位は架空の研究用セット（%s / %s）。計算の流れを確かめるためのもので、表示される排出量は実在の建物の排出量ではない。"
                "実在の建物の評価には、権利を確認した実際の原単位セットの登録が要る。" % (refset["name"], refset["version"]))
    return "原単位セット %s / %s（利用許諾の記録あり）。" % (refset["name"], refset["version"])


# engine unit -> stage it counts in (specs/system.py COMP and its feeders) and the screen fields that usually complete it
UNIT_STAGE = {"A13-01": "A1-A3", "A13-03": "A1-A3", "A13-04": "A1-A3", "X-01": "A1-A3", "A13-05": "A1-A3",
              "A4-01": "A4", "A4-02": "A4", "A5-01": "A5", "A5-02": "A5", "A5-03": "A5", "A5-04": "A5",
              "B1-02": "B1", "B1-03": "B1", "B1-04": "B1", "B2-01": "B2", "B3-01": "B3", "B4-02": "B4", "B5-01": "B5",
              "B6-01": "B6", "B6-02": "B6", "B6-03": "B6", "B6-04": "B6", "X-06": "B6", "B7-01": "B7", "B7-02": "B7",
              "B7-03": "B7", "B7-04": "B7", "C1-01": "C1", "C2-01": "C2", "C3-01": "C3", "X-14": "C3", "C4-01": "C4"}
UNIT_HINTS = {
    "A13-01": ["m_waste_rate", "m_quantity_basis"], "A4-01": ["m_transport_km", "m_transport_mode"],
    "A5-01": ["c_site_electricity", "o_grid_construction"], "A5-02": ["c_diesel"],
    "X-01": ["e_hvac_count", "e_electrical_count", "e_plumbing_count", "e_conveyance_count"], "A5-02": ["c_diesel"],
    "B1-02": ["r_charge_kg", "r_top_up", "r_leak_rate", "r_gwp"], "B1-03": ["r_charge_kg", "r_top_up", "r_loss_rate", "r_life"],
    "B1-04": ["r_charge_kg", "r_recovery_rate", "r_top_up"],
    "B2-01": ["o_fm_ratio", "o_elec_kwh", "o_pv_kwh", "o_export_kwh"],
    "B3-01": ["m_repair_rate", "e_repair_rate", "e_hvac_count", "e_electrical_count", "e_plumbing_count", "e_conveyance_count"], "B4-02": ["m_refresh_cycle", "e_hvac_life", "e_electrical_life"],
    "B5-01": ["a_reconstruction", "a_replacement_cycle", "a_recon_fraction"],
    "B6-01": ["o_elec_kwh", "o_pv_kwh", "o_export_kwh"], "B6-02": ["o_gas_m3", "o_oil_l", "o_dheat_mj"],
    "C1-01": [], "C2-01": ["a_eol_haul_km"], "C3-01": ["a_eol_route"], "C4-01": ["a_eol_route"],
    "X-14": ["e_hvac_count", "e_electrical_count", "e_plumbing_count", "e_conveyance_count", "e_hvac_mass",
             "e_electrical_mass", "e_plumbing_mass", "e_conveyance_mass"]}


MATERIAL_UNITS = {"A13-01", "A13-03", "A13-04", "A13-05", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01"}


def _hints(incomplete: list[str], rep: dict, bad_stages: set | None = None) -> list[dict]:
    """For each incomplete stage, why it is incomplete and what can complete it:
    - screen inputs that are not obtained (「未取得の入力」, with the 調べて入れる / 適用外 advice) — only for fields whose
      state is really 未取得 / 計算不能;
    - other omitted inputs with their reason (a value that is there but cannot be used, an input without a screen field);
    - when an engine unit of the stage stays incomplete and no omitted input explains it, the pointer to the parts the
      screens cannot fill (masses of m3/m2 rows …);
    - separately, what was computed with an assumption or whose split is not determined (in the total).
    `incomplete` is the engine's list AFTER the filter of the units that cannot act; only `bad_stages` are listed."""
    state = {f["field"]: f["state"] for f in rep["fields"]}
    unknown_state = ("not_obtained", "not_computable")
    todo, why, extra, advice = {}, {}, {}, {}
    for m in rep.get("missing_inputs") or []:
        gap = m.get("gap", "omitted")
        for st in m["stages"]:
            if m.get("advice") and st == m["stages"][0]:
                advice.setdefault(st, []).append(m["advice"])         # more than one way to complete it (direct stage)
            if gap == "omitted" and m["field"] in FL.FIELDS and state.get(m["field"], "not_obtained") in unknown_state:
                todo.setdefault(st, []).append(m["label"])
            elif gap == "omitted":
                why.setdefault(st, []).append("%s：%s" % (m["label"], m["reason"]))
            else:
                extra.setdefault(st, []).append(("仮定で計算：" if gap == "assumed" else "内訳：") + m["reason"])
    units = {}
    for u in incomplete:
        units.setdefault(UNIT_STAGE.get(u, "—"), []).append(u)
    out = []
    for st in [s_ for s_ in FL.STAGES_ALL if s_ in todo or s_ in units or s_ in why or s_ in extra] + (["—"] if "—" in units else []):
        if bad_stages is not None and st != "—" and st not in bad_stages:
            continue
        labels = list(dict.fromkeys(todo.get(st, [])))
        if not labels and not why.get(st):
            cand = [f for u in units.get(st, []) for f in UNIT_HINTS.get(u, []) if state.get(f, "not_obtained") in unknown_state]
            labels = list(dict.fromkeys(FL.FIELDS[f]["label"] for f in cand))
        parts = []
        if labels:
            parts.append("未取得の入力：" + "、".join(labels) + "（調べて入れる。本当に無いと分かっているときだけ「適用外」）")
        parts += list(dict.fromkeys(why.get(st, [])))
        parts += list(dict.fromkeys(advice.get(st, [])))
        if units.get(st) and not labels and not why.get(st):
            parts.append("材料の行の質量・単位など、画面の欄では埋まらない部分が欠けている（計算に反映されない入力の一覧を参照）")
        note = "。".join(p.rstrip("。") for p in parts) if parts else "入っていない分がある（計算に反映されない入力の一覧を参照）"
        also = list(dict.fromkeys(extra.get(st, [])))
        out.append({"stage": st, "unit": "、".join(units.get(st, [])) or "—", "fields": labels, "note": note,
                    "also": also})
    return out


def _summary(res: dict, view: dict, rep: dict) -> dict:
    s3 = res.get("SUM-03") or {}
    x2 = res.get("X-02") or {}
    inc = x2.get("incomplete_units") or []
    # stages of the units the engine marks incomplete, spread to the stages that depend on them (B3/B4/B5) by the same
    # rule the bridge uses for its own gaps
    ctx = rep.get("expand") or {}
    route = set(ctx.get("route_stages") or ["C3", "C4"])
    eng = {"material": set(), "equipment": set(), "other": set()}
    kept = []                              # the engine's incomplete units that can still change the total
    for u in inc:
        st = UNIT_STAGE.get(u)
        if st is None:
            kept.append(u)
            continue
        if u in ("C3-01", "C4-01") and st not in route:
            continue                       # the material rows' treatment goes to the other C stage on this route
        if u == "B1-03" and not ctx.get("b1_replacement", True):
            continue                       # no refrigerant replacement falls inside T: its loss rate cannot act
        if u == "B2-01" and ctx.get("b2_moot"):
            continue                       # net purchased electricity is 0: the facility-management share cannot act
        if u == "B2-01" and "B2" in (rep.get("split_stages") or []):
            continue                       # share unknown: B2 is counted inside B6 (a split, reported as such)
        if u == "B5-01" and not ctx.get("b5", False):
            continue                       # no refurbishment / rebuild with a share falls inside T
        if u in ("A4-01", "A4-02") and ctx.get("dist0"):
            continue                       # 0 km: A4 is 0 whatever the masses
        if u == "C2-01" and ctx.get("haul0"):
            continue                       # 0 km haul: C2 is 0 whatever the masses
        if u == "B3-01" and ctx.get("mrep0") and ctx.get("erep0"):
            continue                       # both repair rates are 0: B3 is 0
        kept.append(u)
        kind = "material" if u in MATERIAL_UNITS else ("equipment" if u in ("X-01", "X-14") else "other")
        eng[kind].add(st)
    spread = set()
    # the same "surely 0 multiplier" rule as the bridge: 0 km (A4), 0 haul (C2), repair rate 0 (B3) per kind of row
    zero = {"material": {s_ for s_, z in (("A4", ctx.get("dist0")), ("C2", ctx.get("haul0")), ("B3", ctx.get("mrep0"))) if z},
            "equipment": {"B3"} if ctx.get("erep0") else set(), "other": set()}
    for kind, sts in eng.items():
        c = dict(ctx, b4_equipment=ctx.get("b4_equipment_gap", ctx.get("b4_equipment"))) if kind == "equipment" else ctx
        spread |= set(bridge.expand_stages([x for x in sts if x not in zero[kind]], c, kind)) - zero[kind]
    bad_stages = (spread & set(rep["stages"] or [])) | set(rep.get("incomplete_stages") or [])
    assumed = set(rep.get("assumed_stages") or [])
    split = set(rep.get("split_stages") or [])
    stages = [{"stage": k, "value": v, "complete": k not in bad_stages, "assumed": k in assumed, "split": k in split}
              for k, v in (x2.get("by_stage") or {}).items() if k in (rep["stages"] or [])]
    x7 = res.get("X-07") or {}
    by_year = x7.get("by_year") or []
    start = None
    for f in rep["fields"]:
        if f["field"] == "b_completion_year" and f["reflected"]:
            start = True
    rows = [[i + 1, v] for i, v in enumerate(by_year)]
    total = s3.get("value")
    # the engine's total is short only when an incomplete unit that can act is left (or the engine names none)
    engine_short = not s3.get("complete") and (bool(kept) or not inc)
    omitted = [m for m in rep.get("missing_inputs") or [] if m.get("gap", "omitted") == "omitted"]
    return {"total_kg": total, "total_t": None if total is None else total / 1000.0,
            "per_area": (res.get("SUM-04") or {}).get("value"), "per_area_year": (res.get("SUM-05") or {}).get("value"),
            "complete": not engine_short and not rep.get("missing_inputs"),
            "engine_complete": bool(s3.get("complete")), "incomplete_units": kept, "engine_incomplete_units": inc,
            "hints": _hints(kept, rep, bad_stages),
            "incomplete_stages": sorted(st for st in bad_stages if st),
            "stages": stages, "by_year": rows, "year_axis": "評価期間の年（1 年目〜）",
            "source_keys": "SUM-03.value、X-02.by_stage、X-07.by_year、SUM-04/05.value",
            # a lower bound only when something is LEFT OUT; a value computed with an assumption is not an omission
            "lower_bound": bool(rep["missing_materials"] or omitted) or engine_short,
            "assumed_stages": sorted(assumed),
            "split_stages": sorted(split),
            # nothing that carries emissions reached the engine: the headline must not read as a real 0
            "nothing_counted": not total}


def _checks(res: dict) -> list[dict]:
    out = []
    for k in ("SYS-01", "SYS-02", "SYS-03", "SYS-04", "QA-01", "QA-02", "QA-03", "QA-04", "C-05"):
        r = res.get(k)
        if isinstance(r, dict):
            out.append({"id": k, "ok": r.get("ok"), "n_violations": len(r.get("violations") or []),
                        "examples": (r.get("violations") or [])[:5], "counts": r.get("counts")})
    return out


def _int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def _float(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


# ---------------------------------------------------------------------------------------------- HTTP
# style attributes are set by the page (bar widths); scripts stay strictly same-origin (no inline script)
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


class AppWorker:
    """Runs the App in one dedicated thread; HTTP threads hand it (method, path, body) and wait for the answer."""

    def __init__(self, var, keep_uploads: bool = False):
        self.q: queue.Queue = queue.Queue()
        self.ready = threading.Event()
        self.error = None
        self.t = threading.Thread(target=self._run, args=(var, keep_uploads), name="wlcstudio-app", daemon=True)
        self.t.start()
        self.ready.wait()
        if self.error:
            raise self.error

    def _run(self, var, keep_uploads):
        try:
            self.app = App(var, keep_uploads=keep_uploads)
        except BaseException as e:            # reported to the caller of __init__
            self.error = e
            self.ready.set()
            return
        self.ready.set()
        while True:
            job = self.q.get()
            if job is None:
                self.app.close()
                return
            args, box, done = job
            try:
                box["out"] = self.app.handle(*args)
            except BaseException as e:
                box["err"] = e
            done.set()

    def handle(self, method, path, body):
        box, done = {}, threading.Event()
        self.q.put(((method, path, body), box, done))
        done.wait()
        if "err" in box:
            raise box["err"]
        return box["out"]

    def stop(self):
        self.q.put(None)
        self.t.join(timeout=10)


def make_handler(app, port: int):
    """`app` is anything with handle(method, path, body): the App itself (tests) or an AppWorker (the server)."""
    allowed_hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port, "[::1]:%d" % port}

    class H(BaseHTTPRequestHandler):
        server_version = "WLCStudio/" + APP_VERSION
        sys_version = ""
        timeout = 10                                 # an idle connection is dropped (it only ever blocks its own thread)

        def log_message(self, fmt, *args):          # no request bodies, no addresses in the log
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

        def _send(self, status, payload, ctype="application/json; charset=utf-8", cache="no-store"):
            data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _guard(self) -> bool:
            host = self.headers.get("Host", "")
            if PUBLIC_DEMO:
                if not host:
                    self._send(400, {"error": "Host が無い"})
                    return False
                if self.command in ("POST", "PUT", "DELETE"):
                    origin = self.headers.get("Origin")
                    if origin is not None and urllib.parse.urlparse(origin).netloc != host:
                        self._send(403, {"error": "別のサイトからの書き込みは受け付けない"})
                        return False
                    if self.command != "DELETE" and not (self.headers.get("Content-Type", "").startswith("application/json")):
                        self._send(415, {"error": "JSON で送る"})
                        return False
                    if PUBLIC_REFUSED.match(urllib.parse.urlparse(self.path).path):
                        self._send(403, {"error": PUBLIC_REFUSED_MSG})
                        return False
                return True
            if host not in allowed_hosts:
                self._send(421, {"error": "この Host は受け付けない（ローカル専用）"})
                return False
            if self.command in ("POST", "PUT", "DELETE"):
                origin = self.headers.get("Origin")
                if origin is not None and urllib.parse.urlparse(origin).netloc not in allowed_hosts:
                    self._send(403, {"error": "別のサイトからの書き込みは受け付けない"})
                    return False
                if self.command != "DELETE" and not (self.headers.get("Content-Type", "").startswith("application/json")):
                    self._send(415, {"error": "JSON で送る"})
                    return False
            return True

        def _api(self):
            body = None
            if self.command in ("POST", "PUT"):
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    return self._send(400, {"error": "Content-Length が不正"})
                if n < 0:
                    return self._send(400, {"error": "Content-Length が不正"})
                if n > MAX_BODY:
                    return self._send(413, {"error": "大きすぎる（40 MB まで）"})
                raw = self.rfile.read(n) if n else b""
                try:
                    body = json.loads(raw.decode("utf-8")) if raw else {}
                except (UnicodeDecodeError, ValueError, RecursionError):   # also over-long integer literals, deep nesting
                    return self._send(400, {"error": "JSON として読めない"})
                if not isinstance(body, dict):
                    return self._send(400, {"error": "JSON のオブジェクトで送る"})
            try:
                status, out = app.handle(self.command, urllib.parse.urlparse(self.path).path, body)
                self._send(status, out)
            except ApiError as e:
                self._send(e.status, {"error": str(e)})
            except (ProjectError, ProvenanceError, ValueError, SyntaxError, IndexError, OverflowError) as e:   # SyntaxError: XML ParseError
                self._send(400, {"error": "読めない・正しくない入力：%s" % e if isinstance(e, (SyntaxError, IndexError)) else str(e)})
            except SourceError as e:
                self._send(502, {"error": str(e)})
            except Exception:                        # details go to the local log only
                traceback.print_exc()
                self._send(500, {"error": "内部エラー（端末のログを見る）"})

        def _static(self):
            path = urllib.parse.urlparse(self.path).path
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            f = (WEB / rel).resolve()
            if WEB.resolve() not in f.parents or not f.is_file():
                return self._send(404, {"error": "無い"})
            ctype = "application/manifest+json" if f.suffix == ".webmanifest" else (mimetypes.guess_type(f.name)[0] or "application/octet-stream")
            if ctype.startswith("text/") or ctype in ("application/javascript",):
                ctype += "; charset=utf-8"
            self._send(200, f.read_bytes(), ctype, cache="no-cache")

        def do_GET(self):
            if not self._guard():
                return
            if self.path.startswith("/api/"):
                return self._api()
            return self._static()

        def do_HEAD(self):
            self.do_GET()

        def do_POST(self):
            if self._guard():
                self._api() if self.path.startswith("/api/") else self._send(404, {"error": "無い"})

        do_PUT = do_POST
        do_DELETE = do_POST

    return H


def serve(var: str | Path, host: str = "127.0.0.1", port: int = 8770, keep_uploads: bool = False) -> None:
    try:
        if not PUBLIC_DEMO and not ipaddress.ip_address(host).is_loopback:
            raise SystemExit("ループバック（127.0.0.1 / ::1）以外では起動しない。認証の無いこの版を外部に公開しないこと（docs/security.md）")
    except ValueError:
        if host != "localhost":
            raise SystemExit("ホスト名は localhost か 127.0.0.1 にする") from None
    from .sources.net import sweep
    sweep()
    worker = AppWorker(var, keep_uploads=keep_uploads)
    import socket

    class _Server(ThreadingHTTPServer):
        daemon_threads = True
        address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
    httpd = _Server((host, port), make_handler(worker, port))
    print("WLC Studio %s: http://%s:%d/ （止めるには Ctrl+C）" % (APP_VERSION, "127.0.0.1" if host == "localhost" else host, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        worker.stop()
