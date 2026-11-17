# -*- coding: utf-8 -*-
"""70 評価単位の台帳（data/units70.json）の検査と、台帳の式の照合。

  (a) 構造：単位がちょうど 70、ID が一意、台帳の式（実行形 eval_py）が読む単位がすべて台帳にあり宣言された依存に含まれる、
      依存に循環が無い、入力の項目の名前が生成器のデータモデルで解決できる、依存の辺の表（data/unit_dependencies.csv）の
      端点が解決できる、構成表の行（composition）を持つ単位がちょうど DIRECT の単位で 22 行、式（LaTeX）が空でない。
  (b) 照合：台帳の式の実行形（JSON の helpers_py と各単位の eval_py）を、凍結した生成器の無作為のシナリオ（台帳のために
      新しく選んだ種）・名前付きの境界条件・欠陥入り・特殊条件で評価し、研究のエンジン（第 10 章の統一系
      tstudy.unified.System.at。読み取り専用で import）と、全単位の公開出力キーを葉ごとに比べる（--ref で凍結した基準計算とも）。
  (c) T の形（--time-probe）：直接寄与する単位について、区切り点の間の区間で 3 点が一直線に並ぶこと（区分一次）、
      T によらない単位が T を変えても同じ値であること、SUM-05 は T·値が一次であることを台帳の式で確かめる。
  (d) 独立の評価：02 の LaTeX の式・条件・記号（2 節）を、eval_py も基準計算も見ずに手で写した別の実装（このファイルの
      「独立の評価」の節、関数 run・run_all）で全 70 単位の公開出力を作り、(b) と同じ組で統一系と比べる。
  (e) 節点と跳び（--knots）：事象の切り替え点 sw(τ) と整数年そのもの、その直前・直後の浮動小数、τ 自身、τ と sw(τ) の中点で、
      統一系・eval_py・独立の評価（--ref で基準計算も）を比べ、跳び V(b)-V(b の直前) を比べ、時間の形から求めた跳びの理論値
      （B4-02・B5-01・B3-01・B1-03・B1-04・SUM-03）と、跳ばないはずの単位の連続性を確かめる。整数の時刻の事象の直後の帯
      (K, sw(K)) は未解決の切り替え境界（17 章 03 の TH-2 の 3）として別に数える。
  (f) 入力の感度（--sensitivity）：入力の項目を 1 か所ずつ動かして統一系の公開出力が変わった単位について、その項目が
      宣言した入力（inputs_direct・inputs_notation、依存の閉包を含む）と統一系の記録（inputs_reached）にあるかを調べる。
  (g) 整合：構成表の行が仕様（specs/system.py COMP_ROWS）と一致、AUXILIARY は直接寄与する単位の入力になる、
      REFERENCE・BREAKDOWN・DECISION は C(T) の依存の閉包に入らない、X-02 の完全性の対が仕様と一致、出力キーの集合が
      統一系と一致、独立の評価が読んだ単位が宣言された依存の閉包に入る。

使い方（作業木のどこからでも。python3 -B、WLCSTUDIO_OFFLINE=1。研究コードは読むだけで書き換えない）：
    python3 -B tools/check_units70.py [--n 40] [--seed 880001] [--ref] [--time-probe 8] [--knots 6] [--sensitivity 2] [--json OUT.json]

比較の規則は第 11 章と同じ（checks/check_msp_pre_a.py の compare）：数値は相対差 1e-9 以内、基準が厳密に 0 なら厳密に 0、
真偽値・整数・文字列・None・一覧の長さ・辞書のキーは型を含めて完全一致。浮動小数どうしの標本照合（証拠の区分 F）であり、
厳密な算術の照合でも統計的な上限でもない。架空データで、現実の建物の予測精度は意味しない。
"""
import argparse
import copy
import csv
import json
import math
import os
import random
import re
import sys
import time
import typing

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, ".."))
STUDY = os.path.normpath(os.path.join(BASE, ".."))
RC = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code")
TOL = 1e-9
EPS = 1e-9


# ---------------------------------------------------------------- 台帳の読み込みと実行形
def load_ledger(path):
    return json.load(open(path, encoding="utf-8"))


def eval_refs(code, ids):
    return set(re.findall(r'"([A-Z0-9]+-[0-9]+)"', code)) & set(ids)


def topo(units):
    deps = {u["id"]: list(u["depends_on_units"]) for u in units}
    order, state = [], {}

    def visit(u, stack):
        if state.get(u) == 2:
            return
        if state.get(u) == 1:
            raise ValueError("cycle: " + " -> ".join(stack + [u]))
        state[u] = 1
        for d in deps[u]:
            visit(d, stack + [u])
        state[u] = 2
        order.append(u)

    for u in sorted(deps):
        visit(u, [])
    return order


class Ledger:
    """台帳の式（eval_py）を位相順に実行する。"""

    def __init__(self, L, baselines):
        self.L = L
        self.order = topo(L["units"])
        self.code = {u["id"]: compile(u["eval_py"], "units70.json:" + u["id"], "exec") for u in L["units"]}
        self.H = {}
        exec(compile(L["helpers_py"], "units70.json:helpers", "exec"), self.H)
        self.baselines = baselines

    def run(self, x, T, only=None):
        U = {}
        need = self.order if only is None else [u for u in self.order if u in only]
        for u in need:
            ns = dict(self.H)
            ns.update(x=x, T=T, U=U, BASELINES=self.baselines,
                      LEDGER_SUM03=lambda b: self.run(b, b.boundary.study_period)["SUM-03"]["value"])
            exec(self.code[u], ns)
            U[u] = ns["out"]
        return U


def closure(L, targets):
    deps = {u["id"]: u["depends_on_units"] for u in L["units"]}
    out, st = set(), list(targets)
    while st:
        u = st.pop()
        if u in out:
            continue
        out.add(u)
        st.extend(deps[u])
    return out


# ---------------------------------------------------------------- 比較（第 11 章と同じ規則）
class Acc:
    __slots__ = ("n_values", "n_mismatch", "max_rel", "n_float", "n_bit", "examples", "pairs")

    def __init__(self):
        self.n_values = self.n_mismatch = self.n_float = self.n_bit = self.pairs = 0
        self.max_rel = 0.0
        self.examples = []

    def bad(self, sid, path, got, want, why):
        self.n_mismatch += 1
        if len(self.examples) < 5:
            self.examples.append({"pair": sid, "path": path, "got": repr(got)[:120], "want": repr(want)[:120], "why": why})


def compare(got, want, path, acc, sid):
    if isinstance(want, dict):
        if not isinstance(got, dict):
            acc.bad(sid, path, type(got).__name__, "dict", "not a dictionary")
            return
        if set(got) != set(want):
            acc.bad(sid, path, sorted(map(str, got)), sorted(map(str, want)), "keys differ")
        for k in want:
            if k in got:
                compare(got[k], want[k], "%s/%s" % (path, k), acc, sid)
    elif isinstance(want, (list, tuple)):
        if not isinstance(got, (list, tuple)) or len(got) != len(want):
            acc.bad(sid, path, len(got) if isinstance(got, (list, tuple)) else type(got).__name__, len(want), "length differs")
            return
        for i, (g, w) in enumerate(zip(got, want)):
            compare(g, w, "%s[%d]" % (path, i), acc, sid)
    elif want is None or isinstance(want, (bool, str, int)) and not isinstance(want, float):
        acc.n_values += 1
        if type(got) is not type(want) or got != want:
            acc.bad(sid, path, got, want, "exact comparison failed")
    elif isinstance(want, float):
        acc.n_values += 1
        if not isinstance(got, float) or isinstance(got, bool):
            acc.bad(sid, path, got, want, "not a float")
            return
        if math.isnan(want) or math.isinf(want):
            if not (got == want or (math.isnan(got) and math.isnan(want))):
                acc.bad(sid, path, got, want, "non-finite")
            return
        if want == 0.0:
            if got != 0.0:
                acc.bad(sid, path, got, want, "reference is zero")
            return
        acc.n_float += 1
        if got == want:
            acc.n_bit += 1
        rel = abs(got - want) / abs(want)
        acc.max_rel = max(acc.max_rel, rel)
        if rel > TOL:
            acc.bad(sid, path, got, want, "relative %.3e" % rel)
    else:
        acc.n_values += 1
        if got != want:
            acc.bad(sid, path, got, want, "other type")


def public(d):
    return {k: v for k, v in d.items() if not str(k).startswith("_")}


# ---------------------------------------------------------------- (a) 構造の検査
def resolve_field(path, model):
    """unit_map の「表.列」の名前を生成器のデータモデルで解決する（#＝個数・有無、.value＝一覧の要素、.key＝辞書のキー、
    ~h・~t＝単位の文字列の頭・尾、__no_value__＝行の存在）。"""
    if path.endswith(".__no_value__"):
        path = path[: -len(".__no_value__")]
    path = re.sub(r"~[ht]$", "", path)
    parts = path.split(".")
    tp = model.Scenario
    for i, p in enumerate(parts):
        p = p.rstrip("#")
        if p in ("value", "key") and i == len(parts) - 1:
            return True
        if not hasattr(tp, "__dataclass_fields__"):
            return False
        hints = typing.get_type_hints(tp)
        if p not in hints:
            return False
        tp = hints[p]
        while True:
            org = typing.get_origin(tp)
            args = typing.get_args(tp)
            if org is typing.Union or (org is not None and str(org).endswith("UnionType")):
                tp = [a for a in args if a is not type(None)][0]
                continue
            if org in (list, tuple):
                tp = args[0]
                continue
            if org is dict:
                tp = args[1]
                if i + 1 < len(parts) and parts[i + 1] in ("key", "value"):
                    return True
                continue
            break
    return True


