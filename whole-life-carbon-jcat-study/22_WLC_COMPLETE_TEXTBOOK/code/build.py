"""教材の組み立て（structlab.exam.pipeline の render_subject の流れを引き継ぐ：内容の指紋が同じなら作り直さない、
出力ごとに品質検査を行い、検査結果を保存する）。

  python3 -B build.py [成果物の名前 …]      名前を省くと全部
成果物：①教材（textbook/ch*.md）、②原理シート、③導出のつながり、④問題と解答、⑤研究の全工程の記録、⑥監査表。
出力：../output/<番号>_<名前>.pdf と .docx、../output/品質検査.json、目で確かめる用のページ画像 ../output/_renders/。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mdparse  # noqa: E402
import render  # noqa: E402
from mathrender import render_all  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "output"
CACHE = HERE / "_cache"
HEADER = "ホールライフカーボン完全理解教材"

DOCS = {
    "1": {"name": "ホールライフカーボン完全理解教材", "files": ["textbook/ch00.md", "textbook/ch01.md", "textbook/ch02.md", "textbook/ch03.md",
                                                   "textbook/ch04.md", "textbook/ch05.md", "textbook/ch06.md", "textbook/ch07.md",
                                                   "textbook/ch08.md", "textbook/ch09.md", "textbook/ch10_appendix.md"],
          "title": "ホールライフカーボン完全理解教材", "subtitle": "建築 LCA の基礎から、研究の数学的成果（全体方程式・時間特性・動的 LCA・検証）まで",
          "toc": True, "expect": ["五つの基本原理", "量 × 係数 の和", "建物全体の方程式", "再構成"]},
    "2": {"name": "重要原理シート", "files": ["sheets/principles.md"], "title": "ホールライフカーボン　重要原理シート",
          "subtitle": "教材を読み終えた人の見直し用", "toc": False, "expect": ["P1"]},
    "3": {"name": "数式の導出とつながり", "files": ["sheets/derivations.md"], "title": "数式の導出とつながり",
          "subtitle": "数量×係数から建物全体方程式・動的 LCA・変換まで", "toc": False, "expect": []},
    "4": {"name": "理解確認問題と解答", "files": ["problems/problems.md", "problems/solutions.md"], "title": "理解確認問題・応用問題と詳しい解答",
          "subtitle": "初級・中級・上級。計算問題は厳密な算術で検算済み", "toc": True, "expect": []},
    "5": {"name": "研究の全工程と発見の記録", "files": ["record/research_record.md"], "title": "研究の全工程・発見・検証の記録",
          "subtitle": "第 1 章から第 21 章まで", "toc": True, "expect": []},
    "6": {"name": "学習範囲と問題対応の監査表", "files": ["audit/audit.md"], "title": "学習範囲と問題対応の監査表",
          "subtitle": "研究の論点ごとの、教材の説明・演習問題・元資料の対応", "toc": False, "expect": []},
}


def blocks_of(spec: dict) -> list[dict]:
    blocks = [{"t": "title", "text": spec["title"]}, {"t": "subtitle", "text": spec["subtitle"]},
              {"t": "subtitle", "text": f"作成：{time.strftime('%Y-%m-%d')}　／　対象：独立概念モデル（70 評価単位・架空データ）と一般的な WLC の知識"}]
    for i, f in enumerate(spec["files"]):
        p = ROOT / f
        bs = mdparse.parse(p.read_text(encoding="utf-8"), base=p.parent)
        if i == 0 and spec["toc"] and not any(b["t"] == "toc" for b in bs):
            blocks.append({"t": "toc"})
        blocks += bs
    if not spec["toc"]:
        blocks = [b for b in blocks if b["t"] != "toc"]
        for b in blocks:
            if b["t"] == "h1":
                b["nobreak"] = True
    return blocks


def build(key: str, force: bool = False) -> dict:
    spec = DOCS[key]
    blocks = blocks_of(spec)
    figs = [b["path"] for b in blocks if b["t"] == "img"]
    missing = [f for f in figs if not Path(f).exists()]
    if missing:
        raise FileNotFoundError(f"図が無い: {missing}")
    fp_src = json.dumps(blocks, ensure_ascii=False, sort_keys=True) + "".join(
        hashlib.sha1(Path(f).read_bytes()).hexdigest() for f in figs) + (HERE / "render.py").read_text() + (HERE / "tex2mml.py").read_text()
    fp = hashlib.sha256(fp_src.encode()).hexdigest()
    stem = f"{key}_{spec['name']}"
    pdf, docx = OUT / f"{stem}.pdf", OUT / f"{stem}.docx"
    fp_path = CACHE / f"{stem}.fp"
    if not force and fp_path.exists() and fp_path.read_text() == fp and pdf.exists() and docx.exists():
        return {"name": stem, "skipped": True}
    mp = render_all(mdparse.math_of(blocks), CACHE / "math")
    render.to_pdf(blocks, pdf, title=spec["title"], header=HEADER if key == "1" else spec["title"], math_png=mp)
    render.to_docx(blocks, docx, title=spec["title"], math_png=mp)
    n_img = len(mdparse.math_of(blocks)) + len(figs)
    chk_pdf = render.check_pdf(pdf, spec["expect"], render_dir=OUT / "_renders", render_pages=[1, 2, 3],
                               header=HEADER if key == "1" else spec["title"])
    chk_docx = render.check_docx(docx, spec["expect"], n_images=n_img)
    fp_path.parent.mkdir(parents=True, exist_ok=True)
    fp_path.write_text(fp)
    return {"name": stem, "skipped": False, "pdf": chk_pdf, "docx": chk_docx, "math": len(mdparse.math_of(blocks)),
            "figures": len(figs), "chars": sum(len(str(b.get("text", ""))) + sum(len(x) for x in b.get("items", [])) +
                                               sum(len(str(c)) for r in b.get("rows", []) for c in r) for b in blocks)}


def main(keys: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rp = OUT / "品質検査.json"
    report = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    bad = 0
    for k in keys or list(DOCS):
        if not all((ROOT / f).exists() for f in DOCS[k]["files"]):
            print(f"{k}: 原稿が未作成のため飛ばす")
            continue
        r = build(k, force="--force" in sys.argv)
        if not r.get("skipped"):
            report[r["name"]] = r
            ok = r["pdf"]["ok"] and r["docx"]["ok"]
            bad += not ok
            print(f"{r['name']}: PDF {r['pdf']['pages']} ページ、式 {r['math']}、図 {r['figures']}、文字 {r['chars']:,} "
                  f"→ {'OK' if ok else '問題: ' + '; '.join(r['pdf']['problems'] + r['docx']['problems'])}")
        else:
            print(f"{r['name']}: 変更なし")
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main([a for a in sys.argv[1:] if not a.startswith("--")]))
