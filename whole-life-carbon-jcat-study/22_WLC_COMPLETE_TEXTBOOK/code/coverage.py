"""知識の対応範囲の計測（利用者の試験対策システムの scoring.py・topics.py・cues.py の考え方を教材用に置き換えたもの）。

試験対策システムは「試験に出そうか」で論点に S/A/B/C の等級を付け、資料の量を決めた。教材では基準を変える：
  - 支える問題の数と種類：その節の知識を使う問題（problems.json の sections）の数と、12 種類のうち何種類か
  - 前提としての重さ：後の節・章から何回参照されるか（「第 N 章」「N.M 節」「式 (N.M)」の参照の数）
  - 等級による削除はしない。数が小さい節も、前提として参照される・研究の論点に対応するなら残す
さらに、用語が初出の前に使われていないか（**用語** の太字を定義の目印とする）を機械的に調べる。

  python3 -B coverage.py   → ../audit/coverage.json と、監査表に入れる表（audit/_coverage_tables.md）
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from textlib import norm  # noqa: E402

ROOT = HERE.parent
KINDS = ["用語の説明", "原理の説明", "数式の導出", "数値計算", "公式の変形", "工程間の比較", "時間関数の解析",
         "数学的な証明", "間違った数式の訂正", "新しい条件を与えた応用問題", "研究方法の選択と根拠", "理論の限界"]


def sections() -> list[dict]:
    """教材の節（"N.M"）を順に。章の冒頭の文は "N.0" とする。"""
    out = []
    for f in sorted((ROOT / "textbook").glob("ch*.md")):
        chap = None
        cur = None
        for ln in f.read_text(encoding="utf-8").splitlines():
            m1 = re.match(r"^#\s+第(\d+)章\s*(.*)$", ln)
            m2 = re.match(r"^##\s+(\d+\.\d+)\s+(.*)$", ln)
            if m1:
                chap = int(m1.group(1))
                cur = {"id": f"{chap}.0", "title": m1.group(2), "chapter": chap, "text": ""}
                out.append(cur)
            elif m2:
                cur = {"id": m2.group(1), "title": m2.group(2), "chapter": int(m2.group(1).split(".")[0]), "text": ""}
                out.append(cur)
            elif ln.startswith("## ") and cur is not None:   # 「この章のまとめ」など番号の無い節
                cur = {"id": f"{cur['chapter']}.S", "title": ln[3:].strip(), "chapter": cur["chapter"], "text": ""}
                out.append(cur)
            elif cur is not None:
                cur["text"] += ln + "\n"
            elif f.name.startswith("ch10"):
                cur = {"id": "A.0", "title": "付録", "chapter": 10, "text": ln + "\n"}
                out.append(cur)
    return out


REF_SEC = re.compile(r"(\d+)\.(\d+)\s*節")
REF_EQ = re.compile(r"式\s*[（(](\d+)\.(\d+)[)）]")
REF_CH = re.compile(r"第\s*(\d+)\s*章")


def references(secs: list[dict]) -> dict[str, set[str]]:
    """節 → それを参照する（別の）節の集合。章の参照は、その章の冒頭（N.0）への参照として数える。"""
    by = defaultdict(set)
    ids = {s["id"] for s in secs}
    for s in secs:
        t = s["text"]
        for m in REF_SEC.finditer(t):
            k = f"{m.group(1)}.{m.group(2)}"
            if k in ids and k != s["id"]:
                by[k].add(s["id"])
        for m in REF_EQ.finditer(t):
            # 式 (N.M) は第 N 章のどの節かを本文から探す
            tag = f"$${'['}{m.group(1)}.{m.group(2)}]"
            for s2 in secs:
                if tag in s2["text"] and s2["id"] != s["id"]:
                    by[s2["id"]].add(s["id"])
        for m in REF_CH.finditer(t):
            k = f"{m.group(1)}.0"
            if k in ids and int(m.group(1)) != s["chapter"]:
                by[k].add(s["id"])
    return by


COMMON = {"合計", "毎年", "係数", "期間", "範囲", "考え方", "いつ", "すべての", "前提", "厳密", "近似", "成り立たない",
          "証明", "反例", "不採用", "表現には使わない", "傾き", "跳び", "比例"}


def first_use(secs: list[dict]) -> list[dict]:
    """**用語** の太字（定義の目印）より前の章で、その用語が参照の印（第 N 章・N.M 節）なしに使われているか。
    同じ章の前の節（動機の説明）、第 0 章（原理の一覧）、日常語に近い語（COMMON）は除く。"""
    order = {s["id"]: i for i, s in enumerate(secs)}
    defined = {}
    for s in secs:
        for m in re.finditer(r"\*\*([^*$]{2,14}?)\*\*", s["text"]):
            term = m.group(1).strip("：:。、 ")
            if re.search(r"[0-9]|原理|注意|例題|研究では|用語|この章", term) or len(term) < 2 or term in COMMON:
                continue
            defined.setdefault(term, s)
    issues = []
    for term, ds in defined.items():
        used = []
        for s in secs:
            if order[s["id"]] >= order[ds["id"]] or s["chapter"] in (0, ds["chapter"]):
                continue
            for sent in re.split(r"(?<=[。．])|\n", s["text"]):
                if norm(term) in norm(sent) and not re.search(r"第\s*\d+\s*章|\d+\.\d+\s*節", sent):
                    used.append(s["id"])
                    break
        if used:
            issues.append({"term": term, "defined_in": ds["id"], "used_before_in": used})
    return issues


def main() -> int:
    secs = sections()
    probs = json.loads((ROOT / "problems" / "problems.json").read_text(encoding="utf-8"))["problems"]
    refs = references(secs)
    support = []
    for s in secs:
        ps = [p for p in probs if s["id"] in p["sections"]]
        kinds = sorted({p["kind"] for p in ps}, key=KINDS.index)
        support.append({"id": s["id"], "title": s["title"], "problems": [p["id"] for p in ps], "n_problems": len(ps),
                        "n_kinds": len(kinds), "kinds": kinds, "levels": sorted({p["level"] for p in ps}),
                        "referenced_by": sorted(refs.get(s["id"], set())), "n_referenced": len(refs.get(s["id"], set())),
                        "chars": len(s["text"])})
    fu = first_use(secs)
    out = ROOT / "audit"
    out.mkdir(exist_ok=True)
    (out / "coverage.json").write_text(json.dumps({"sections": support, "first_use": fu}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    # 監査表に入れる表
    rows = ["| 節 | 題 | 支える問題（種類数／問題数） | 後の節からの参照 | 問題 |", "|---|---|---|---|---|"]
    for r in support:
        if r["id"].endswith(".S") or r["id"].endswith(".0") and r["n_problems"] == 0 and r["n_referenced"] == 0:
            continue
        if r["id"].endswith(".1") and r["title"].startswith("何を求めたい"):
            continue
        rows.append(f"| {r['id']} | {r['title']} | {r['n_kinds']}／{r['n_problems']} | {r['n_referenced']} | "
                    f"{'、'.join(r['problems']) or '—'} |")
    zero = [r for r in support if r["n_problems"] == 0 and not r["id"].endswith((".S", ".0", ".1"))
            and not r["title"].startswith(("初めて見る", "よくある誤解"))]
    (out / "_coverage_tables.md").write_text("\n".join(rows), encoding="utf-8")
    print(f"節 {len(secs)}、問題が 1 問も使わない節 {len(zero)}：{'、'.join(r['id'] for r in zero)}")
    print(f"用語の初出の前の使用 {len(fu)} 件")
    for x in fu[:40]:
        print(f"  {x['term']}：定義 {x['defined_in']}、先に使用 {x['used_before_in'][:4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