def structure_checks(L, model, deps_csv):
    ids = [u["id"] for u in L["units"]]
    res, problems = {}, []
    res["単位の数"] = len(ids)
    if len(ids) != 70:
        problems.append("units: %d (expected 70)" % len(ids))
    res["ID の重複"] = len(ids) - len(set(ids))
    if res["ID の重複"]:
        problems.append("duplicate ids")
    unres = [(u["id"], d) for u in L["units"] for d in u["depends_on_units"] if d not in ids]
    res["解決できない依存"] = len(unres)
    problems += ["unresolved dependency %s <- %s" % x for x in unres]
    undecl = [(u["id"], d) for u in L["units"] for d in eval_refs(u["eval_py"], ids) - set(u["depends_on_units"]) - {u["id"]}]
    res["式が読むが宣言に無い依存"] = len(undecl)
    problems += ["undeclared dependency %s <- %s" % x for x in undecl]
    try:
        topo(L["units"])
        res["依存の循環"] = 0
    except ValueError as ex:
        res["依存の循環"] = 1
        problems.append(str(ex))
    fields = set()
    for u in L["units"]:
        fields |= {x["path"] for x in u["inputs_direct"]}
        fields |= set(u["inputs_reached"])
    bad_f = sorted(f for f in fields if not resolve_field(f, model))
    res["入力の項目（解決できたもの／全体）"] = "%d/%d" % (len(fields) - len(bad_f), len(fields))
    problems += ["unresolved input field %s" % f for f in bad_f]
    n_edges, bad_e = 0, []
    with open(deps_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            n_edges += 1
            for end in (row["from"], row["to"]):
                if end.startswith("input:"):
                    if not resolve_field(end[6:], model):
                        bad_e.append(end)
                elif end not in ids:
                    bad_e.append(end)
    res["依存の辺（解決できたもの／全体）"] = "%d/%d" % (n_edges - len(bad_e), n_edges)
    problems += ["unresolved edge end %s" % e for e in sorted(set(bad_e))]
    comp_units = sorted(u["id"] for u in L["units"] if u["composition"])
    direct = sorted(u["id"] for u in L["units"] if u["role"] == "DIRECT")
    n_rows = sum(len(u["composition"]) for u in L["units"])
    res["構成表の行（単位／行）"] = "%d/%d" % (len(comp_units), n_rows)
    if comp_units != direct or n_rows != 22 or len(direct) != 21:
        problems.append("composition rows do not match the DIRECT units (21 units, 22 rows)")
    empty = [u["id"] for u in L["units"] if not u["formula_latex"].strip() or not u["eval_py"].strip()]
    res["式が空の単位"] = len(empty)
    problems += ["empty formula %s" % u for u in empty]
    return res, problems


# ---------------------------------------------------------------- 事象と区切り点（(c) のため）
def event_times(x, H):
    out = set()

    def per(c):
        if c is None or isinstance(c, bool) or not (c > 0.0) or math.isinf(c):
            return
        n = 1
        while n * c < H:
            out.add(n * c)
            n += 1
    for r in x.materials:
        per(r.refresh_cycle)
    for q in x.equipment:
        if q.replacement_event_list is not None:
            out.update(float(t) for t in q.replacement_event_list if t > 0)
        else:
            per(q.service_life)
    for d in x.refrigerants:
        if d.change_years is not None:
            out.update(float(t) for t in d.change_years if t > 0)
        else:
            per(d.service_life)
    per(x.boundary.replacement_cycle)
    return out


def breakpoints(x, H):
    b = set(float(k) for k in range(0, int(H) + 1))
    for t in event_times(x, H):
        b.add(t)
        b.add(t / (1.0 - EPS))
    return sorted(v for v in b if 0.0 <= v <= H)




# =====================================================================================================
# (d) 独立の評価：02 の式（LaTeX）・条件・2 節の記号を手で写した別の実装。eval_py・基準計算（refcalc）・統一系の仕様は
#     使わない（読むのは生成器の入力 x と評価期間 T だけ）。X-04 の行・QA-03 の使用・SYS-01〜03 の箇所の表・B4-02 の
#     n_partial・X-02 の CHK は、02 にこの照合で書き足した定義（統一系の仕様を読んで精密にした）に従う。
#     run(x, T) は SUM-08・X-04・X-05・QA-01・QA-03・SYS-01〜03・n_partial・complete を除く単位、run_all はその全部。
#     戻り値の第 2 要素 reads は、単位ごとに独立の評価が読んだ上流の単位（依存の整合 (g) に使う）。
# =====================================================================================================
PP = "PERMITTED_PUBLIC"
STAGES = ("A1-A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4")


def num(v):
    return v is not None and not isinstance(v, bool) and isinstance(v, (int, float)) and not math.isnan(v)


def ge0(v):
    return num(v) and 0.0 <= v < math.inf


def gt0(v):
    return num(v) and 0.0 < v < math.inf


def in01(v):
    return num(v) and 0.0 <= v <= 1.0


def th(T, tau):
    return tau < T * (1.0 - EPS)


def w(T, k):                      # w_k(T) = clip(T-k, 0, 1)
    return max(0.0, min(1.0, T - k))


def kcell(tau):                   # k_tau
    return max(1, math.ceil(tau * (1.0 - EPS))) - 1


def Eper(T, c):
    if not gt0(c):
        return []
    out, n = [], 1
    while th(T, n * c):
        out.append(n * c)
        n += 1
    return out


def Elst(T, L):
    return [float(t) for t in L if t > 0 and th(T, t)]


def cv(x, a, b, extra=()):
    if a is None or b is None:
        return None
    if a == b:
        return 1.0
    for c in extra:
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    for c in x.unit_conversions:
        if c.from_unit == a and c.to_unit == b:
            return c.factor
    return None


def G(x, s, f, u, extra=()):
    if f is None or f not in x.factors:
        return False
    r = x.factors[f]
    return r.licence_status == PP and list(r.stages) == [s] and cv(x, u, r.unit, extra) is not None


def FF(x, s, f, u, extra=()):     # ゲート付きの換算済み係数（ゲートが偽なら None）
    if not G(x, s, f, u, extra):
        return None
    r = x.factors[f]
    return cv(x, u, r.unit, extra) * r.value


def aunit(u):
    h, s, t = (u or "").partition("/")
    return h if s and t == "year" else None


def gunit(g):
    h, s, t = (g.unit or "").partition("/")
    return t if s and h == "kgCO2e" and t else None


def vk(p, Y):
    if p.kind == "CONSTANT" and p.base is not None:
        return [p.base for _ in range(Y)]
    if p.kind == "LINEAR_TREND" and p.base is not None and p.slope is not None:
        return [p.base + p.slope * k for k in range(Y)]
    return [p.table[k] for k in range(Y)]


def same(v, t):
    return all(a == b or abs(a - b) <= 1e-12 * max(abs(a), abs(b)) for a, b in zip(v, t))


def run(x, T, keep=False):
    R = {}
    reads = {}
    cur = [None]

    def U(uid):
        reads.setdefault(cur[0], set()).add(uid)
        return R[uid]

    Y = math.ceil(T)
    H = len(x.operation.grid.table)
    M, EQ, D = x.materials, x.equipment, x.refrigerants
    inc = set(x.boundary.included_lifecycle_stages)
    iota = {s: (1 if s in inc else 0) for s in STAGES}

    def unit(uid):
        cur[0] = uid
        reads.setdefault(uid, set())

    # ---------------- A13-05
    unit("A13-05")
    qo, qi, nsk = [], [], 0
    for r in M:
        ok = ge0(r.quantity) and num(r.waste_rate) and 0.0 <= r.waste_rate < 1.0
        if not ok:
            qo.append(None); qi.append(None); nsk += 1
            continue
        Q, wr = r.quantity, r.waste_rate
        if r.quantity_basis == "DESIGN":
            qo.append(Q * (1.0 / (1.0 - wr))); qi.append(Q)
        else:
            qo.append(Q); qi.append(Q * (1.0 - wr))
    R["A13-05"] = {"q_ord": qo, "q_inst": qi, "n_skipped": nsk}

    # ---------------- A13-02
    unit("A13-02")
    fc, ninv = [], 0
    for r in M:
        if r.composition is None:
            fc.append(None); continue
        ok = all(G(x, "A1-A3", c.factor_id, "kg") and ge0(c.mass_fraction) for c in r.composition) and \
            abs(sum(c.mass_fraction for c in r.composition) - 1.0) <= 1e-6 if all(ge0(c.mass_fraction) for c in r.composition) else False
        if not ok:
            fc.append(None); ninv += 1; continue
        fc.append(sum(c.mass_fraction * FF(x, "A1-A3", c.factor_id, "kg") for c in r.composition))
    R["A13-02"] = {"by_item": fc, "n_invalid": ninv}

    # ---------------- X-15
    unit("X-15")
    kinds, fstar, cstar, nun, ndec = [], [], [], 0, 0
    Fc = U("A13-02")["by_item"]
    for i, r in enumerate(M):
        E = False
        e = r.epd
        if e is not None and e.factor_id in x.factors:
            f = x.factors[e.factor_id]
            E = (list(e.declared_stages) == list(f.stages) and e.declared_unit == f.unit and e.valid_until == f.valid_until
                 and f.valid_until is not None and not (f.valid_until < x.project.assessment_date)
                 and G(x, "A1-A3", e.factor_id, r.quantity_unit, r.conversions))
        if e is not None and not E:
            ndec += 1
        if E:
            f = x.factors[e.factor_id]
            kinds.append("EPD"); fstar.append(f.value); cstar.append(cv(x, r.quantity_unit, f.unit, r.conversions))
        elif r.composition is not None:
            c = cv(x, r.quantity_unit, "kg", r.conversions)
            if Fc[i] is not None and c is not None:
                kinds.append("COMPOSITE"); fstar.append(Fc[i]); cstar.append(c)
            else:
                kinds.append(None); fstar.append(None); cstar.append(None); nun += 1
        elif G(x, "A1-A3", r.factor_id, r.quantity_unit, r.conversions):
            f = x.factors[r.factor_id]
            kinds.append("GENERIC"); fstar.append(f.value); cstar.append(cv(x, r.quantity_unit, f.unit, r.conversions))
        else:
            kinds.append(None); fstar.append(None); cstar.append(None); nun += 1
    R["X-15"] = {"kind": kinds, "factor": fstar, "conv": cstar, "n_unresolved": nun, "n_epd_declined": ndec}

    # ---------------- A13-01 / A13-03
    for uid, pick in (("A13-01", ("GENERIC", "COMPOSITE")), ("A13-03", ("EPD",))):
        unit(uid)
        X = U("X-15"); q = U("A13-05")["q_ord"]
        bi, nsk = [], 0
        for i in range(len(M)):
            k = X["kind"][i]
            if uid == "A13-01" and k is None:
                nsk += 1; bi.append(0.0); continue
            if k in pick:
                if q[i] is None:
                    nsk += 1; bi.append(0.0); continue
                bi.append(q[i] * X["conv"][i] * X["factor"][i])
            else:
                bi.append(0.0)
        R[uid] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}

    # ---------------- A13-04
    unit("A13-04")
    a01, a03 = U("A13-01")["by_item"], U("A13-03")["by_item"]
    bi, nsk = [], 0
    for i, r in enumerate(M):
        ru = r.unquantified_cost_ratio
        if num(ru) and 0.0 < ru < 1.0:
            bi.append((a01[i] + a03[i]) * (ru / (1.0 - ru)))
        else:
            bi.append(0.0)
            if not (ru is None or (num(ru) and ru == 0.0)):
                nsk += 1
    R["A13-04"] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}

    # ---------------- X-01
    unit("X-01")
    bi, nsk = [], 0
    for q in EQ:
        F = FF(x, "A1-A3", q.factor_id, q.quantity_unit)
        if ge0(q.quantity) and F is not None:
            bi.append(q.quantity * F)
        else:
            bi.append(0.0); nsk += 1
    R["X-01"] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}

    # ---------------- X-03
    unit("X-03")
    X = U("X-15"); q = U("A13-05")["q_ord"]
    mass, em = {}, {}
    for i, r in enumerate(M):
        if X["kind"][i] == "COMPOSITE" and q[i] is not None:
            for c in r.composition:
                f = c.factor_id
                m = q[i] * X["conv"][i] * c.mass_fraction
                mass[f] = mass.get(f, 0.0) + m
                em[f] = em.get(f, 0.0) + m * FF(x, "A1-A3", f, "kg")
    R["X-03"] = {"value": math.fsum(em.values()), "mass_by_component": mass, "emission_by_component": em}

    # ---------------- X-13
    unit("X-13")
    A = U("A13-05")
    net, wst = [], []
    for i, r in enumerate(M):
        if A["q_ord"][i] is not None and in01(r.reuse_rate):
            wv = (A["q_ord"][i] - A["q_inst"][i]) * (1.0 - r.reuse_rate)
            wst.append(wv); net.append(A["q_inst"][i] + wv)
        else:
            wst.append(None); net.append(None)
    R["X-13"] = {"by_item": net, "waste_by_item": wst}

    # ---------------- X-16
    unit("X-16")
    bi, nsk = [], 0
    for c in x.cost_items:
        Ip, Ib = x.price_index.get(c.price_year), x.price_index.get(c.factor_base_year)
        F = FF(x, "A1-A3", c.factor_id, c.currency)
        if ge0(c.amount) and gt0(Ip) and gt0(Ib) and F is not None:
            bi.append(c.amount * (Ib / Ip) * F)
        else:
            bi.append(0.0); nsk += 1
    R["X-16"] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}

    # ---------------- X-17
    unit("X-17")
    a01, a03 = U("A13-01")["by_item"], U("A13-03")["by_item"]
    sq = x.summary_quantities
    qc = {"REBAR": sq.reinforcement_kg, "STRUCTURAL_STEEL": sq.steel_kg, "CONCRETE": sq.concrete_m3, "TIMBER": sq.timber_m3,
          "ENVELOPE": sq.envelope_m2, "INTERIOR": sq.interior_m2}
    S = {c: [] for c in qc}
    for i, r in enumerate(M):
        if r.material_class in ("REBAR", "STRUCTURAL_STEEL", "CONCRETE", "TIMBER"):
            c = r.material_class
        elif r.quantity_unit == "m2" and r.construction_division in ("ROOF_EXTERIOR_WALL", "OPENINGS"):
            c = "ENVELOPE"
        elif r.quantity_unit == "m2" and r.construction_division == "INTERIOR":
            c = "INTERIOR"
        else:
            continue
        S[c].append(a01[i] + a03[i])
    bc = {}
    for c, qq in qc.items():
        fb = (math.fsum(S[c]) / qq) if qq != 0 else 0.0
        bc[c] = {"quantity": qq, "fbar": fb, "emission": qq * fb}
    R["X-17"] = {"value": math.fsum(v["emission"] for v in bc.values()), "by_class": bc}

    # ---------------- A4-01 / X-12 / A4-02
    for uid in ("A4-01", "X-12"):
        unit(uid)
        bi, nsk = [], 0
        for r in M:
            t = r.transport
            if t.delivery_factor_id is not None:
                bi.append(0.0); continue
            F = FF(x, "A4", t.factor_id, "tkm")
            ok = ge0(t.mass_t) and ge0(t.distance_km) and F is not None and (uid == "A4-01" or gt0(t.load_factor))
            if ok:
                bi.append(t.mass_t * t.distance_km * (1.0 if uid == "A4-01" else 1.0 / t.load_factor) * F)
            else:
                bi.append(0.0); nsk += 1
        R[uid] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}
    unit("A4-02")
    q = U("A13-05")["q_ord"]
    bi, nsk = [], 0
    for i, r in enumerate(M):
        t = r.transport
        if t.delivery_factor_id is None:
            bi.append(0.0); continue
        F = FF(x, "A4", t.delivery_factor_id, r.quantity_unit, r.conversions)
        if q[i] is not None and F is not None:
            bi.append(q[i] * F)
        else:
            bi.append(0.0); nsk += 1
    R["A4-02"] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}

    # ---------------- A5
    unit("A5-01")
    g = x.operation.grid
    gu = gunit(g)
    c = cv(x, "kWh", gu) if gu is not None else None
    ok = ge0(x.construction.electricity_kwh) and gu is not None and c is not None and g.licence_status == PP
    R["A5-01"] = {"value": (x.construction.electricity_kwh * c * g.construction_value) if ok else 0.0, "computed": ok}
    unit("A5-02")
    v, nsk = [], 0
    for fu in x.construction.fuels:
        F = FF(x, "A5", fu.factor_id, fu.unit, fu.conversions)
        if ge0(fu.quantity) and F is not None:
            v.append(fu.quantity * F)
        else:
            nsk += 1
    R["A5-02"] = {"value": math.fsum(v), "n_skipped": nsk}
    unit("A5-03")
    v, nsk = [], 0
    for ws in x.construction.waste_streams:
        F = FF(x, "A5", ws.factor_id, "kg")
        if ge0(ws.mass_kg) and F is not None:
            v.append(ws.mass_kg * F)
        else:
            nsk += 1
    R["A5-03"] = {"value": math.fsum(v), "n_skipped": nsk}
    unit("A5-04")
    p, f_, wa = U("A5-01")["value"], U("A5-02")["value"], U("A5-03")["value"]
    R["A5-04"] = {"value": p + f_ + wa, "parts": {"power": p, "fuels": f_, "waste": wa}, "other_assessed": False}

    # ---------------- C1..C4, X-14
    unit("C1-01")
    v, nsk = [], 0
    for a in x.end_of_life.demolition_activities:
        F = FF(x, "C1", a.factor_id, a.unit)
        if ge0(a.quantity) and F is not None:
            v.append(a.quantity * F)
        else:
            nsk += 1
    R["C1-01"] = {"value": math.fsum(v), "n_skipped": nsk}
    unit("C2-01")
    bi, nsk = [], 0
    for r in M:
        e = r.end_of_life
        F = FF(x, "C2", e.haul_factor_id, "tkm")
        if ge0(e.mass_kg) and ge0(e.haul_distance_km) and F is not None:
            bi.append(e.mass_kg / 1000.0 * e.haul_distance_km * F)
        else:
            bi.append(0.0); nsk += 1
    hv = []
    for h in x.end_of_life.waste_hauls:
        F = FF(x, "C2", h.factor_id, "tkm")
        if ge0(h.mass_t) and ge0(h.distance_km) and F is not None:
            hv.append(h.mass_t * h.distance_km * F)
        else:
            nsk += 1
    R["C2-01"] = {"value": math.fsum(bi + hv), "by_item": bi, "n_skipped": nsk}
    for uid, st, land in (("C3-01", "C3", False), ("C4-01", "C4", True)):
        unit(uid)
        bi, nsk, nrs = [], 0, 0
        for r in M:
            e = r.end_of_life
            if not ge0(e.mass_kg):
                bi.append(0.0); nsk += 1; continue
            s = []
            for rt in e.routes:
                if (rt.route == "LANDFILL") != land:
                    continue
                F = FF(x, st, rt.factor_id, "kg")
                if ge0(rt.fraction) and F is not None:
                    s.append(e.mass_kg * rt.fraction * F)
                else:
                    nrs += 1
            bi.append(math.fsum(s))
        R[uid] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk, "n_routes_skipped": nrs}
    unit("X-14")
    bi, nsk = [], 0
    for q_ in EQ:
        F = FF(x, "C3", q_.eol_factor_id, "kg")
        if ge0(q_.end_of_life_mass_kg) and F is not None:
            bi.append(q_.end_of_life_mass_kg * F)
        else:
            bi.append(0.0); nsk += 1
    R["X-14"] = {"value": math.fsum(bi), "by_item": bi, "n_skipped": nsk}

    # ---------------- C-05
    unit("C-05")
    qin = U("A13-05")["q_inst"]
    viol, under, nun = [], [], 0
    for i, r in enumerate(M):
        fr = [rt.fraction for rt in r.end_of_life.routes]
        neg = any(not num(f) or f < 0 for f in fr)
        s = sum(f for f in fr if num(f)) if not neg else None
        v1 = neg or s > 1 + 1e-6
        if (not v1) and s < 1 - 1e-6:
            under.append("materials[%d].end_of_life.routes" % i)
        c = cv(x, r.quantity_unit, "kg", r.conversions)
        m = r.end_of_life.mass_kg
        chk = c is not None and qin[i] is not None and m is not None
        if not chk:
            nun += 1
        v2 = chk and m > qin[i] * c * (1 + 1e-6)
        if v1:
            viol.append("materials[%d].end_of_life.routes" % i)
        if v2:
            viol.append("materials[%d].end_of_life.mass_kg" % i)
    R["C-05"] = {"ok": not viol, "violations": viol, "under_allocated": under, "n_mass_unchecked": nun}

    # ---------------- X-09
    unit("X-09")
    mass, em = {}, {}
    for r in M:
        e = r.end_of_life
        if not ge0(e.mass_kg):
            continue
        c = r.material_class
        if c not in mass:
            mass[c] = {k: 0.0 for k in ("REUSE", "RECYCLE", "PROCESSING", "LANDFILL")}
            em[c] = {k: 0.0 for k in ("REUSE", "RECYCLE", "PROCESSING", "LANDFILL")}
        for rt in e.routes:
            if not ge0(rt.fraction):
                continue
            mm = e.mass_kg * rt.fraction
            mass[c][rt.route] += mm
            F = FF(x, "C4" if rt.route == "LANDFILL" else "C3", rt.factor_id, "kg")
            if F is not None:
                em[c][rt.route] += mm * F
    R["X-09"] = {"value": math.fsum(v for d in em.values() for v in d.values()), "mass": mass, "emission": em}

    # ---------------- STO
    unit("STO-01")
    ok = ge0(sq.timber_m3) and ge0(sq.timber_dry_density_kg_per_m3) and ge0(sq.timber_carbon_fraction)
    R["STO-01"] = {"value": sq.timber_m3 * sq.timber_dry_density_kg_per_m3 * sq.timber_carbon_fraction * (44.0 / 12.0) if ok else None}
    unit("STO-02")
    F = FF(x, "MEMO", sq.concrete_uptake_factor_id, "m3")
    R["STO-02"] = {"value": sq.concrete_m3 * F if (ge0(sq.concrete_m3) and F is not None) else None}

    # ---------------- SYS-04 / QA-04
    unit("SYS-04")
    Aa = x.project.gross_floor_area
    SA = 0.0
    for k in sorted(x.project.use_area_breakdown):
        SA += x.project.use_area_breakdown[k]
    if gt0(Aa):
        r_ = Aa - SA
        R["SYS-04"] = {"ok": r_ <= 1e-9 * Aa and -r_ <= 1e-9 * Aa, "status": "EVALUATED", "sum": SA, "residual": r_}
    else:
        R["SYS-04"] = {"ok": False, "status": "INVALID", "sum": SA, "residual": None}
    unit("QA-04")
    s4 = U("SYS-04")
    if s4["status"] == "EVALUATED":
        R["QA-04"] = {"ok": s4["residual"] <= 1e-6 * Aa and -s4["residual"] <= 1e-6 * Aa, "status": "EVALUATED"}
    else:
        R["QA-04"] = {"ok": False, "status": "NOT_EVALUATED"}

    # ---------------- refrigerants B1-01..04
    unit("B1-01")
    v, nsk = [], 0
    for d in D:
        if ge0(d.charge_mass_kg) and ge0(d.gwp):
            v.append(d.charge_mass_kg * d.gwp)
        else:
            nsk += 1
    R["B1-01"] = {"value": math.fsum(v), "n_skipped": nsk}

    def dev_events(d, TT):
        if d.change_years is not None:
            return sorted(Elst(TT, d.change_years))
        return Eper(TT, d.service_life)

    unit("B1-02")
    st = []          # per device: (ok, q, u list for k=0..Y-1, chi)
    bi, by, nsk = [], [0.0] * (Y + 1), 0
    for d in D:
        ok = ge0(d.charge_mass_kg) and ge0(d.gwp) and in01(d.annual_leak_rate)
        if not ok:
            st.append(None); bi.append(0.0); nsk += 1; continue
        m0, r = d.charge_mass_kg, d.annual_leak_rate
        qd = 1.0 - (0.0 if d.top_up else r)
        ev = dev_events(d, T)
        chi = [0] * (Y + 1)
        for tau in ev:
            chi[kcell(tau)] = 1
        u = [m0]
        for k in range(Y - 1):
            u.append(m0 if chi[k] else qd * u[k])
        vals = [d.gwp * r * u[k] * w(T, k) for k in range(Y)]
        for k in range(Y):
            by[k + 1] += vals[k]
        bi.append(math.fsum(vals))
        st.append((m0, r, qd, u, chi, ev))
    R["B1-02"] = {"value": math.fsum(bi), "by_item": bi, "by_year": by, "n_skipped": nsk}
    R["_b1state"] = st
    unit("B1-03")
    B = U("B1-02")
    tot, by, nsk = [], [0.0] * (Y + 1), 0
    for di, d in enumerate(D):
        s_ = st[di]
        if s_ is None or not in01(d.replacement_loss_rate):
            nsk += 1; continue
        m0, r, qd, u, chi, ev = s_
        lam = d.replacement_loss_rate
        seen = set()
        for tau in ev:
            k = kcell(tau)
            if k not in seen:
                seen.add(k)
                amt = lam * d.gwp * u[k] * (1.0 - (0.0 if d.top_up else r * w(T, k)))
            else:
                amt = lam * d.gwp * m0
            tot.append(amt)
            by[k + 1] += amt
    R["B1-03"] = {"value": math.fsum(tot), "by_year": by, "n_skipped": nsk}
    unit("B1-04")
    U("B1-02")
    K = Y - 1
    tot, nsk = [], 0
    for di, d in enumerate(D):
        s_ = st[di]
        if s_ is None or not in01(d.end_of_life_recovery_rate):
            nsk += 1; continue
        m0, r, qd, u, chi, ev = s_
        kap = (1.0 - d.end_of_life_recovery_rate) * d.gwp
        if any(kcell(t) == K for t in ev):
            ue = m0
        else:
            ue = u[K] * (1.0 - (0.0 if d.top_up else r * (T - K)))
        tot.append(kap * ue)
    R["B1-04"] = {"value": math.fsum(tot), "n_skipped": nsk}

    # ---------------- events B4-01, B4-03
    unit("B4-01")
    ev_eq = []
    for q_ in EQ:
        if q_.replacement_event_list is not None:
            ev_eq.append(Elst(T, q_.replacement_event_list))
        else:
            ev_eq.append(Eper(T, q_.service_life))
    R["B4-01"] = {"events": ev_eq, "n_events": sum(len(e) for e in ev_eq)}
    unit("B4-03")
    nmat = [len(Eper(T, r.refresh_cycle)) for r in M]
    R["B4-03"] = {"by_item": nmat}

    # ---------------- B3-01 / B3-02
    unit("B3-01")
    a01, a03, x01 = U("A13-01")["by_item"], U("A13-03")["by_item"], U("X-01")["by_item"]
    U("B4-01"); U("B4-03")
    rows, nsk = [], 0
    for i, r in enumerate(M):
        if ge0(r.repair_rate):
            rows.append(((a01[i] + a03[i]) * r.repair_rate, Eper(T, r.refresh_cycle)))
        else:
            nsk += 1
    for j, q_ in enumerate(EQ):
        if ge0(q_.repair_rate):
            rows.append((x01[j] * q_.repair_rate, ev_eq[j]))
        else:
            nsk += 1
    by = [0.0] * (Y + 1)
    for a, ev in rows:
        ys = {kcell(t) + 1 for t in ev}
        for y in range(1, Y + 1):
            if y not in ys:
                by[y] += a * w(T, y - 1)
    R["B3-01"] = {"value": math.fsum(by), "by_year": by, "n_skipped": nsk}
    unit("B3-02")
    s_ = [a for a, _ in rows]
    R["B3-02"] = {"value": T * math.fsum(s_), "n_skipped": nsk}

    # ---------------- B4-02
    unit("B4-02")
    A13 = {k: U(k)["by_item"] for k in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")}
    x01, x14 = U("X-01")["by_item"], U("X-14")["by_item"]
    q = U("A13-05")["q_ord"]
    U("B4-01"); U("B4-03")
    um, ue_ = [], []
    partial_m, partial_e = [], []
    skipped_rows = {}
    for i, r in enumerate(M):
        s = math.fsum([A13[k][i] for k in ("A13-01", "A13-03", "A4-01", "A4-02", "C2-01", "C3-01", "C4-01")])
        inst = 0.0
        if r.installation_factor_id is not None and q[i] is not None:
            F = FF(x, "A5", r.installation_factor_id, r.quantity_unit, r.conversions)
            if F is not None:
                inst = q[i] * F
        um.append(s + inst)
    for j, q_ in enumerate(EQ):
        s = x01[j] + x14[j]
        for f, stg in ((q_.delivery_factor_id, "A4"), (q_.installation_factor_id, "A5")):
            if f is not None and ge0(q_.quantity):
                F = FF(x, stg, f, q_.quantity_unit)
                if F is not None:
                    s += q_.quantity * F
        ue_.append(s)
    bim = [nmat[i] * um[i] for i in range(len(M))]
    bie = [len(ev_eq[j]) * ue_[j] for j in range(len(EQ))]
    by = [0.0] * (Y + 1)
    for i, r in enumerate(M):
        for t in Eper(T, r.refresh_cycle):
            by[kcell(t) + 1] += um[i]
    for j in range(len(EQ)):
        for t in ev_eq[j]:
            by[kcell(t) + 1] += ue_[j]
    R["B4-02"] = {"value": math.fsum(bim + bie), "by_item_material": bim, "by_item_equipment": bie, "by_year": by,
                  "n_partial": None}
    R["_b4u"] = (um, ue_)

    # ---------------- X-08
    unit("X-08")
    U("B4-02"); U("B4-01"); U("B4-03")
    cyc = {}
    for i, r in enumerate(M):
        if nmat[i] > 0:
            cyc.setdefault(r.refresh_cycle, []).append(um[i])
    expl = 0.0
    for j, q_ in enumerate(EQ):
        if q_.replacement_event_list is not None:
            expl += ue_[j] * len(ev_eq[j])
        elif ev_eq[j]:
            cyc.setdefault(q_.service_life, []).append(ue_[j])
    bc = {}
    for c, us in cyc.items():
        N = len(Eper(T, c))
        Uc = math.fsum(us)
        bc[repr(float(c))] = {"count": N, "unit_emission": Uc, "emission": N * Uc}
    R["X-08"] = {"value": expl + math.fsum(v["emission"] for v in bc.values()), "by_cycle": bc, "explicit": expl}

    # ---------------- B5-01
    unit("B5-01")
    base = math.fsum(U(k)["value"] for k in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01",
                                              "C3-01", "C4-01", "X-14"))
    b = x.boundary
    by = [0.0] * (Y + 1)
    if b.reconstruction_scenario == "NONE":
        R["B5-01"] = {"value": 0.0, "n_events": 0, "by_year": by, "computed": True}
    elif not in01(b.reconstruction_scope_fraction):
        R["B5-01"] = {"value": 0.0, "n_events": 0, "by_year": by, "computed": False}
    else:
        ev = Eper(T, b.replacement_cycle)
        amp = b.reconstruction_scope_fraction * base
        for t in ev:
            by[kcell(t) + 1] += amp
        R["B5-01"] = {"value": len(ev) * amp, "n_events": len(ev), "by_year": by, "computed": True}

    # ---------------- operation
    op = x.operation
    unit("X-06")
    gok = _grid_ok(g)
    if not gok:
        gam = [g.table[k] for k in range(Y)]
    elif g.kind == "CONSTANT":
        gam = [g.start] * Y
    elif g.kind == "LINEAR_DECLINE_TO_FLOOR":
        gam = [max(g.floor, g.start - g.annual_decline * k) for k in range(Y)]
    else:
        gam = []
        for k in range(Y):
            vv = None
            for s_ in g.steps:
                if s_.from_index <= k:
                    vv = s_.value
            gam.append(vv)
    R["X-06"] = {"by_year": [0.0] + gam, "matches_table": same(gam, g.table[:Y]), "source": "DESCRIPTOR" if gok else "TABLE"}
    unit("B6-04")
    eu = aunit(op.electricity.unit)
    cg = cv(x, aunit(op.onsite_generation.unit), eu) if eu is not None else None
    cx = cv(x, aunit(op.onsite_export.unit), eu) if eu is not None else None
    comp = eu is not None and cg is not None and cx is not None
    ce, ge, xe = vk(op.electricity, Y), vk(op.onsite_generation, Y), vk(op.onsite_export, Y)
    nk = []
    for k in range(Y):
        if comp:
            dk = ce[k] - (ge[k] * cg - xe[k] * cx)
            nk.append(dk if dk >= 0 else 0.0)
        else:
            nk.append(0.0)
    dmt = all(same(vk(p, Y), p.table[:Y]) for p in (op.electricity, op.onsite_generation, op.onsite_export))
    R["B6-04"] = {"by_year": [0.0] + nk, "computed": comp, "descriptors_match_tables": dmt}
    unit("B6-01")
    U("B6-04"); U("X-06")
    gu = gunit(g)
    c61 = cv(x, eu, gu) if (eu is not None and gu is not None) else None
    ok61 = g.licence_status == PP and comp and c61 is not None
    ek = [(nk[k] * c61 * gam[k]) if ok61 else 0.0 for k in range(Y)]
    R["B6-01"] = {"by_year": [0.0] + ek, "computed": ok61}
    unit("B6-02")
    fk = [0.0] * Y
    nsk = 0
    parts = []
    for p, fid in ((op.gas, op.gas_factor_id), (op.oil, op.oil_factor_id), (op.district_heat, op.district_heat_factor_id)):
        F = FF(x, "B6", fid, aunit(p.unit)) if aunit(p.unit) is not None else None
        if F is None:
            nsk += 1; continue
        vv = vk(p, Y)
        for k in range(Y):
            fk[k] += vv[k] * F
    dmt = all(same(vk(p, Y), p.table[:Y]) for p in (op.gas, op.oil, op.district_heat))
    R["B6-02"] = {"by_year": [0.0] + fk, "n_skipped": nsk, "descriptors_match_tables": dmt}
    unit("B6-03")
    U("B6-01"); U("B6-02")
    R["B6-03"] = {"value": math.fsum(w(T, k) * (ek[k] + fk[k]) for k in range(Y))}
    unit("B2-01")
    U("B6-01")
    rho = op.facility_management_ratio
    EL = math.fsum(ek[k] * w(T, k) for k in range(Y))
    okb2 = in01(rho)
    R["B2-01"] = {"value": rho * EL if okb2 else 0.0, "computed": okb2}
    unit("X-11")
    U("X-06")
    I = getattr(op, "electricity_per_m2_per_year", None)
    c11 = cv(x, "kWh", gu) if gu is not None else None
    ok11 = gt0(Aa) and ge0(I) and c11 is not None and g.licence_status == PP
    Gt = math.fsum(gam[k] * w(T, k) for k in range(Y))
    R["X-11"] = {"value": Aa * I * c11 * Gt if ok11 else None}
    ww = x.water_waste
    bw = {}
    for uid, p, fid in (("B7-01", ww.water, ww.water_factor_id), ("B7-02", ww.sewage, ww.sewage_factor_id),
                        ("B7-03", ww.municipal_waste, ww.waste_factor_id)):
        unit(uid)
        F = FF(x, "B7", fid, aunit(p.unit)) if aunit(p.unit) is not None else None
        vv = vk(p, Y)
        bk = [(vv[k] * F) if F is not None else 0.0 for k in range(Y)]
        bw[uid] = bk
        R[uid] = {"by_year": [0.0] + bk, "n_skipped": 0 if F is not None else 1, "descriptors_match_tables": same(vv, p.table[:Y])}
    unit("B7-04")
    for k_ in ("B7-01", "B7-02", "B7-03"):
        U(k_)
    R["B7-04"] = {"value": math.fsum(w(T, k) * (bw["B7-01"][k] + bw["B7-02"][k] + bw["B7-03"][k]) for k in range(Y))}

    # ---------------- X-10
    unit("X-10")
    U("A13-05"); U("B4-01"); U("B4-03")
    A = R["A13-05"]
    res, wst, nex = [], [], 0
    for i, r in enumerate(M):
        c = cv(x, r.quantity_unit, "kg", r.conversions)
        m = r.end_of_life.mass_kg
        if c is not None and A["q_ord"][i] is not None and ge0(m):
            res.append(A["q_ord"][i] * c * (1 + nmat[i]))
            wst.append(((A["q_ord"][i] - A["q_inst"][i]) * c + m) * (1 + nmat[i]))
        else:
            nex += 1
    for j, q_ in enumerate(EQ):
        m = q_.end_of_life_mass_kg
        if ge0(m):
            wst.append(m * (1 + len(ev_eq[j])))
        else:
            nex += 1
    R["X-10"] = {"resource_kg": math.fsum(res), "waste_kg": math.fsum(wst), "n_excluded": nex}

    # ---------------- X-02 and totals
    unit("X-02")
    COMP = [("A1-A3", "A13-01", 1), ("A1-A3", "A13-03", 1), ("A1-A3", "A13-04", 1), ("A1-A3", "X-01", 1), ("A4", "A4-01", 1),
            ("A4", "A4-02", 1), ("A5", "A5-04", 1), ("B1", "B1-02", 1), ("B1", "B1-03", 1), ("B1", "B1-04", 1), ("B2", "B2-01", 1),
            ("B3", "B3-01", 1), ("B4", "B4-02", 1), ("B5", "B5-01", 1), ("B6", "B6-03", 1), ("B6", "B2-01", -1), ("B7", "B7-04", 1),
            ("C1", "C1-01", 1), ("C2", "C2-01", 1), ("C3", "C3-01", 1), ("C3", "X-14", 1), ("C4", "C4-01", 1)]
    full = {s: [] for s in STAGES}
    bsl = {s: [] for s in STAGES}
    for s, u_, sg in COMP:
        V = U(u_)["value"]
        full[s].append(sg * V)
        beta = iota["B2"] if (s, u_) == ("B6", "B2-01") else 1
        bsl[s].append(sg * beta * V)
    full = {s: math.fsum(v) for s, v in full.items()}
    bs = {s: math.fsum(bsl[s]) for s in STAGES if iota[s]}
    R["X-02"] = {"by_stage": bs, "by_stage_all": full, "complete": None, "incomplete_units": None}
    C = math.fsum(bs.values())
    unit("SUM-01"); U("X-02")
    R["SUM-01"] = {"value": math.fsum(bs.get(s, 0.0) for s in ("A1-A3", "A4", "A5")), "complete": None}
    unit("SUM-02"); U("X-02")
    R["SUM-02"] = {"value": math.fsum(v for s, v in bs.items() if s not in ("B6", "B7")), "complete": None}
    unit("SUM-03"); U("X-02")
    R["SUM-03"] = {"value": C, "complete": None}
    unit("SUM-04"); U("SUM-03")
    R["SUM-04"] = {"value": C * (1.0 / Aa) if gt0(Aa) else None}
    unit("SUM-05"); U("SUM-03")
    R["SUM-05"] = {"value": C / (Aa * T) if gt0(Aa) else None}
    unit("SUM-06"); U("SUM-03")
    R["SUM-06"] = {"value": C / 1000.0}
    unit("SUM-07"); U("SUM-03"); U("X-02")
    dfn = C > 0 and not any(v < 0 for v in bs.values())
    R["SUM-07"] = {"defined": dfn, "by_stage": {s: v / C for s, v in bs.items()} if dfn else {}}

    # ---------------- X-07 (year allocation)
    unit("X-07")
    for k_ in ("B1-02", "B1-03", "B1-04", "B2-01", "B3-01", "B4-02", "B5-01", "B6-01", "B6-02", "B7-01", "B7-02", "B7-03", "X-02"):
        U(k_)
    s0 = math.fsum(iota[s] * full[s] for s in ("A1-A3", "A4", "A5"))
    sy = [0.0] * (Y + 1)
    rho_eff = rho if okb2 else 0.0
    for y in range(1, Y + 1):
        k = y - 1
        parts_ = []
        if iota["B1"]:
            parts_ += [R["B1-02"]["by_year"][y], R["B1-03"]["by_year"][y]]
        if iota["B3"]:
            parts_.append(R["B3-01"]["by_year"][y])
        if iota["B4"]:
            parts_.append(R["B4-02"]["by_year"][y])
        if iota["B5"]:
            parts_.append(R["B5-01"]["by_year"][y])
        wk = w(T, k)
        if iota["B2"]:
            parts_.append(rho_eff * ek[k] * wk)
        if iota["B6"]:
            parts_.append((ek[k] + fk[k]) * wk - (iota["B2"] * rho_eff * ek[k] * wk))
        if iota["B7"]:
            parts_.append((bw["B7-01"][k] + bw["B7-02"][k] + bw["B7-03"][k]) * wk)
        if y == Y:
            parts_.append(math.fsum(iota[s] * full[s] for s in ("C1", "C2", "C3", "C4")))
            if iota["B1"]:
                parts_.append(R["B1-04"]["value"])
        sy[y] = math.fsum(parts_)
    sy[0] = s0
    cum, acc = [], 0.0
    for v in sy:
        acc += v
        cum.append(acc)
    R["X-07"] = {"by_year": sy, "cumulative": cum, "value": cum[-1]}

    # ---------------- QA-02
    unit("QA-02")
    viol, warn = [], []
    for name, rows_, attr in (("equipment", EQ, "replacement_event_list"), ("refrigerants", D, "change_years")):
        for i, r in enumerate(rows_):
            L_ = getattr(r, attr)
            if L_ is None:
                continue
            if any((not (t >= 0)) or (not th(T, t)) for t in L_):
                viol.append("%s[%d].%s" % (name, i, attr))
            if any(t == 0 for t in L_):
                warn.append("%s[%d].%s" % (name, i, attr))
    R["QA-02"] = {"ok": not viol, "violations": viol, "warnings": warn}
    R["_b3rows"] = rows
    if not keep:
        for k_ in ("_b1state", "_b4u", "_b3rows"):
            R.pop(k_, None)
    return R, reads


