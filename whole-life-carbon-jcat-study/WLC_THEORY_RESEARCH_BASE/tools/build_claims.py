# -*- coding: utf-8 -*-
"""data/claims.csv を作る（式・定理・主張・検証件数・70 単位・仮説・未解決 → 本基盤の節・区分・原典・コード）。

使い方（研究基盤のフォルダで）：
    python3 -B tools/build_claims.py            # data/claims.csv を書く
    python3 -B tools/build_claims_md.py         # 12_原典とコード対応表.md と data/claims_by_source.csv を書く

読むもの：tools/claims_curated.py（手で選んだ F・C 行と T-57 以降の行）、data/theorems.csv、data/verification_counts.csv、
data/units70.json、data/hypotheses.csv、09_未解決問題と限界.md、02_70評価単位の完全台帳.md。
git は読み取りだけ（コードの最終コミットを `git log -1 --format=%h f2ea616 -- <パス>` で取る）。研究コードは読まない・動かさない。
標準ライブラリだけ。__pycache__ を作らない（python3 -B）。
"""
import csv
import io
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import claims_curated as curated  # noqa: E402

BASE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)
STUDY = os.path.dirname(BASE)
WT = os.path.dirname(STUDY)
REV = "f2ea616"
BASEC = "（本基盤）"

# ------------------------------------------------------------------ helpers
_commit_cache = {}


def git_commit(rel):
    """rel は whole-life-carbon-jcat-study/ からの相対。"""
    if not rel or rel.startswith("WLC_THEORY_RESEARCH_BASE/"):
        return BASEC if rel else ""
    if rel in _commit_cache:
        return _commit_cache[rel]
    full = os.path.join(STUDY, rel.rstrip("/"))
    if not os.path.exists(full):
        _commit_cache[rel] = "（所在なし）"
        return _commit_cache[rel]
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    out = subprocess.run(["git", "-C", WT, "log", "-1", "--format=%h", REV, "--",
                          "whole-life-carbon-jcat-study/" + rel.rstrip("/")],
                         capture_output=True, text=True, env=env, check=False).stdout.strip()
    _commit_cache[rel] = out or "（不明）"
    return _commit_cache[rel]


def split_outside_parens(text, seps=("、", "・", ";")):
    parts, buf, depth = [], [], 0
    for ch in text:
        if ch in "（(":
            depth += 1
        elif ch in "）)":
            depth = max(0, depth - 1)
        if depth == 0 and ch in seps:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf).strip())
    return [p for p in parts if p]


def parse_code_field(text):
    """theorems.csv の code 列などを [(path, funcs)] に。"""
    if not text or text.strip() in ("—", "-"):
        return []
    out, prev = [], None
    for piece in split_outside_parens(text):
        m = re.match(r"^([^（(]+)(?:[（(](.*)[）)])?(.*)$", piece)
        if not m:
            continue
        path, funcs = m.group(1).strip(), (m.group(2) or "").strip()
        if not re.search(r"\.(py|json|md)$|/$", path):
            # 関数名だけの断片や説明はコードの説明として前の要素に足す
            if out:
                out[-1] = (out[-1][0], (out[-1][1] + "・" + piece).strip("・"))
            continue
        if not re.match(r"^(\d\d_|research_archive|WLC_THEORY)", path) and prev:
            segs = prev.split("/")
            first = path.split("/")[0]
            if "/" in path and first in segs:
                path = "/".join(segs[:segs.index(first)] + path.split("/"))
            else:
                path = "/".join(segs[:-1] + [path]) if not prev.endswith("/") else prev + path
        out.append((path, funcs))
        prev = path
    return out


SRC_RE = re.compile(r"((?:\d\d_[A-Za-z0-9_]+|research_archive)/[^@\s、；;]*?)`?@([0-9a-f]{7})\s*([^、；;]*)")


def parse_sources(text):
    res = []
    for m in SRC_RE.finditer(text or ""):
        res.append((m.group(1), m.group(2), m.group(3).strip()))
    return res