def _grid_ok(g):
    if g.kind == "CONSTANT":
        return g.start is not None
    if g.kind == "LINEAR_DECLINE_TO_FLOOR":
        return None not in (g.start, g.floor, g.annual_decline) and g.annual_decline >= 0.0 and g.start >= g.floor
    if g.kind == "STEPWISE":
        s = g.steps or []
        return bool(s) and s[0].from_index == 0 and all(s[i].from_index < s[i + 1].from_index for i in range(len(s) - 1))
    return False


# =====================================================================================================
# the remaining outputs: n_partial / complete (X-02, SUM-01..03), SUM-08, X-04, X-05, QA-01, QA-03, SYS-01..03
# =====================================================================================================
SYS1 = ([("p", "gross_floor_area")] + [("m", f) for f in ("quantity", "waste_rate", "reuse_rate", "material_life", "repair_rate",
        "refresh_cycle", "transport.mass_t", "transport.distance_km", "end_of_life.mass_kg")]
        + [("e", f) for f in ("quantity", "service_life", "repair_rate", "end_of_life_mass_kg")]
        + [("r", f) for f in ("charge_mass_kg", "gwp", "annual_leak_rate", "replacement_loss_rate", "end_of_life_recovery_rate")]
        + [("rn", "service_life"), ("ce", "electricity_kwh"), ("cf", "quantity"), ("cw", "mass_kg"), ("dd", "quantity"), ("dh", "mass_t"),
           ("dh", "distance_km")])


def _get(o, path):
    for p in path.split("."):
        o = getattr(o, p)
    return o


def run_all(x, T, baselines=None, _base=False, keep=False):
    R, reads = run(x, T, keep=True)
    M, EQ, D = x.materials, x.equipment, x.refrigerants
    Y = math.ceil(T)
    inc = set(x.boundary.included_lifecycle_stages)
    iota = {s: (1 if s in inc else 0) for s in STAGES}
    X15, A05 = R["X-15"], R["A13-05"]
    q = A05["q_ord"]
    nmat = R["B4-03"]["by_item"]
    ev_eq = R["B4-01"]["events"]
    g = x.operation.grid
    um, ue_ = R["_b4u"]

    def rd(u, *deps):
        reads.setdefault(u, set()).update(deps)

    # ---- per-row masks (same predicates as the ledger formulas)
    kind = X15["kind"]
    a01ok = [kind[i] in ("GENERIC", "COMPOSITE") and q[i] is not None for i in range(len(M))]
    a03ok = [kind[i] == "EPD" and q[i] is not None for i in range(len(M))]
    a01sk = [kind[i] is None or (kind[i] in ("GENERIC", "COMPOSITE") and q[i] is None) for i in range(len(M))]
    a03sk = [kind[i] == "EPD" and q[i] is None for i in range(len(M))]

    def a41ok(r):
        t = r.transport
        return t.delivery_factor_id is None and ge0(t.mass_t) and ge0(t.distance_km) and G(x, "A4", t.factor_id, "tkm")

    def a42ok(i, r):
        t = r.transport
        return t.delivery_factor_id is not None and q[i] is not None and G(x, "A4", t.delivery_factor_id, r.quantity_unit, r.conversions)

    def c21ok(r):
        e = r.end_of_life
        return ge0(e.mass_kg) and ge0(e.haul_distance_km) and G(x, "C2", e.haul_factor_id, "tkm")

    def rtok(r, rt):
        st = "C4" if rt.route == "LANDFILL" else "C3"
        return ge0(r.end_of_life.mass_kg) and ge0(rt.fraction) and G(x, st, rt.factor_id, "kg")

    def instok(i, r):
        return r.installation_factor_id is not None and q[i] is not None and G(x, "A5", r.installation_factor_id, r.quantity_unit, r.conversions)

    def eqok(qq, f, st):
        return f is not None and ge0(qq.quantity) and G(x, st, f, qq.quantity_unit)

    # ---- B4-02 n_partial
    npm = []
    for i, r in enumerate(M):
        t = r.transport
        sk41 = t.delivery_factor_id is None and not a41ok(r)
        sk42 = t.delivery_factor_id is not None and not a42ok(i, r)
        rsk = ge0(r.end_of_life.mass_kg) and any(not rtok(r, rt) for rt in r.end_of_life.routes)
        part = (a01sk[i] or a03sk[i] or sk41 or sk42 or not c21ok(r) or not ge0(r.end_of_life.mass_kg) or rsk
                or (r.installation_factor_id is not None and not instok(i, r)))
        npm.append(part)
    npe = []
    for j, qq in enumerate(EQ):
        x01ok = ge0(qq.quantity) and G(x, "A1-A3", qq.factor_id, qq.quantity_unit)
        x14ok = ge0(qq.end_of_life_mass_kg) and G(x, "C3", qq.eol_factor_id, "kg")
        part = (not x01ok or not x14ok or (qq.delivery_factor_id is not None and not eqok(qq, qq.delivery_factor_id, "A4"))
                or (qq.installation_factor_id is not None and not eqok(qq, qq.installation_factor_id, "A5")))
        npe.append(part)
    R["B4-02"]["n_partial"] = sum(1 for i in range(len(M)) if npm[i] and nmat[i] >= 1) + \
        sum(1 for j in range(len(EQ)) if npe[j] and len(ev_eq[j]) >= 1)

    # ---- X-02 complete / incomplete_units ; SUM-01..03 complete
    CHK = {"A1-A3": ("A13-01", "A13-03", "A13-04", "X-01"), "A4": ("A4-01", "A4-02"), "A5": ("A5-01", "A5-02", "A5-03"),
           "B1": ("B1-02", "B1-03", "B1-04"), "B2": ("B2-01", "B6-01"), "B3": ("B3-01",), "B4": ("B4-02",), "B5": ("B5-01",),
           "B6": ("B6-01", "B6-02"), "B7": ("B7-01", "B7-02", "B7-03"), "C1": ("C1-01",), "C2": ("C2-01",), "C3": ("C3-01", "X-14"),
           "C4": ("C4-01",)}

    def bad(u):
        o = R[u]
        return bool(o.get("n_skipped", 0) or o.get("n_routes_skipped", 0) or o.get("n_partial", 0) or o.get("computed", True) is False)
    incu = sorted({u for s, us in CHK.items() if iota[s] for u in us if bad(u)})
    rd("X-02", *{u for us in CHK.values() for u in us})
    R["X-02"]["complete"] = not incu
    R["X-02"]["incomplete_units"] = incu
    for k in ("SUM-01", "SUM-02", "SUM-03"):
        R[k]["complete"] = not incu

    # ---- lines L_s: list of (factor, activity) per stage (no stage predicate)
    def Fv(f):
        return x.factors[f].value

    def cvf(u, f, extra=()):
        return cv(x, u, x.factors[f].unit, extra)
    st_lines = {s: [] for s in STAGES}
    rep = {}                                         # row -> list of (f, act) lines repeated by a repair (b3)
    ren_m, ren_e = {}, {}                            # row -> lines repeated by a renewal (b4)
    for i, r in enumerate(M):
        base_l = []
        if a01ok[i] and kind[i] == "GENERIC":
            base_l.append((r.factor_id, q[i] * X15["conv"][i]))
        if a03ok[i]:
            base_l.append((r.epd.factor_id, q[i] * X15["conv"][i]))
        if a01ok[i] and kind[i] == "COMPOSITE":
            for c in r.composition:
                base_l.append((c.factor_id, q[i] * X15["conv"][i] * c.mass_fraction * cvf("kg", c.factor_id)))
        st_lines["A1-A3"] += base_l
        ru = r.unquantified_cost_ratio
        if num(ru) and 0.0 < ru < 1.0:
            st_lines["A1-A3"] += [(f, a * (ru / (1.0 - ru))) for f, a in base_l]
        rep[("m", i)] = list(base_l)
        ren = list(base_l)
        t = r.transport
        if a41ok(r):
            l = (t.factor_id, t.mass_t * t.distance_km * cvf("tkm", t.factor_id)); st_lines["A4"].append(l); ren.append(l)
        if a42ok(i, r):
            l = (t.delivery_factor_id, q[i] * cvf(r.quantity_unit, t.delivery_factor_id, r.conversions)); st_lines["A4"].append(l); ren.append(l)
        e = r.end_of_life
        if c21ok(r):
            l = (e.haul_factor_id, e.mass_kg * 0.001 * e.haul_distance_km * cvf("tkm", e.haul_factor_id)); st_lines["C2"].append(l); ren.append(l)
        for rt in e.routes:
            if rtok(r, rt):
                l = (rt.factor_id, e.mass_kg * rt.fraction * cvf("kg", rt.factor_id))
                st_lines["C4" if rt.route == "LANDFILL" else "C3"].append(l); ren.append(l)
        if instok(i, r):
            ren.append((r.installation_factor_id, q[i] * cvf(r.quantity_unit, r.installation_factor_id, r.conversions)))
        ren_m[i] = ren
    for j, qq in enumerate(EQ):
        ren = []
        if ge0(qq.quantity) and G(x, "A1-A3", qq.factor_id, qq.quantity_unit):
            l = (qq.factor_id, qq.quantity * cvf(qq.quantity_unit, qq.factor_id)); st_lines["A1-A3"].append(l); ren.append(l)
            rep[("e", j)] = [l]
        else:
            rep[("e", j)] = []
        if ge0(qq.end_of_life_mass_kg) and G(x, "C3", qq.eol_factor_id, "kg"):
            l = (qq.eol_factor_id, qq.end_of_life_mass_kg * cvf("kg", qq.eol_factor_id)); st_lines["C3"].append(l); ren.append(l)
        for f, stg in ((qq.delivery_factor_id, "A4"), (qq.installation_factor_id, "A5")):
            if eqok(qq, f, stg):
                ren.append((f, qq.quantity * cvf(qq.quantity_unit, f)))
        ren_e[j] = ren
    for fu in x.construction.fuels:
        if ge0(fu.quantity) and G(x, "A5", fu.factor_id, fu.unit, fu.conversions):
            st_lines["A5"].append((fu.factor_id, fu.quantity * cvf(fu.unit, fu.factor_id, fu.conversions)))
    for ws in x.construction.waste_streams:
        if ge0(ws.mass_kg) and G(x, "A5", ws.factor_id, "kg"):
            st_lines["A5"].append((ws.factor_id, ws.mass_kg * cvf("kg", ws.factor_id)))
    for a in x.end_of_life.demolition_activities:
        if ge0(a.quantity) and G(x, "C1", a.factor_id, a.unit):
            st_lines["C1"].append((a.factor_id, a.quantity * cvf(a.unit, a.factor_id)))
    for h in x.end_of_life.waste_hauls:
        if ge0(h.mass_t) and ge0(h.distance_km) and G(x, "C2", h.factor_id, "tkm"):
            st_lines["C2"].append((h.factor_id, h.mass_t * h.distance_km * cvf("tkm", h.factor_id)))
    static_lines = [l for s in ("A1-A3", "A4", "A5", "C1", "C2", "C3", "C4") for l in st_lines[s]]
    # B3: repair lines x rate x repair years; B4: renewal lines x count; B5: static lines x N*phi
    a01b, a03b, x01b = R["A13-01"]["by_item"], R["A13-03"]["by_item"], R["X-01"]["by_item"]
    for i, r in enumerate(M):
        if ge0(r.repair_rate) and r.repair_rate != 0 and (a01b[i] + a03b[i]) != 0:
            evy = {kcell(t) for t in Eper(T, r.refresh_cycle)}
            yrs = T - math.fsum(w(T, k) for k in evy)
            st_lines["B3"] += [(f, a * r.repair_rate * yrs) for f, a in rep[("m", i)]]
        if nmat[i]:
            st_lines["B4"] += [(f, a * nmat[i]) for f, a in ren_m[i]]
    for j, qq in enumerate(EQ):
        if ge0(qq.repair_rate) and qq.repair_rate != 0 and x01b[j] != 0:
            evy = {kcell(t) for t in ev_eq[j]}
            yrs = T - math.fsum(w(T, k) for k in evy)
            st_lines["B3"] += [(f, a * qq.repair_rate * yrs) for f, a in rep[("e", j)]]
        if ev_eq[j]:
            st_lines["B4"] += [(f, a * len(ev_eq[j])) for f, a in ren_e[j]]
    b = x.boundary
    live = b.reconstruction_scenario != "NONE" and in01(b.reconstruction_scope_fraction)
    b5k = (len(Eper(T, b.replacement_cycle)) * b.reconstruction_scope_fraction) if live else 0.0
    st_lines["B5"] = [(f, b5k * a) for f, a in static_lines]
    op, wwt = x.operation, x.water_waste
    for p, fid, st in ((op.gas, op.gas_factor_id, "B6"), (op.oil, op.oil_factor_id, "B6"), (op.district_heat, op.district_heat_factor_id, "B6"),
                       (wwt.water, wwt.water_factor_id, "B7"), (wwt.sewage, wwt.sewage_factor_id, "B7"),
                       (wwt.municipal_waste, wwt.waste_factor_id, "B7")):
        au = aunit(p.unit)
        if au is not None and G(x, st, fid, au):
            vv = vk(p, Y)
            c = cvf(au, fid)
            st_lines[st].append((fid, math.fsum(w(T, k) * vv[k] * c for k in range(Y))))
    a51 = R["A5-01"]["value"]
    EL = math.fsum(R["B6-01"]["by_year"][k + 1] * w(T, k) for k in range(Y))
    v21 = R["B2-01"]["value"]
    pseudo = {s: 0.0 for s in STAGES}
    pseudo["A5"] = a51
    pseudo["B1"] = R["B1-02"]["value"] + R["B1-03"]["value"] + R["B1-04"]["value"]
    pseudo["B2"] = v21
    pseudo["B6"] = EL - v21
    pseudo["B5"] = b5k * a51

    def agg(lines):
        d = {}
        for f, a in lines:
            d[f] = d.get(f, 0.0) + a
        return d
    Ls = {s: agg(st_lines[s]) for s in STAGES}
    recomp = {s: math.fsum([a * Fv(f) for f, a in Ls[s].items()] + [pseudo[s]]) for s in STAGES}
    Aall = agg([(f, a) for s in STAGES for f, a in Ls[s].items()])
    bg = {gname: 0.0 for gname in x.gases}
    for f, a in Aall.items():
        for gname, amt in x.factors[f].gas_amounts.items():
            if gname in bg:
                bg[gname] += a * amt
    fg = math.fsum(x.gwp[gname] * v for gname, v in bg.items() if gname in x.gwp)
    grid = a51 + EL + b5k * a51
    refr = pseudo["B1"]
    R["X-04"] = {"value": fg + grid + refr, "by_gas": bg, "co2e_from_gases": fg, "grid_co2e": grid, "refrigerant_co2e": refr,
                 "by_stage_recomputed": recomp}
    rd("X-04", "A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-01", "A5-02", "A5-03", "B1-02", "B1-03", "B1-04", "B2-01",
       "B3-01", "B4-02", "B5-01", "B6-03", "B7-04", "C1-01", "C2-01", "C3-01", "C4-01", "X-14")
    co2p = dict(pseudo)
    co2p["B1"] = 0.0
    co2 = {s: math.fsum([a * x.factors[f].gas_amounts.get("CO2", 0.0) for f, a in Ls[s].items()] + [co2p[s]]) for s in STAGES}
    v05 = math.fsum(co2[s] for s in STAGES if iota[s]) + (co2["B2"] if (iota["B6"] and not iota["B2"]) else 0.0)
    R["X-05"] = {"value": v05, "by_stage_co2": co2}
    rd("X-05", "X-04")
    # ---- QA-01
    full = R["X-02"]["by_stage_all"]
    viol = ["stage %s" % s for s in STAGES if abs(full[s] - recomp[s]) > 1e-9 * max(abs(full[s]), 1.0)]
    for i in range(len(M)):
        if a01b[i] != 0 and a03b[i] != 0:
            viol.append("materials[%d] A13-01/A13-03" % i)
        if R["A4-01"]["by_item"][i] != 0 and R["A4-02"]["by_item"][i] != 0:
            viol.append("materials[%d] A4-01/A4-02" % i)
    R["QA-01"] = {"ok": not viol, "violations": viol}
    rd("QA-01", "X-02", "X-04", "A13-01", "A13-03", "A4-01", "A4-02")
    # ---- QA-03: factors that appear in a line (mask true, whatever the activity) at T
    used = set()
    for i, r in enumerate(M):
        if a01ok[i] and kind[i] == "GENERIC":
            used.add(r.factor_id)
        if a03ok[i]:
            used.add(r.epd.factor_id)
        if a01ok[i] and kind[i] == "COMPOSITE":
            used |= {c.factor_id for c in r.composition}
        if a41ok(r):
            used.add(r.transport.factor_id)
        if a42ok(i, r):
            used.add(r.transport.delivery_factor_id)
        if c21ok(r):
            used.add(r.end_of_life.haul_factor_id)
        used |= {rt.factor_id for rt in r.end_of_life.routes if rtok(r, rt)}
        if instok(i, r) and nmat[i] >= 1:
            used.add(r.installation_factor_id)
    for j, qq in enumerate(EQ):
        if ge0(qq.quantity) and G(x, "A1-A3", qq.factor_id, qq.quantity_unit):
            used.add(qq.factor_id)
        if ge0(qq.end_of_life_mass_kg) and G(x, "C3", qq.eol_factor_id, "kg"):
            used.add(qq.eol_factor_id)
        for f, stg in ((qq.delivery_factor_id, "A4"), (qq.installation_factor_id, "A5")):
            if eqok(qq, f, stg) and ev_eq[j]:
                used.add(f)
    for f, a in Ls["A5"].items():
        used.add(f)
    for st in ("C1", "C2"):
        used |= set(Ls[st])
    for p, fid, st in ((op.gas, op.gas_factor_id, "B6"), (op.oil, op.oil_factor_id, "B6"), (op.district_heat, op.district_heat_factor_id, "B6"),
                       (wwt.water, wwt.water_factor_id, "B7"), (wwt.sewage, wwt.sewage_factor_id, "B7"),
                       (wwt.municipal_waste, wwt.waste_factor_id, "B7")):
        au = aunit(p.unit)
        if au is not None and G(x, st, fid, au):
            used.add(fid)
    okq = lambda f: x.factors[f].licence_status == PP and bool(x.factors[f].source_url)
    R["QA-03"] = {"ok": all(okq(f) for f in used), "violations": sorted(f for f in used if not okq(f)), "n_used": len(used)}
    rd("QA-03", "X-04")
    # ---- SUM-08
    bsid = x.boundary.baseline_scenario
    bscn = (baselines or {}).get(bsid) if bsid is not None else None
    C = R["SUM-03"]["value"]
    if bscn is None:
        R["SUM-08"] = {"status": "NO_BASELINE", "delta": None, "saving": None}
    else:
        A1, A2 = x.project.gross_floor_area, bscn.project.gross_floor_area
        reasons = []
        if not (A1 == A2 or (A1 is None and A2 is None)):
            reasons.append("AREA")
        if not (T == bscn.boundary.study_period):
            reasons.append("PERIOD")
        if set(x.boundary.included_lifecycle_stages) != set(bscn.boundary.included_lifecycle_stages):
            reasons.append("STAGES")
        if x.boundary.results_gas_scope != bscn.boundary.results_gas_scope:
            reasons.append("GAS_SCOPE")
        if {f.release_year for f in x.factors.values()} != {f.release_year for f in bscn.factors.values()}:
            reasons.append("FACTOR_VERSION")
        if reasons:
            R["SUM-08"] = {"status": "NOT_COMPARABLE", "delta": None, "saving": None, "reasons": reasons}
        else:
            Cb = run_all(bscn, bscn.boundary.study_period, None, _base=True)[0]["SUM-03"]["value"]
            R["SUM-08"] = {"status": "COMPARED", "baseline": Cb, "delta": C - Cb, "saving": ((Cb - C) * (1.0 / Cb)) if Cb > 0 else None}
    rd("SUM-08", "SUM-03")
    if not _base:
        sys_units(x, R, reads, a01ok, a03ok, kind)
    if not keep:
        for k_ in ("_b1state", "_b4u", "_b3rows"):
            R.pop(k_, None)
    return R, reads