def esc_md(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def join_sources(srcs):
    return (" ; ".join(p for p, c, sec in srcs), " ; ".join(c for p, c, sec in srcs), " ; ".join(sec for p, c, sec in srcs))


def join_code(code):
    paths = [p for p, f in code]
    return (" ; ".join(paths), " ; ".join(git_commit(p) for p in paths), " ; ".join(f for p, f in code))


# ------------------------------------------------------------------ rows
FIELDS = ["id", "kind", "orig_id", "statement", "latex", "class", "scope", "base_ref",
          "source_path", "source_commit", "source_section", "code_path", "code_commit", "code_function",
          "checked_by", "lineage", "note"]
rows = []


def mk(id_, kind, orig, statement, latex, cls, scope, base_ref, srcs, code, checked, lineage, note):
    sp, sc, ss = join_sources(srcs)
    cp, cc, cf = join_code(code)
    return dict(zip(FIELDS, [id_, kind, orig, statement, latex, cls, scope, base_ref, sp, sc, ss, cp, cc, cf, checked, lineage, note]))


# F rows (curated)
for r in curated.ROWS:
    if r[1] == "formula":
        rows.append(mk(*r))

# T rows: theorems.csv + extra
TH_REF = {
    "10.D-01": "04 §3 (R1・R3)；03 §4.7；08 §1.1",
    "10.D-03-1": "03 §3.2；05 §2.1；08 §1.1",
    "10.D-03-4": "05 §2.1・§3.3；03 §5.3；08 §1.1",
    "10.D-08-a": "05 §7.1；03 §5.5；08 §1.1",
    "10.D-08-c": "05 §7.1；04 §3 (R9)；03 §5.5；08 §1.1",
    "10.D-08-d": "05 §7.1；04 §3 (R9)；03 §5.5；08 §1.1",
    "10.D-09": "05 §7.3・§7.4；03 §5.4；08 §1.1",
    "10.D-09-b": "05 §7.3・§7.5；08 §1.5；09 OQ-11",
    "14.COMP": "06 §3.1〜§3.3；03 §6.2；02 §4",
    "17.L-1": "05 §3.3；08 §1.2",
    "17.L-2": "05 §3.2；03 §3.3；08 §1.2",
    "17.TH-0i": "05 §3.5；03 §5.6；08 §1.2",
    "17.TH-1": "05 §4.1；08 §1.2",
    "17.TH-2.1": "05 §4.2；08 §1.2",
    "17.TH-2.2": "05 §4.2；08 §1.2",
    "17.TH-2.3": "05 §4.3；03 §3.4；08 §4.1；09 OQ-07",
    "17.TH-2.4": "05 §4.2；08 §1.2",
    "17.TH-3": "05 §4.4；08 §1.2",
    "17.TH-4": "05 §5.1；07 §2.2；03 §7；08 §1.2",
    "17.TH-4a": "05 §5.1；07 §2.2",
    "17.TH-4b": "05 §5.1；07 §2.2",
    "17.TH-4c": "05 §5.1；07 §2.2・§8.2；09 OQ-25",
    "17.TH-4d": "05 §5.1；07 §2.2",
    "17.TH-5": "05 §5.2",
    "17.TH-6": "05 §5.3",
    "17.TH-7": "05 §8.1；03 §7",
    "17.TH-8": "05 §8.3",
    "17.TH-8b.1": "05 §8.2",
    "17.TH-8b.2": "05 §8.2",
    "17.TH-9": "05 §8.5；09 OQ-31",
    "17.TH-9s": "05 §7.2；09 OQ-13",
    "17.TH-10": "05 §8.4；09 OQ-31",
    "17.TH-11a": "05 §6.1；03 §5.5；15 §5.2",
    "17.TH-11b": "05 §6.1",
    "17.TH-11c": "05 §6.1",
    "17.TH-11d": "05 §6.2",
    "17.TH-11e": "05 §6.3；09 OQ-30",
    "17.TH-12": "05 §10.5",
    "17.TH-13": "05 §10.5；09 OQ-32",
    "17.TH-14": "05 §10.4；03 §5.6",
    "17.MIN": "05 §9.2；04 §7.1；09 OQ-21",
    "17.WAV": "05 §8.6；09 OQ-31",
    "17.CONV": "05 §8.7；07 §5.5",
    "18.REC": "07 §6.1；03 §7；08 §1.3",
    "18.T1": "07 §8.3；08 §1.3；09 OQ-25",
    "18.T2": "07 §8.3；08 §1.3",
    "18.REL-P07": "07 §5.2；08 §1.3",
    "18.REL-STATE": "07 §5.4；09 OQ-29",
    "18.YEAR": "07 §4.2；08 §1.3",
    "16.L1": "04 §4.1；08 §1.4",
    "16.C1": "04 §4.1；08 §1.4",
    "16.T1": "04 §6.1；08 §1.4；09 OQ-19",
    "16.T2": "04 §6.1；08 §1.4；09 OQ-19",
    "16.IMP": "04 §6.1；08 §1.4；09 OQ-19",
    "16.CERT": "04 §6.2；08 §1.4",
    "19.CONSTR": "04 §6.3；08 §1.4",
}
tid = {}
th_rows = list(csv.DictReader(open(os.path.join(BASE, "data/theorems.csv"), encoding="utf-8")))
missing = [r["id"] for r in th_rows if r["id"] not in TH_REF]
assert not missing, missing
n = 0
trows = []
for r in th_rows:
    n += 1
    i = f"T-{n:02d}"
    tid[r["id"]] = i
    srcs = parse_sources(r["proof_source"])
    lineage = "B" if r["id"].startswith(("16.", "19.")) else "A"
    trows.append(mk(i, "theorem", r["id"], r["statement_short"], "", r["class"], r["scope"], TH_REF[r["id"]], srcs,
                    parse_code_field(r["code"]), r["checked_by"], lineage, "data/theorems.csv の行"))
for r in curated.TEXTRA:
    n += 1
    i = f"T-{n:02d}"
    orig, stmt, cls, scope, bref, srcs, code, checked, lineage, note = r
    tid[orig] = i
    trows.append(mk(i, "theorem", orig, stmt, "", cls, scope, bref, srcs, code, checked, lineage, note))
rows.extend(trows)

# C rows
for r in curated.ROWS:
    if r[1] == "claim":
        rows.append(mk(*r))

# V rows
vrows = list(csv.DictReader(open(os.path.join(BASE, "data/verification_counts.csv"), encoding="utf-8")))
R = curated.R
C17, C18, C20 = curated.C17, curated.C18, curated.C20


def vcode(k):
    if k in (1, 2, 5):
        return [("09_APPROX_STUDY/research_code/bench/verify_unified.py", "（照合）")]
    if k in (3, 4):
        return []
    if k == 6:
        return [(R + "experiments/exp01_rampstep_sweep.py", "main")]
    if k == 7:
        return [(R + "experiments/exp02_knot_spectrum.py", "main")]
    if k in (8, 9):
        return [(R + "experiments/exp03_fourier_counting.py", "main")]
    if k == 10:
        return [(R + "experiments/exp04_pod_time_curves.py", "main")]
    if 11 <= k <= 21:
        return [(R + "checks/check_unified.py", "main"), (R + "checks/sets_unified.py", "（集合）")]
    if k in (22, 23):
        return [(R + "checks/check_unified_controls.py", "main")]
    if k in (24, 25):
        return [(R + "experiments/expU1_b14_forms.py", "main")]
    if 26 <= k <= 30:
        return [(R + "experiments/expU2_cross_engines.py", "main")]
    if k == 31:
        return [("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results/external_engines.json", "command（main の GitHub Actions で実行）")]
    if k in (32, 33):
        return [(R + "experiments/expU3_intermediate_state.py", "main")]
    if 34 <= k <= 39:
        return [(C17 + "verify_canon.py", "main")]
    if k == 40:
        return [(C17 + "density_check.py", "main")]
    if 41 <= k <= 48:
        return [(C17 + "timechar_terms.py", "S1〜S6")]
    if 49 <= k <= 52:
        return [(C17 + "timechar.py", "th0123・th6")]
    if k == 53:
        return [(C17 + "lattice_jumps.py", "main")]
    if k == 54:
        return [(C17 + "timechar.py", "tswitch・tstar")]
    if 55 <= k <= 57:
        return [(C17 + "timechar.py", "laplace_closed・th78")]
    if k == 58:
        return [(C17 + "timechar.py", "th10")]
    if 59 <= k <= 63:
        return [(C17 + "sliver_test.py", "main")]
    if 64 <= k <= 71:
        return [(C17 + "units_eq.py", "main")]
    if k in (72, 73):
        return [(C17 + "h_test.py", "main")]
    if k == 74:
        return [(C17 + "expand.py", "main")]
    if k == 75:
        return [(C17 + "units_time.py", "main")]
    if 76 <= k <= 79:
        return [(C18 + "dynlca.py", "analyse")]
    if k == 80:
        return [(C18 + "dynlca.py", "ext_analysis"), (C18 + "extensions.py", "timeline")]
    if 92 <= k <= 99:
        return [(C20 + "run4.py", "negative_controls"), (C20 + "agg4.py", "（集計）")]
    if 81 <= k <= 102:
        return [(C20 + "run4.py", "scenario_checks・checks_on"), (C20 + "agg4.py", "（集計）")]
    if 103 <= k <= 111:
        return [("15_JCAT_CONVERSION/tools/compile2.py", "（変換器）"), ("15_JCAT_CONVERSION/tools/excel_ref.py", "（参照評価器）")]
    if 112 <= k <= 116:
        return [("16_UNRESOLVED8_EXACT_APPROX/tools/synth_all.py", "（合成データ）"), ("16_UNRESOLVED8_EXACT_APPROX/tools/exact8.py", "（方式 A）")]
    if k == 117:
        return [("16_UNRESOLVED8_EXACT_APPROX/tools/test_powexp.py", "（推定）")]
    if 118 <= k <= 120:
        return [("16_UNRESOLVED8_EXACT_APPROX/tools/run8.py", "（原版が要る）"), ("16_UNRESOLVED8_EXACT_APPROX/tools/agg8.py", "（件数）")]
    if 121 <= k <= 123 or k == 125:
        return [("19_JCAT_REMAINING12/tools/agg12.py", "（非公開の結果から件数だけ）")]
    if k == 124:
        return [("19_JCAT_REMAINING12/tools/test12.py", "（合成データ）"), ("19_JCAT_REMAINING12/tools/exact12.py", "（方式 A）")]
    return []


def vref(k):
    if k <= 5:
        return "08 §3.1" + ("・§4.3" if k in (3, 4) else "")
    if k <= 10:
        return "08 §3.5" + ("；05 §6.5" if k in (8, 9) else "；05 §8.8" if k == 10 else "")
    if k <= 21:
        return "08 §3.2；06 §7.2"
    if k <= 23:
        return "08 §3.3"
    if k <= 33:
        return "08 §3.4" + ("；05 §7.5" if k in (24, 25) else "")
    if k <= 75:
        return "08 §3.6" + ("；05 §4.3；09 OQ-07" if 59 <= k <= 63 else "；06 §7.1" if 34 <= k <= 38 else "")
    if k <= 80:
        return "08 §3.7；07 §6.2"
    if k <= 102:
        return "08 §3.8" + ("・§3.3" if 92 <= k <= 99 else "") + ("；06 §7.3" if k == 81 else "")
    return "08 §3.9"


for k, r in enumerate(vrows, 1):
    srcs = parse_sources(r["source"])
    lineage = "B" if r["check"].startswith(("15 ", "16 ", "19 ")) else "A"
    stmt = f"{r['check']}（{r['population']}）：件数 {r['n'] or '—'}、合格 {r['passed'] or '—'}、失敗 {r['failed'] or '—'}"
    note = r["note"]
    if 103 <= k <= 120 or 121 <= k <= 123 or k == 125:
        note = (note + "。" if note else "") + "原版または非公開資料が要る（NONPUBLIC_INDEX）。公開は件数だけ"
    if k == 117 or 103 <= k <= 111:
        note = (note + "。" if note else "") + "どのスクリプトがこの件数を出したかの記録は原典に無く、主な道具だけを挙げた"
    rows.append(mk(f"V-{k:03d}", "verification", r["check"].split(" ")[0] + " 章", stmt, "", r["class"],
                   f"許容差：{r['tolerance'] or '—'}", vref(k), srcs, vcode(k), "data/verification_counts.csv の行", lineage, note))

# U rows
units = json.load(open(os.path.join(BASE, "data/units70.json"), encoding="utf-8"))
sec_of = {}
cur = None
for line in open(os.path.join(BASE, "02_70評価単位の完全台帳.md"), encoding="utf-8"):
    m = re.match(r"^### (5\.\d+) ", line)
    if m:
        cur = m.group(1)
    m = re.match(r"^#### (\S+) ", line)
    if m and cur:
        sec_of[m.group(1)] = cur
for u in units["units"]:
    uid = u["id"]
    assert uid in sec_of, uid
    lc = u.get("ledger_check") or {}
    v11 = next((v for v in u.get("verification", []) if v.get("source") == "VER11" and "counts" in v), None)
    td = u.get("time_dependent")
    td = (td is True) or (str(td).lower() == "true")
    stmt = f"{u['name']}。役割 {u['role']}" + (f"（副：{u['role_secondary']}）" if u.get("role_secondary") else "") + \
        f"、段階 {u['stage']}、{'T に依存' if td else 'T によらない'}、導出 {u.get('derivation') or '—'}、構造 {u.get('route') or '—'}"
    scope = "架空データ。"
    checked = []
    if v11:
        c = v11["counts"]
        checked.append(f"[F] V11：統一系×基準計算 1,293 組で {c['n_compared']:,} 値・不一致 {c['n_mismatch']}・最大相対差 {c['max_rel']:.1e}")
    if lc:
        checked.append(f"[F] L：台帳の式×統一系 {lc.get('pairs')} 組で {lc.get('n_values'):,} 値・不一致 {lc.get('n_mismatch')}・最大相対差 {float(lc.get('max_rel') or 0):.1e}")
    if u["role"] == "DIRECT":
        checked.append("§4 の共通の記録（[P] TH-0、[E]、[F] 27,153 値、[S] 90,055 ケース）")
    ref_fn = u.get("reference_function") or ""
    mod, _, fn = ref_fn.rpartition(".")
    refpath = "09_APPROX_STUDY/research_code/" + mod.replace(".", "/") + ".py" if mod else ""
    srcs = [("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/UNITS_70.md", "ac291dd", f"{uid} の行"),
            ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results/unit_map.json", "ac291dd", uid)]
    if u["role"] == "DIRECT":
        srcs.append(("14_EQUATION_DISCLOSURE/07_建物全体の統一方程式_完全版.md", "4c38df6", "§3・§4"))
    code = [("10_TRANSFORM_STUDY/research_code/tstudy/unified.py", "System.at"),
            ("10_TRANSFORM_STUDY/research_code/specs/", "（仕様データ。ステップ数は units70.csv の steps_*）")]
    if refpath:
        code.append((refpath, fn + "（凍結した基準計算）"))
    code.append(("WLC_THEORY_RESEARCH_BASE/tools/check_units70.py", "（台帳の式 eval_py の照合）"))
    latex = (u.get("formula_latex") or "").strip()
    rows.append(mk(f"U-{uid}", "unit", uid, stmt, latex, "F", scope + "LaTeX の式と実行形の対応は手で書いたもの（機械的な照合なし、02 §7）",
                   f"02 §{sec_of[uid]} {uid}", srcs, code, "；".join(checked), "A", "全項目は data/units70.json"))

# HYP rows
for r in csv.DictReader(open(os.path.join(BASE, "data/hypotheses.csv"), encoding="utf-8")):
    srcs = parse_sources(r["related_sources"])
    code = []
    m = re.search(r"コード[：:]\s*([^。]+)", r["data_needed"])
    if m:
        for piece in split_outside_parens(m.group(1)):
            p = piece.strip()
            if re.match(r"^(tstudy|specs|checks|experiments)/", p):
                code.append(("10_TRANSFORM_STUDY/research_code/" + p.split("（")[0], ""))
            elif re.match(r"^\d\d_", p):
                code.append((p.split("（")[0], ""))
            elif p.startswith("tools/"):
                code.append(("WLC_THEORY_RESEARCH_BASE/" + p.split("（")[0], ""))
    rows.append(mk(r["id"], "hypothesis", r["id"], f"{r['title']}：{r['statement']}", "", "H", f"優先度 {r['priority']}。未検証",
                   f"10 {r['id']}；11 §3 {r['id']}", srcs, code, f"反証の条件：{r['falsification']}", "BASE（利用者の仮説を本基盤が登録）",
                   f"反対仮説：{r['opposing']}"))

# OQ rows
t09 = open(os.path.join(BASE, "09_未解決問題と限界.md"), encoding="utf-8").read()
abbr = {}
for line in t09.splitlines():
    m = re.match(r"^\| (\[[^|]+\]) \| (.+) \|$", line)
    if m and "`" in m.group(2):
        names = re.findall(r"\[[^\]]+\]", m.group(1))
        paths = re.findall(r"`([^`]+)`", m.group(2))
        commit = re.findall(r"@([0-9a-f]{7})", m.group(2))
        if not paths or not commit:
            continue
        first = paths[0]
        d = first.rsplit("/", 1)[0] + "/" if "/" in first else ""
        full = [first] + [p if "/" in p else d + p for p in paths[1:]]
        for j, nm in enumerate(names):
            abbr[nm] = (full[min(j, len(full) - 1)], commit[-1])
oq_tab = re.findall(r"^\| (OQ-\d\d) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", t09, re.M)
sections = re.split(r"^### (OQ-\d\d) ", t09, flags=re.M)
oq_text = {sections[i]: sections[i + 1] for i in range(1, len(sections) - 1, 2)}
for oid, title, kind_, closure, hyps in oq_tab:
    body = oq_text.get(oid, "")
    srcs = []
    for m in re.finditer(r"\[(\d\d/\d\d|\d\dR|[A-Z0-9]+)\]", body):
        key = "[" + m.group(1) + "]"
        if key in abbr and abbr[key] not in [(p, c) for p, c, _ in srcs]:
            srcs.append((abbr[key][0], abbr[key][1], ""))
        if len(srcs) >= 3:
            break
    for p, c, sec in parse_sources(body):
        if len(srcs) >= 4:
            break
        if (p, c) not in [(a, b) for a, b, _ in srcs]:
            srcs.append((p, c, sec))
    code = [(p, "") for p in dict.fromkeys(re.findall(r"`((?:\d\d_[^`]*?|tools/[^`]*?)\.py)`", body))][:3]
    code = [(("WLC_THEORY_RESEARCH_BASE/" + p) if p.startswith("tools/") else p, f) for p, f in code]
    rows.append(mk(oid, "open", oid, re.sub(r"\*\*", "", title), "", "未解決", f"種類：{kind_}。閉じ方：{closure}",
                   f"09 {oid}", srcs, code, "—", "A／B（項目による）", f"関係する仮説：{hyps}"))

# placeholder resolution
for r in rows:
    for k in ("statement", "scope", "checked_by", "note"):
        r[k] = re.sub(r"\{T:([^}]+)\}", lambda m: f"{tid[m.group(1)]}〔{m.group(1)}〕", r[k])

ids = [r["id"] for r in rows]
assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
with open(os.path.join(BASE, "data/claims.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
print("rows", len(rows), {k: sum(1 for r in rows if r["kind"] == k) for k in
                          ["formula", "theorem", "claim", "verification", "unit", "hypothesis", "open"]})
missing_code = sorted({p for r in rows for p in r["code_path"].split(" ; ") if p and git_commit(p) == "（所在なし）"})
print("missing code paths:", missing_code)
missing_src = sorted({p for r in rows for p in r["source_path"].split(" ; ") if p and not p.startswith("WLC_") and not os.path.exists(os.path.join(STUDY, p))})
print("missing source paths:", missing_src)