def sys_units(x, R, reads, a01ok, a03ok, kind):
    M, EQ, D = x.materials, x.equipment, x.refrigerants
    # ---- SYS-01
    STATES_ = ("OBSERVED", "ESTIMATE", "EXPLICIT_ZERO", "MISSING", "DERIVED")
    cnt = {s: 0 for s in STATES_}
    found = []

    def state(owner, key, v, app=True, ovr_owner=None, ovr_key=None):
        if not app:
            return None
        oo = ovr_owner if ovr_owner is not None else owner
        kk = ovr_key if ovr_key is not None else key
        d = oo.states.get(kk)
        if d is None:
            rec = x.provenance.get(oo.provenance_id)
            d = rec.value_state if rec is not None else "MISSING"
        if v is None:
            return "MISSING"
        if d == "DERIVED":
            return "DERIVED"
        if v == 0:
            return "EXPLICIT_ZERO"
        return d
    items = []          # (order, row, pos, path, state)
    for p_, (tag, f) in enumerate(SYS1):
        if tag == "p":
            items.append((0, 0, p_, "project.gross_floor_area", state(x.project, f, x.project.gross_floor_area)))
        elif tag == "m":
            for i, r in enumerate(M):
                items.append((1, i, p_, "materials[%d].%s" % (i, f), state(r, f, _get(r, f))))
        elif tag == "e":
            for i, r in enumerate(EQ):
                app = True if f != "service_life" else (r.service_life is not None or r.replacement_event_list is None)
                items.append((2, i, p_, "equipment[%d].%s" % (i, f), state(r, f, _get(r, f), app)))
        elif tag in ("r", "rn"):
            for i, r in enumerate(D):
                if tag == "r":
                    items.append((3, i, p_, "refrigerants[%d].%s" % (i, f), state(r, f, _get(r, f))))
                else:
                    app = r.service_life is None and r.change_years is None
                    items.append((3, i, p_, "refrigerants[%d].service_life" % i, state(r, "service_life", None, app)))
        elif tag == "ce":
            items.append((4, 0, p_, "construction.electricity_kwh", state(x.construction, f, x.construction.electricity_kwh)))
        elif tag in ("cf", "cw"):
            lst = "fuels" if tag == "cf" else "waste_streams"
            for i, r in enumerate(getattr(x.construction, lst)):
                items.append((5 if tag == "cf" else 6, i, p_, "construction.%s[%d].%s" % (lst, i, f),
                              state(r, f, getattr(r, f), True, x.construction, "%s[%d].%s" % (lst, i, f))))
        elif tag in ("dd", "dh"):
            lst = "demolition_activities" if tag == "dd" else "waste_hauls"
            for i, r in enumerate(getattr(x.end_of_life, lst)):
                items.append((7 if tag == "dd" else 8, i, p_, "end_of_life.%s[%d].%s" % (lst, i, f),
                              state(r, f, getattr(r, f), True, x.end_of_life, "%s[%d].%s" % (lst, i, f))))
    for it in items:
        if it[4] is not None:
            cnt[it[4]] += 1
    viol = [it[3] for it in sorted(items, key=lambda t: (t[0], t[1], t[2])) if it[4] == "MISSING"]
    R["SYS-01"] = {"ok": cnt["MISSING"] == 0, "counts": cnt, "violations": viol}
    reads.setdefault("SYS-01", set())
    # ---- SYS-02 (uses and pure unit conversions; see the site table of the ledger)
    def rec(f):
        return f is not None and f in x.factors

    def conv_ok(a, f, extra=()):
        return cv(x, a, x.factors[f].unit, extra) is not None
    paths, n, sm = set(), 0, {}

    def use(path, app, unit_present, f, a, stage, extra=()):
        nonlocal n
        if not app:
            return
        n += 1
        bad = (unit_present is False) or (unit_present is not False and rec(f) and not conv_ok(a, f, extra))
        if bad:
            paths.add(path)
        if unit_present is not False and rec(f) and list(x.factors[f].stages) != [stage]:
            sm[f] = sm.get(f, 0) + 1

    def unit_site(path, app, preds):
        nonlocal n
        if not app:
            return
        n += 1
        if not all(preds):
            paths.add(path)
    for i, r in enumerate(M):
        up = r.quantity_unit is not None
        use("materials[%d].quantity_unit" % i, r.composition is None, up, r.factor_id, r.quantity_unit, "A1-A3", r.conversions)
        for c in (r.composition or []):
            use("materials[%d].composition" % i, True, None, c.factor_id, "kg", "A1-A3")
        t = r.transport
        use("materials[%d].quantity_unit" % i, t.delivery_factor_id is not None, up, t.delivery_factor_id, r.quantity_unit, "A4", r.conversions)
        use("materials[%d].transport" % i, t.delivery_factor_id is None, None, t.factor_id, "tkm", "A4")
        use("materials[%d].quantity_unit" % i, r.installation_factor_id is not None, up, r.installation_factor_id, r.quantity_unit, "A5",
            r.conversions)
        use("materials[%d].end_of_life" % i, True, None, r.end_of_life.haul_factor_id, "tkm", "C2")
        for rt in r.end_of_life.routes:
            use("materials[%d].end_of_life" % i, True, None, rt.factor_id, "kg", "C4" if rt.route == "LANDFILL" else "C3")
        unit_site("materials[%d].quantity_unit" % i, r.composition is not None, [cv(x, r.quantity_unit, "kg", r.conversions) is not None])
    for j, qq in enumerate(EQ):
        up = qq.quantity_unit is not None
        use("equipment[%d].quantity_unit" % j, True, up, qq.factor_id, qq.quantity_unit, "A1-A3")
        use("equipment[%d].quantity_unit" % j, qq.delivery_factor_id is not None, up, qq.delivery_factor_id, qq.quantity_unit, "A4")
        use("equipment[%d].quantity_unit" % j, qq.installation_factor_id is not None, up, qq.installation_factor_id, qq.quantity_unit, "A5")
        use("equipment[%d].end_of_life" % j, qq.eol_factor_id is not None, None, qq.eol_factor_id, "kg", "C3")
    for i, fu in enumerate(x.construction.fuels):
        use("construction.fuels[%d].unit" % i, True, fu.unit is not None, fu.factor_id, fu.unit, "A5", fu.conversions)
    for i, ws in enumerate(x.construction.waste_streams):
        use("construction.waste_streams[%d]" % i, True, None, ws.factor_id, "kg", "A5")
    op, wwt = x.operation, x.water_waste
    for name, p, fid, st in (("operation.gas", op.gas, op.gas_factor_id, "B6"), ("operation.oil", op.oil, op.oil_factor_id, "B6"),
                             ("operation.district_heat", op.district_heat, op.district_heat_factor_id, "B6"),
                             ("water_waste.water", wwt.water, wwt.water_factor_id, "B7"),
                             ("water_waste.sewage", wwt.sewage, wwt.sewage_factor_id, "B7"),
                             ("water_waste.municipal_waste", wwt.municipal_waste, wwt.waste_factor_id, "B7")):
        au = aunit(p.unit)
        use(name, True, au is not None, fid, au, st)
    for i, a in enumerate(x.end_of_life.demolition_activities):
        use("end_of_life.demolition_activities[%d].unit" % i, True, a.unit is not None, a.factor_id, a.unit, "C1")
    for i, h in enumerate(x.end_of_life.waste_hauls):
        use("end_of_life.waste_hauls[%d]" % i, True, None, h.factor_id, "tkm", "C2")
    sq = x.summary_quantities
    use("summary_quantities.concrete_uptake", sq.concrete_uptake_factor_id is not None, None, sq.concrete_uptake_factor_id, "m3", "MEMO")
    for i, c in enumerate(x.cost_items):
        use("cost_items[%d]" % i, True, c.currency is not None, c.factor_id, c.currency, "A1-A3")
    g = op.grid
    gu = gunit(g)
    eu = aunit(op.electricity.unit)
    unit_site("construction.electricity", True, [gu is not None, gu is not None and cv(x, "kWh", gu) is not None])
    unit_site("operation.electricity", True, [eu is not None, gu is not None, eu is not None and gu is not None and cv(x, eu, gu) is not None])
    for name, p in (("operation.onsite_generation", op.onsite_generation), ("operation.onsite_export", op.onsite_export)):
        au = aunit(p.unit)
        unit_site(name, True, [au is not None, eu is not None, au is not None and eu is not None and cv(x, au, eu) is not None])
    R["SYS-02"] = {"ok": not paths and not sm, "n_checked": n, "violations": sorted(paths),
                   "stage_mismatches": sorted("factors{%s}.stages" % f for f in sm)}
    reads.setdefault("SYS-02", set())
    # ---- SYS-03
    keys, n3, cntf, nbad = set(), 0, {}, [0]

    def ref(path, app, f):
        nonlocal n3
        if not app:
            return
        n3 += 1
        if f is None:
            keys.add(path + " (no factor)"); nbad[0] += 1
        elif f not in x.factors:
            keys.add("factors{%s} (no record)" % f); nbad[0] += 1
        else:
            cntf[f] = cntf.get(f, 0) + 1
    for i, r in enumerate(M):
        ref("materials[%d].factor_id" % i, r.composition is None, r.factor_id)
        for k, c in enumerate(r.composition or []):
            ref("materials[%d].composition[%d].factor_id" % (i, k), True, c.factor_id)
        ref("materials[%d].epd.factor_id" % i, r.epd is not None, r.epd.factor_id if r.epd is not None else None)
        ref("materials[%d].installation_factor_id" % i, r.installation_factor_id is not None, r.installation_factor_id)
        t = r.transport
        ref("materials[%d].transport.delivery_factor_id" % i, t.delivery_factor_id is not None, t.delivery_factor_id)
        ref("materials[%d].transport.factor_id" % i, t.delivery_factor_id is None, t.factor_id)
        ref("materials[%d].end_of_life.haul_factor_id" % i, True, r.end_of_life.haul_factor_id)
        for k, rt in enumerate(r.end_of_life.routes):
            ref("materials[%d].end_of_life.routes[%d].factor_id" % (i, k), True, rt.factor_id)
    for j, qq in enumerate(EQ):
        ref("equipment[%d].factor_id" % j, True, qq.factor_id)
        ref("equipment[%d].eol_factor_id" % j, qq.eol_factor_id is not None, qq.eol_factor_id)
        ref("equipment[%d].delivery_factor_id" % j, qq.delivery_factor_id is not None, qq.delivery_factor_id)
        ref("equipment[%d].installation_factor_id" % j, qq.installation_factor_id is not None, qq.installation_factor_id)
    for i, fu in enumerate(x.construction.fuels):
        ref("construction.fuels[%d].factor_id" % i, True, fu.factor_id)
    for i, ws in enumerate(x.construction.waste_streams):
        ref("construction.waste_streams[%d].factor_id" % i, True, ws.factor_id)
    for nm, f in (("operation.gas_factor_id", op.gas_factor_id), ("operation.oil_factor_id", op.oil_factor_id),
                  ("operation.district_heat_factor_id", op.district_heat_factor_id), ("water_waste.water_factor_id", wwt.water_factor_id),
                  ("water_waste.sewage_factor_id", wwt.sewage_factor_id), ("water_waste.waste_factor_id", wwt.waste_factor_id)):
        ref(nm, True, f)
    for i, a in enumerate(x.end_of_life.demolition_activities):
        ref("end_of_life.demolition_activities[%d].factor_id" % i, True, a.factor_id)
    for i, h in enumerate(x.end_of_life.waste_hauls):
        ref("end_of_life.waste_hauls[%d].factor_id" % i, True, h.factor_id)
    ref("summary_quantities.concrete_uptake_factor_id", sq.concrete_uptake_factor_id is not None, sq.concrete_uptake_factor_id)
    for i, c in enumerate(x.cost_items):
        ref("cost_items[%d].factor_id" % i, True, c.factor_id)
    okq = lambda f: x.factors[f].licence_status == PP and bool(x.factors[f].source_url)
    nlic = 0
    for f, c in cntf.items():
        if not okq(f):
            keys.add("factors{%s}.licence_status" % f)
            nlic += c
    gbad = g.licence_status != PP
    if gbad:
        keys.add("operation.grid")
    naff = nbad[0] + nlic + (1 if gbad else 0)
    R["SYS-03"] = {"ok": naff == 0, "n_checked": n3 + 1, "violations": sorted(keys), "n_references_affected": naff}
    reads.setdefault("SYS-03", set())


# ---------------------------------------------------------------- (e) 節点と跳び（区切り点そのもの・その前後の浮動小数）
def sw(tau):
    """事象の切り替え点 sw(tau)：tau < fl(T fl(1-eps)) となる最小の浮動小数 T（17 章 03 の L-2）。"""
    T = tau / (1.0 - EPS)
    while tau < T * (1.0 - EPS):
        T = math.nextafter(T, -math.inf)
    while not (tau < T * (1.0 - EPS)):
        T = math.nextafter(T, math.inf)
    return T


def all_events(x, H):
    """(tau, 種類, 行) の一覧：資材の更新周期、設備の一覧・耐用年数、冷媒の一覧・耐用年数、大型改修の周期（T = H まで）。"""
    out = []
    for i, r in enumerate(x.materials):
        out += [(t, "mat", i) for t in Eper(H, r.refresh_cycle)]
    for j, q in enumerate(x.equipment):
        L = q.replacement_event_list
        out += [(t, "eq", j) for t in (Elst(H, L) if L is not None else Eper(H, q.service_life))]
    for d, r in enumerate(x.refrigerants):
        L = r.change_years
        out += [(t, "ref", d) for t in (sorted(Elst(H, L)) if L is not None else Eper(H, r.service_life))]
    out += [(t, "ren", 0) for t in Eper(H, x.boundary.replacement_cycle)]
    return out


def predicted_jumps(x, b, evs, R):
    """時間の形（02 の各単位の「T：」）から求めた、切り替え点 b での跳びの理論値（台帳の独立の評価の内部量を使う）。
    B4-02：その時刻の事象の 1 回分の排出の和。B5-01：φ A^base × 回数。B3-01：-a_ρ w_k(b)（その年セルの最初の事象のとき）。
    B1-03：Γ_e + Δ_e w_k(b)。B1-04：年セル K の最初の交換で κ (m0 - u_K (1 - [¬tu] r (b-K)))。"""
    um, ue = R["_b4u"]
    st = R["_b1state"]
    Y = math.ceil(b)
    K = Y - 1
    J = {"B4-02": [], "B5-01": [], "B3-01": [], "B1-03": [], "B1-04": []}
    here = [(t, k, i) for (t, k, i) in evs if sw(t) == b]
    bd = x.boundary
    for t, kind, i in here:
        kc = kcell(t)
        if kind == "mat":
            J["B4-02"].append(um[i])
        elif kind == "eq":
            J["B4-02"].append(ue[i])
        elif kind == "ren" and bd.reconstruction_scenario != "NONE" and in01(bd.reconstruction_scope_fraction):
            base = math.fsum(R[k]["value"] for k in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-04", "C1-01", "C2-01",
                                                     "C3-01", "C4-01", "X-14"))
            J["B5-01"].append(bd.reconstruction_scope_fraction * base)
        elif kind == "ref":
            d = x.refrigerants[i]
            s_ = st[i]
            if s_ is None:
                continue
            m0, r, qd, u, chi, ev = s_
            earlier = [t2 for t2 in ev if kcell(t2) == kc and t2 < t]
            first = not earlier and not any(t2 == t for t2 in ev[:ev.index(t)]) if t in ev else False
            if in01(d.replacement_loss_rate):
                lam = d.replacement_loss_rate
                if first:
                    J["B1-03"].append(lam * d.gwp * u[kc] * (1.0 - (0.0 if d.top_up else r * w(b, kc))))
                else:
                    J["B1-03"].append(lam * d.gwp * m0)
            if in01(d.end_of_life_recovery_rate) and first and kc == K:
                kap = (1.0 - d.end_of_life_recovery_rate) * d.gwp
                J["B1-04"].append(kap * (m0 - u[K] * (1.0 - (0.0 if d.top_up else r * (b - K)))))
    for a, ev in R["_b3rows"]:
        for t in ev:
            if sw(t) == b and not any(kcell(t2) == kcell(t) and t2 < t for t2 in ev):
                J["B3-01"].append(-a * w(b, kcell(t)))
                break
    return {u: math.fsum(v) for u, v in J.items()}


def knot_check(L, led, scen_list, rng, n_ev, n_lat, with_ref, System, scenarios, baseline, BASELINES, log):
    """区切り点 b（事象の切り替え点 sw(tau) と整数年）そのものと、その前後の浮動小数・tau 自身・tau と sw(tau) の中点で、
    統一系・台帳の式（eval_py）・独立の評価（・凍結した基準計算）を比べ、跳び V(b) - V(prev(b)) を比べる。"""
    res = {"n_scen": 0, "n_knots_event": 0, "n_knots_lattice": 0, "n_knots_integer_event": 0, "n_probe": 0, "n_probe_band": 0,
           "ind": {}, "led": {}, "ref_ind": {}, "jump": {"n": 0, "bad": 0, "bad_band": 0, "worst": 0.0, "ex": []},
           "pred": {"n": 0, "bad": 0, "bad_band": 0, "worst": 0.0, "by_unit": {}, "ex": []},
           "cont": {"n": 0, "bad": 0, "bad_band": 0, "ex": []}, "band": {"probes": 0, "units": {}, "max_rel": {}, "ex": []}}
    acc = {"ind": {}, "led": {}, "ref_ind": {}}
    SCALAR = ["B1-02", "B1-03", "B1-04", "B2-01", "B3-01", "B3-02", "B4-02", "B5-01", "B6-03", "B7-04", "X-08", "X-11", "SUM-01",
              "SUM-02", "SUM-03", "SUM-04", "SUM-05", "SUM-06", "X-07"]
    CONT = ("B1-02", "B2-01", "B6-03", "B7-04", "X-11")             # 事象でも格子でも跳ばない単位（帯の外）
    for s in scen_list:
        H = float(len(s.operation.grid.table))
        try:
            S0 = System(s, baselines=BASELINES)
        except Exception:
            continue
        res["n_scen"] += 1
        evs = all_events(s, H)
        taus = sorted({t for t, _, _ in evs if sw(t) <= H})
        intK = sorted({t for t in taus if t == round(t)})
        ev_knots = rng.sample(taus, min(n_ev, len(taus)))
        for t in intK[:6]:
            if t not in ev_knots:
                ev_knots.append(t)
        lat = set(rng.sample(range(1, int(H)), min(n_lat, int(H) - 1))) | {int(t) for t in intK[:6] if 1 <= t < H}
        res["n_knots_event"] += len(ev_knots)
        res["n_knots_lattice"] += len(lat)
        res["n_knots_integer_event"] += len([t for t in ev_knots if t in intK])
        probes = []
        for tau in ev_knots:
            b = sw(tau)
            pts = {"prev": math.nextafter(b, 0.0), "at": b, "next": math.nextafter(b, math.inf), "tau": tau}
            if b - tau > 4 * math.ulp(b):
                pts["mid"] = tau + 0.5 * (b - tau)
            probes.append(("event", tau, b, pts))
        for k in sorted(lat):
            b = float(k)
            probes.append(("lattice", b, b, {"prev": math.nextafter(b, 0.0), "at": b, "next": math.nextafter(b, math.inf)}))
        cache = {}

        def band(T):
            return any(t < T < sw(t) for t in intK)

        def at(T):
            if T in cache:
                return cache[T]
            r = None
            if 0.0 < T and math.ceil(T) <= H:
                sc = scenarios.with_period(s, T)
                try:
                    e = S0.at(T)
                    m, _ = run_all(sc, T, None, keep=True)
                    l = led.run(sc, T)
                    f = baseline.run_reference(sc) if with_ref else None
                    r = (e, m, l, f)
                except Exception as ex:
                    log("   knot probe failed %s T=%r %s" % (s.meta.scenario_id[:30], T, type(ex).__name__))
            cache[T] = r
            return r

        for kind, tau, b, pts in probes:
            vals = {}
            for nm, T in pts.items():
                r = at(T)
                if r is None:
                    continue
                vals[nm] = r
                e, m, l, f = r
                inb = band(T)
                res["n_probe"] += 1
                res["n_probe_band"] += inb
                sid = "%s|%s|T=%r" % (s.meta.scenario_id[:28], kind, T)
                for uid in [u["id"] for u in L["units"]]:
                    if uid == "SUM-08":
                        continue
                    mv = {k: v for k, v in m[uid].items() if not k.startswith("_")}
                    for nmA, got, want in (("ind", mv, public(e[uid])), ("led", public(l[uid]), public(e[uid])),
                                           ("ref_ind", mv, public(f[uid]) if f is not None else None)):
                        if want is None:
                            continue
                        key = (uid, "band" if inb else "out")
                        A = acc[nmA].setdefault(key, Acc())
                        before = A.n_mismatch
                        compare(got, {k: want[k] for k in got if k in want} if nmA == "ind" or nmA == "ref_ind" else want, uid, A, sid)
                        if nmA == "ind" and inb and A.n_mismatch > before:
                            res["band"]["units"][uid] = res["band"]["units"].get(uid, 0) + 1
                            gv, wv = mv.get("value"), want.get("value")
                            if isinstance(gv, float) and isinstance(wv, float) and wv != 0:
                                res["band"]["max_rel"][uid] = max(res["band"]["max_rel"].get(uid, 0.0), abs(gv - wv) / abs(wv))
                            if len(res["band"]["ex"]) < 6:
                                res["band"]["ex"].append({"scenario": s.meta.scenario_id, "T": T, "unit": uid, "engine": wv, "ledger": gv})
                if inb:
                    res["band"]["probes"] += 1
            if "prev" not in vals or "at" not in vals:
                continue
            (e0, m0, _, _), (e1, m1, _, _) = vals["prev"], vals["at"]
            inb = band(pts["prev"]) or band(pts["at"])
            for u in SCALAR:
                a0, a1, b0, b1 = e0[u].get("value"), e1[u].get("value"), m0[u].get("value"), m1[u].get("value")
                if None in (a0, a1, b0, b1):
                    continue
                je, jm = a1 - a0, b1 - b0
                scale = max(abs(a0), abs(a1), 1.0)
                res["jump"]["n"] += 1
                d = abs(je - jm) / scale
                if not inb:
                    res["jump"]["worst"] = max(res["jump"]["worst"], d)
                if d > 1e-9:
                    res["jump"]["bad_band" if inb else "bad"] += 1
                    if not inb and len(res["jump"]["ex"]) < 8:
                        res["jump"]["ex"].append({"scenario": s.meta.scenario_id, "kind": kind, "tau": tau, "unit": u, "engine": je, "ledger": jm})
                if u in CONT or (kind == "lattice" and u == "B3-01"):
                    res["cont"]["n"] += 1
                    if abs(je) > 1e-9 * scale:
                        res["cont"]["bad_band" if inb else "bad"] += 1
                        if not inb and len(res["cont"]["ex"]) < 8:
                            res["cont"]["ex"].append({"scenario": s.meta.scenario_id, "kind": kind, "knot": tau, "unit": u, "jump": je})
            if kind == "event":
                pj = predicted_jumps(s, pts["at"], evs, m1)
                inc = set(s.boundary.included_lifecycle_stages)
                pj["SUM-03"] = math.fsum([pj["B1-03"] + pj["B1-04"] if "B1" in inc else 0.0, pj["B3-01"] if "B3" in inc else 0.0,
                                          pj["B4-02"] if "B4" in inc else 0.0, pj["B5-01"] if "B5" in inc else 0.0])
                for u, p in pj.items():
                    a0, a1 = e0[u]["value"], e1[u]["value"]
                    res["pred"]["n"] += 1
                    bu = res["pred"]["by_unit"].setdefault(u, {"n": 0, "bad": 0, "nonzero": 0})
                    bu["n"] += 1
                    bu["nonzero"] += (p != 0.0)
                    d = abs((a1 - a0) - p) / max(abs(a0), abs(a1), 1.0)
                    if not inb:
                        res["pred"]["worst"] = max(res["pred"]["worst"], d)
                    if d > 1e-9:
                        res["pred"]["bad_band" if inb else "bad"] += 1
                        bu["bad"] += 1
                        if not inb and len(res["pred"]["ex"]) < 8:
                            res["pred"]["ex"].append({"scenario": s.meta.scenario_id, "tau": tau, "unit": u, "jump": a1 - a0, "predicted": p})
        log("   knots %s: %d event + %d lattice knots, %d probes" % (s.meta.scenario_id[:30], len(ev_knots), len(lat), res["n_probe"]))
    for nmA in acc:
        res[nmA] = {}
        for (uid, zone), A in sorted(acc[nmA].items()):
            res[nmA].setdefault(uid, {})[zone] = {"n_values": A.n_values, "n_mismatch": A.n_mismatch, "max_rel": A.max_rel,
                                                  "examples": A.examples[:2]}
    return res


# ---------------------------------------------------------------- (f) 入力の感度（統一系で入力を 1 つ動かす）
def _walk(obj, parts, rng):
    p = parts[0].rstrip("#")
    last = len(parts) == 1
    if isinstance(obj, dict):
        if not obj:
            return None
        k = rng.choice(sorted(obj, key=str))
        if p == "key" and last:
            return ("dictkey", obj, k)
        if p == "value" and last:
            return ("item", obj, k)
        return _walk(obj[k], parts, rng)
    if isinstance(obj, (list, tuple)):
        if not obj:
            return None
        if p == "value" and last:
            return ("item", obj, rng.randrange(len(obj)))
        return _walk(obj[rng.randrange(len(obj))], parts, rng)
    if not hasattr(obj, p):
        return None
    if last:
        return ("attr", obj, p, parts[0].endswith("#"))
    return _walk(getattr(obj, p), parts[1:], rng)


def _mutate(v, rng, x):
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + rng.choice([1, 2, -1])
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return 1.0
        return v * rng.choice([1.37, 0.61]) + rng.choice([0.0, 0.11])
    if isinstance(v, str):
        if v in x.factors and rng.random() < 0.5:
            others = [f for f in x.factors if x.factors[f].unit == x.factors[v].unit and f != v]
            if others:
                return rng.choice(sorted(others))
        if "/" in v:
            h, _, t = v.partition("/")
            return rng.choice([h + "_X/" + t, h + "/" + t + "_X"])
        return v + "_X"
    if isinstance(v, list) and v:
        w_ = list(v)
        i = rng.randrange(len(w_))
        w_[i] = _mutate(w_[i], rng, x)
        return w_
    return None


def perturb(s, path, rng):
    """入力の項目 path（unit_map の名前）の具体的な 1 か所を、型に合わせて動かした写し。値の無い所（⊥）は動かさない。"""
    x = copy.deepcopy(s)
    clean = path.replace(".__no_value__", "")
    tail = None
    if clean.endswith("~h") or clean.endswith("~t"):
        tail, clean = clean[-1], clean[:-2]
    for _ in range(12):
        h = _walk(x, clean.split("."), rng)
        if h is None:
            continue
        if h[0] == "dictkey":
            _, d, k = h
            nk = (k + "_X") if isinstance(k, str) else (k + 1)
            if nk in d:
                continue
            d[nk] = d.pop(k)
            return x, "%s: key %r -> %r" % (path, k, nk)
        if h[0] == "item":
            _, c, k = h
            v = c[k]
            nv = _mutate(v, rng, x)
            if nv is None or nv == v:
                continue
            c[k] = nv
            return x, "%s: %r -> %r" % (path, v, nv)
        _, o, a, presence = h
        v = getattr(o, a)
        if presence:
            if v is None:
                continue
            nv = None
        elif tail is not None and isinstance(v, str):
            hd, sep, tl = v.partition("/")
            nv = (hd + "_X" + sep + tl) if tail == "h" else (hd + sep + tl + "_X")
        else:
            nv = _mutate(v, rng, x)
            if nv is None or nv == v:
                continue
        try:
            setattr(o, a, nv)
        except Exception:
            continue
        return x, "%s: %r -> %r" % (path, v, nv)
    return None, None


def canon(path):
    """入力の項目の名前の正規形（#＝個数・有無、~h・~t＝単位の頭・尾、.value＝要素、__no_value__ は同じ項目とみなす）。"""
    p = path.replace(".__no_value__", "")
    p = re.sub(r"~[ht]$", "", p)
    p = p.replace("#", "")
    if p.endswith(".value") and not p.startswith("factors.value"):
        p = p[: -len(".value")]
    return p


def sensitivity_check(L, pop, rng, trials, System, BASELINES, log):
    """入力の項目を 1 つずつ動かし、統一系の公開出力が変わった単位について、その項目がその単位（または依存の閉包の単位）の
    宣言した入力（inputs_direct と inputs_notation）と、統一系の記録（inputs_reached）に含まれるかを調べる。"""
    U = {u["id"]: u for u in L["units"]}
    deps = {u: set(U[u]["depends_on_units"]) for u in U}

    def clos(u):
        out, st = set(), [u]
        while st:
            v = st.pop()
            if v not in out:
                out.add(v)
                st += list(deps[v])
        return out
    C = {u: clos(u) for u in U}
    direct = {u: {canon(x["path"]) for x in U[u]["inputs_direct"]} for u in U}
    notation = {u: {canon(p) for p in U[u].get("inputs_notation", [])} for u in U}
    reached = {u: {canon(p) for p in U[u]["inputs_reached"]} for u in U}
    decl = {u: set().union(*[direct[v] | notation[v] for v in C[u]]) for u in U}
    reach = {u: set().union(*[reached[v] for v in C[u]]) for u in U}
    fields = sorted(p for p in ({x["path"] for u in U.values() for x in u["inputs_direct"]} | {p for u in U.values() for p in u["inputs_reached"]}
                                | {p for u in U.values() for p in u.get("inputs_notation", [])})
                    if not p.endswith("__no_value__"))              # 行そのものの有無の擬似の項目は動かさない
    base = {s.meta.scenario_id: System(s, baselines=BASELINES).at(s.boundary.study_period) for s in pop}
    res = {"n_fields": len(fields), "n_perturbations": 0, "n_no_effect": 0, "n_unit_effects": 0, "n_engine_errors": 0,
           "missing_declared": {}, "missing_reached": {}, "declared_not_exercised": {}, "fields_never_perturbed": []}
    moved = {u: set() for u in U}
    for f in fields:
        did = False
        for s in pop:
            for _ in range(trials):
                x, desc = perturb(s, f, rng)
                if x is None:
                    continue
                did = True
                res["n_perturbations"] += 1
                try:
                    e = System(x, baselines=BASELINES).at(x.boundary.study_period)
                except Exception:
                    res["n_engine_errors"] += 1
                    continue
                b = base[s.meta.scenario_id]
                hit = False
                for u in U:
                    A = Acc()
                    compare(public(e[u]), public(b[u]), u, A, "")
                    if A.n_mismatch == 0:
                        continue
                    hit = True
                    res["n_unit_effects"] += 1
                    cf = canon(f)
                    moved[u].add(cf)
                    if cf not in decl[u]:
                        res["missing_declared"].setdefault("%s <- %s" % (u, cf), desc)
                    if cf not in reach[u]:
                        res["missing_reached"].setdefault("%s <- %s" % (u, cf), desc)
                res["n_no_effect"] += (not hit)
        if not did:
            res["fields_never_perturbed"].append(f)
    for u in U:
        nm = sorted(direct[u] - moved[u])
        if nm:
            res["declared_not_exercised"][u] = nm
    log("   sensitivity: %d fields, %d perturbations, missing declared %d, missing reached %d"
        % (len(fields), res["n_perturbations"], len(res["missing_declared"]), len(res["missing_reached"])))
    return res


# ---------------------------------------------------------------- (g) 役割・構成表・出力キー・依存の整合
def consistency_checks(L, specs_system, engine_keys, ind_reads):
    U = {u["id"]: u for u in L["units"]}
    deps = {u: set(U[u]["depends_on_units"]) for u in U}

    def clos(u):
        out, st = set(), [u]
        while st:
            v = st.pop()
            if v not in out:
                out.add(v)
                st += list(deps[v])
        return out
    res, problems = {}, []
    comp = sorted((c["stage"], u["id"], c["sign"], c["beta"]) for u in L["units"] for c in u["composition"])
    code = sorted((s, u, sg, "iota_B2" if (s, u) == ("B6", "B2-01") else "1") for s, u, sg in specs_system.COMP_ROWS)
    res["構成表の行が仕様（specs/system.py COMP_ROWS）と一致"] = comp == code
    if comp != code:
        problems.append("composition rows differ from specs/system.py COMP_ROWS")
    direct = [u for u in U if U[u]["role"] == "DIRECT"]
    feed = set().union(*[clos(d) for d in direct])
    c3 = clos("SUM-03")
    bad_aux = sorted(u for u in U if U[u]["role"] == "AUXILIARY" and u not in feed)
    bad_side = sorted(u for u in U if U[u]["role"] in ("REFERENCE", "BREAKDOWN", "DECISION") and u in c3)
    res["AUXILIARY のうち直接寄与する単位の入力にならないもの"] = bad_aux
    res["REFERENCE・BREAKDOWN・DECISION のうち C(T) の依存の閉包に入るもの"] = bad_side
    res["C(T)（SUM-03）の依存の閉包の単位の数"] = len(c3)
    problems += ["AUXILIARY unit %s does not feed a DIRECT unit" % u for u in bad_aux]
    problems += ["%s unit %s lies in the dependency closure of SUM-03" % (U[u]["role"], u) for u in bad_side]
    chk = sorted((s, u) for s, us in specs_system.STAGE_UNITS.items() for u in us)
    led_chk = sorted(tuple(p) for p in L.get("x02_chk", [])) if L.get("x02_chk") else None
    res["X-02 の完全性の対（CHK）が仕様と一致"] = (led_chk == chk) if led_chk is not None else "台帳に x02_chk が無い"
    if led_chk is not None and led_chk != chk:
        problems.append("X-02 CHK pairs differ from specs/system.py STAGE_UNITS")
    keyd = {}
    for u in U:
        lk = {o["key"] for o in U[u]["outputs"]}
        ek = engine_keys.get(u, set())
        if lk != ek:
            keyd[u] = {"台帳だけ": sorted(lk - ek), "統一系だけ": sorted(ek - lk)}
    res["出力キーの集合（台帳と、比べた全組の統一系の公開出力の和集合）が違う単位"] = keyd
    for u, d in keyd.items():
        if d["統一系だけ"]:
            problems.append("output keys of %s missing in the ledger: %s" % (u, d["統一系だけ"]))
    extra = {}
    for u, rd in ind_reads.items():
        if u in deps:
            ex = sorted(set(rd) - {u} - clos(u))
            if ex:
                extra[u] = ex
    res["独立の評価が読んだが台帳の依存の閉包に無い単位"] = extra
    problems += ["independent evaluation of %s reads %s outside the declared dependencies" % (u, v) for u, v in extra.items()]
    return res, problems


# ---------------------------------------------------------------- 本体
def _command(argv):
    """記録する実行の命令（出力・台帳・依存の表のパスは置き換える：作業場所のパスを資料に残さない）。"""
    out, skip = [], None
    for x in argv:
        if skip is not None:
            if skip:
                out.append(skip)
            skip = None
            continue
        if x in ("--json", "--ledger", "--deps"):          # --ledger・--deps は既定の data/ の台帳を指すものとして省く
            skip = "<OUT.json>" if x == "--json" else ""
            if x == "--json":
                out.append(x)
            continue
        out.append(x)
    return "python3 -B tools/check_units70.py " + " ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.join(BASE, "data", "units70.json"))
    ap.add_argument("--deps", default=os.path.join(BASE, "data", "unit_dependencies.csv"))
    ap.add_argument("--n", type=int, default=40, help="無作為のシナリオの数（規模 M まで）")
    ap.add_argument("--seed", type=int, default=880001)
    ap.add_argument("--t-per-scenario", type=int, default=3, help="シナリオごとの無作為の評価期間の数（自身の評価期間に加える）")
    ap.add_argument("--dirty", type=int, default=6)
    ap.add_argument("--special", type=int, default=1, help="特殊条件を作るシナリオの数（1 つにつき 10 種類）")
    ap.add_argument("--ref", action="store_true", help="凍結した基準計算とも比べる")
    ap.add_argument("--time-probe", type=int, default=0, help="(c) に使うシナリオの数")
    ap.add_argument("--knots", type=int, default=0, help="(e) 節点と跳びに使う無作為のシナリオの数（境界条件のシナリオを半数加える）")
    ap.add_argument("--knots-events", type=int, default=40, help="(e) シナリオごとの事象の節点の数（整数の時刻の事象を最大 6 個加える）")
    ap.add_argument("--knots-lattice", type=int, default=12, help="(e) シナリオごとの格子（整数年）の節点の数")
    ap.add_argument("--sensitivity", type=int, default=0, help="(f) 入力の感度に使うシナリオの数")
    ap.add_argument("--sens-trials", type=int, default=2, help="(f) 項目・シナリオごとの摂動の回数")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    t0 = time.time()
    L = load_ledger(a.ledger)
    sys.path.insert(0, RC)
    cwd = os.getcwd()
    os.chdir(RC)
    from tstudy import baseline, scenarios
    from tstudy.unified import System
    from checks import sets_unified
    from specs import system as specs_system
    reg = baseline.load()
    from synth import model, population
    os.chdir(cwd)

    def log(msg):
        print(msg, flush=True)

    st, problems = structure_checks(L, model, a.deps)
    log("(a) 構造: %s" % st)
    for p in problems:
        log("   problem: " + p)
    led = Ledger(L, population.BASELINES)
    rng = random.Random(a.seed)
    ids = [u["id"] for u in L["units"]]
    role = {u["id"]: u["role"] for u in L["units"]}

    pop = list(population.verification_population(a.n, a.seed, "M"))
    sets = []

    def periods(s, k):
        own = s.boundary.study_period
        return [own] + [round(rng.uniform(0.05, 129.9), 6) for _ in range(k)]
    sets.append(("R", "無作為のシナリオ（種 %d、%d 件、規模 M まで）×（自身の T＋無作為の T %d 個）" % (a.seed, a.n, a.t_per_scenario),
                 [(s.meta.scenario_id, s, periods(s, a.t_per_scenario)) for s in pop], True))
    sets.append(("E", "生成器の名前付きの境界条件×（自身の T＋無作為の T 1 個）",
                 [("edge " + n, s, periods(s, 1)) for n, s in population.edge_cases()], True))
    if a.dirty:
        sets.append(("D", "欠陥入り（種 %d から %d 件、定義域の外）×（60＋無作為の T 1 個）" % (a.seed + 100, a.dirty),
                     [(n, s, [60.0, round(rng.uniform(1.0, 120.0), 6)]) for n, s in sets_unified.dirty(a.seed + 100, a.dirty)], False))
    if a.special:
        sp_ = [c for c in sets_unified.new_special(pop[: a.special]) if c]
        sets.append(("X", "特殊条件（第 11 章の new_special の変異を無作為のシナリオに適用、定義域の外を含む）×（自身の T＋無作為の T 1 個）",
                     [(c[0], c[1], periods(c[1], 1)) for c in sp_], False))

    acc = {u: Acc() for u in ids}
    accr = {u: Acc() for u in ids}
    acci = {u: Acc() for u in ids}
    engine_keys = {u: set() for u in ids}
    ind_reads = {}
    set_rows = []
    n_pairs = 0
    for name, desc, entries, filt in sets:
        pairs = excl = 0
        for sid, s, Ts in entries:
            for T in Ts:
                sc = scenarios.with_period(s, T)
                if filt and scenarios.valid_domain(sc):
                    excl += 1
                    continue
                key = "%s|%s|T=%r" % (name, sid[:40], T)
                try:
                    eng = System(sc, baselines=population.BASELINES).at(T)
                except Exception as ex:              # 統一系が評価できない入力（Unusable など）は記録して飛ばす
                    excl += 1
                    log("   engine could not evaluate %s %s %s" % (key, type(ex).__name__, str(ex)[:80]))
                    continue
                mine = led.run(sc, T)
                ind, rd = run_all(sc, T, population.BASELINES)
                for u, v in rd.items():
                    ind_reads.setdefault(u, set()).update(v)
                ref = baseline.run_reference(sc) if a.ref else None
                pairs += 1
                for u in ids:
                    acc[u].pairs += 1
                    engine_keys[u] |= set(public(eng[u]))
                    compare(public(mine[u]), public(eng[u]), u, acc[u], key)
                    acci[u].pairs += 1
                    compare(public(ind[u]), public(eng[u]), u, acci[u], key)
                    if ref is not None:
                        accr[u].pairs += 1
                        compare(public(mine[u]), public(ref[u]), u, accr[u], key)
        set_rows.append({"name": name, "desc": desc, "pairs": pairs, "excluded": excl})
        n_pairs += pairs
        log("   set %s: pairs %d excluded %d (%.0f s)" % (name, pairs, excl, time.time() - t0))

    units_out = []
    for u in ids:
        A, I = acc[u], acci[u]
        row = {"id": u, "role": role[u], "pairs": A.pairs, "n_values": A.n_values, "n_mismatch": A.n_mismatch, "max_rel": A.max_rel,
               "bit_identical": (A.n_bit / A.n_float) if A.n_float else None, "examples": A.examples,
               "n_values_ind": I.n_values, "n_mismatch_ind": I.n_mismatch, "max_rel_ind": I.max_rel, "examples_ind": I.examples}
        if a.ref:
            R = accr[u]
            row.update(n_values_ref=R.n_values, n_mismatch_ref=R.n_mismatch, max_rel_ref=R.max_rel, examples_ref=R.examples,
                       bit_identical_ref=(R.n_bit / R.n_float) if R.n_float else None)
        units_out.append(row)
    by_role = []
    for rl in ["DIRECT", "AGGREGATE", "AUXILIARY", "REFERENCE", "DECISION", "BREAKDOWN"]:
        us = [x for x in units_out if x["role"] == rl]
        g = {"role": rl, "n_units": len(us), "pairs": n_pairs, "n_values": sum(x["n_values"] for x in us),
             "n_mismatch": sum(x["n_mismatch"] for x in us), "max_rel": max((x["max_rel"] for x in us), default=0.0),
             "n_values_ind": sum(x["n_values_ind"] for x in us), "n_mismatch_ind": sum(x["n_mismatch_ind"] for x in us),
             "max_rel_ind": max((x["max_rel_ind"] for x in us), default=0.0)}
        if a.ref:
            g["n_mismatch_ref"] = sum(x["n_mismatch_ref"] for x in us)
            g["max_rel_ref"] = max((x["max_rel_ref"] for x in us), default=0.0)
        by_role.append(g)
    not_checked = {u: "公開出力の値が 1 つも比べられなかった" for u in ids if acc[u].n_values == 0}
    not_checked_ind = {u: "独立の評価で値が 1 つも比べられなかった" for u in ids if acci[u].n_values == 0}

    # ------------------------------------------------------------ (c) T の形
    tp = None
    if a.time_probe:
        direct = [u["id"] for u in L["units"] if u["role"] == "DIRECT"]
        tdep = [u["id"] for u in L["units"] if u["role"] == "DIRECT" and u["time_dependent"]]
        tind = [u for u in direct if u not in tdep]
        targets = set(direct) | {"SUM-03", "SUM-05"}
        need = closure(L, targets)
        nint = nlin = nbad = nconst = nconst_bad = nh = nh_bad = 0
        worst = 0.0
        examples = []
        for s in pop[: a.time_probe]:
            H = float(len(s.operation.grid.table))
            bp = breakpoints(s, H)
            gaps = [(bp[i], bp[i + 1]) for i in range(len(bp) - 1) if bp[i + 1] - bp[i] > 1e-3]
            for lo, hi in rng.sample(gaps, min(12, len(gaps))):
                pts = [lo + (hi - lo) * f for f in (0.2, 0.5, 0.8)]
                vals = []
                for T in pts:
                    sc = scenarios.with_period(s, T)
                    if scenarios.valid_domain(sc):
                        vals = None
                        break
                    vals.append(led.run(sc, T, only=need))
                if vals is None:
                    continue
                nint += 1
                for u in tdep + ["SUM-03"]:
                    v = [vals[i][u]["value"] for i in range(3)]
                    nlin += 1
                    err = abs(v[1] - 0.5 * (v[0] + v[2]))
                    sc_ = max(abs(v[0]), abs(v[2]), 1.0)
                    worst = max(worst, err / sc_)
                    if err > 1e-9 * sc_:
                        nbad += 1
                        if len(examples) < 5:
                            examples.append({"unit": u, "interval": [lo, hi], "values": v})
                for u in tind:
                    nconst += 1
                    if not (vals[0][u]["value"] == vals[1][u]["value"] == vals[2][u]["value"]):
                        nconst_bad += 1
                v5 = [vals[i]["SUM-05"]["value"] for i in range(3)]
                if None not in v5:
                    nh += 1
                    tv = [pts[i] * v5[i] for i in range(3)]
                    if abs(tv[1] - 0.5 * (tv[0] + tv[2])) > 1e-9 * max(abs(tv[0]), abs(tv[2]), 1e-300):
                        nh_bad += 1
        tp = {"n_intervals": nint, "n_affine_checks": nlin, "n_affine_fail": nbad, "worst_rel": worst,
              "n_const_checks": nconst, "n_const_fail": nconst_bad, "n_sum05_checks": nh, "n_sum05_fail": nh_bad, "examples": examples,
              "units_affine": tdep + ["SUM-03"], "units_const": tind}
        tp["text"] = ("無作為のシナリオ %d 件で、区切り点（整数年、事象の時刻 τ と τ/(1−ε)）の間の幅 1e-3 年を超える区間を各 12 個まで選び、"
                      "区間の 0.2・0.5・0.8 の 3 点で台帳の式を評価した（定義域の外の点を含む区間は除外）。区間 %d 個。"
                      "T に依存する直接寄与の単位と SUM-03（%s）の 3 点の一次性：%d 件中 不一致 %d（中点の値と両端の平均の差の最大、相対 %.1e）。"
                      "T によらない直接寄与の単位（%d 単位）の値が 3 点で同じ（ビット一致）：%d 件中 不一致 %d。SUM-05 の T·値の一次性：%d 件中 不一致 %d。"
                      "[F]（浮動小数、区間の内側の標本。区切り点そのものは (e) で調べた）。"
                      % (a.time_probe, nint, "、".join(tdep + ["SUM-03"]), nlin, nbad, worst, len(tind), nconst, nconst_bad, nh, nh_bad))
        log("(c) " + tp["text"])

    # ------------------------------------------------------------ (e) 節点と跳び
    kn = None
    if a.knots:
        kpop = list(population.verification_population(a.knots, a.seed + 200, "M"))
        edge = [s for _, s in population.edge_cases()]
        kpop += rng.sample(edge, min(len(edge), max(1, a.knots // 2)))
        kn = knot_check(L, led, kpop, rng, a.knots_events, a.knots_lattice, a.ref, System, scenarios, baseline, population.BASELINES, log)
        kn["n_random"] = a.knots
        kn["seed"] = a.seed + 200

    # ------------------------------------------------------------ (f) 入力の感度
    sens = None
    if a.sensitivity:
        spop = list(population.verification_population(a.sensitivity, a.seed + 300, "M"))
        sens = sensitivity_check(L, spop, rng, a.sens_trials, System, population.BASELINES, log)
        sens["n_scenarios"], sens["trials"], sens["seed"] = a.sensitivity, a.sens_trials, a.seed + 300

    # ------------------------------------------------------------ (g) 整合
    cons, cprob = consistency_checks(L, specs_system, engine_keys, ind_reads)
    log("(g) 整合: %s" % {k: (v if not isinstance(v, (dict, list)) else len(v)) for k, v in cons.items()})
    for p in cprob:
        log("   problem: " + p)
    problems += cprob

    summ = {
        "command": _command(sys.argv[1:]),
        "when": time.strftime("%Y-%m-%d"),
        "seconds": round(time.time() - t0, 1),
        "structure": st, "problems": problems, "sets": set_rows, "n_pairs": n_pairs,
        "with_reference": bool(a.ref), "by_role": by_role, "units": units_out, "not_checked": not_checked,
        "not_checked_independent": not_checked_ind, "time_probe": tp, "knots": kn, "sensitivity": sens, "consistency": cons,
        "scope": ("凍結した生成器の架空のシナリオ（無作為 %d 件・境界条件・欠陥入り %d 件・特殊条件）と評価期間 %d 組。R・E は定義域の内側だけ、"
                  "D・X は定義域の外を含めて比べた（第 11 章の欠陥集合と同じ扱い）。年セルの終わりを越える事象の直後の帯は (b) の標本にほぼ入らず、(e) で狙って調べた"
                  % (a.n, a.dirty, n_pairs)),
    }
    tot_mis = sum(x["n_mismatch"] for x in units_out)
    tot_ind = sum(x["n_mismatch_ind"] for x in units_out)
    log("(b) pairs %d values %d mismatches %d (engine)%s; units with mismatch: %s" % (
        n_pairs, sum(x["n_values"] for x in units_out), tot_mis,
        (", %d (reference)" % sum(x["n_mismatch_ref"] for x in units_out)) if a.ref else "",
        [x["id"] for x in units_out if x["n_mismatch"]] or "none"))
    log("(d) independent: values %d mismatches %d; units with mismatch: %s" % (
        sum(x["n_values_ind"] for x in units_out), tot_ind, [x["id"] for x in units_out if x["n_mismatch_ind"]] or "none"))
    for x in units_out:
        if x["n_mismatch"] or x["n_mismatch_ind"] or (a.ref and x["n_mismatch_ref"]):
            log("    %s %d %d %s %s" % (x["id"], x["n_mismatch"], x["n_mismatch_ind"], x["examples"][:1], x["examples_ind"][:1]))
    if kn:
        log("(e) knots: %s" % {k: v for k, v in kn.items() if k in ("n_scen", "n_knots_event", "n_knots_lattice", "n_probe", "n_probe_band")})
        log("    jump %s pred %s cont %s" % ({k: v for k, v in kn["jump"].items() if k != "ex"}, {k: v for k, v in kn["pred"].items() if k not in ("ex", "by_unit")},
                                            {k: v for k, v in kn["cont"].items() if k != "ex"}))
        log("    band units %s max_rel %s" % (kn["band"]["units"], kn["band"]["max_rel"]))
        for nmA in ("ind", "led", "ref_ind"):
            out_bad = {u: z["out"]["n_mismatch"] for u, z in kn[nmA].items() if "out" in z and z["out"]["n_mismatch"]}
            log("    %s mismatches outside the band: %s" % (nmA, out_bad or "none"))
    if sens:
        for k in ("missing_declared", "missing_reached"):
            log("(f) %s: %d" % (k, len(sens[k])))
            for kk, v in sorted(sens[k].items())[:60]:
                log("    %s | %s" % (kk, v))
    log("not checked: %s %s | %.0f s" % (not_checked or "none", not_checked_ind or "", time.time() - t0))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(summ, f, ensure_ascii=False, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    knot_bad = bool(kn) and (kn["jump"]["bad"] or kn["pred"]["bad"] or kn["cont"]["bad"]
                             or any(z.get("out", {}).get("n_mismatch") for nmA in ("ind", "led", "ref_ind") for z in kn[nmA].values()))
    return 0 if (not problems and tot_mis == 0 and tot_ind == 0 and not knot_bad) else 1


if __name__ == "__main__":
    sys.exit(main())
