"""クラウド解析ジョブの実行（GitHub Actions の cloud-jobs.yml から呼ばれる。手元でも実行可）

  python cloud/run_job.py --id <job-id>          # cloud_jobs/inbox/<id>/ を処理し cloud_jobs/outbox/<id>/ に結果
  python cloud/run_job.py --branch aqros-job/<id>

ジョブ種別: sweep（パラメータ計算）/ analysis（データ詳細解析）/ report（Word・PDF 生成）/ ocr（文字起こし）

ログ（CI に残る）には件数・所要時間・ファイル名だけを出し、データの中身・文書の本文は出さない。
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

MAX_SWEEP = 20000
MAX_INPUT_BYTES = 200 * 1024 * 1024


def log(msg: str) -> None:
    print(f"[aqros-job] {msg}", flush=True)


def clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if hasattr(v, "item"):
        return clean(v.item())
    return v


# ----------------------------------------------------------------------------- sweep
def job_sweep(job: dict, inp: Path, out: Path) -> dict:
    import csv

    from aqros import models as M

    p = job.get("params") or {}
    kind = p.get("kind", "bypass")
    rows: list[dict] = []
    if kind == "bypass":
        n_units = [int(x) for x in p.get("n_units", [5, 10, 15, 20])]
        settings = [s for s in p.get("settings", ["中"]) if s in M.FAN_SETTINGS]
        bins = [b for b in p.get("size_bins", ["0.3-0.5"]) if b in M.EP_EFFICIENCY_ENDPOINTS]
        laws = [l for l in p.get("ep_laws", list(M.EP_LAWS)) if l in M.EP_LAWS]
        steps = max(2, min(int(p.get("steps", 21)), 101))
        n = len(n_units) * len(settings) * len(bins) * len(laws) * steps
        if n > MAX_SWEEP or not n:
            raise ValueError(f"組合せ数 {n} は上限 {MAX_SWEEP} を超えるか 0 です")
        for nu, st, b, law in itertools.product(n_units, settings, bins, laws):
            for r in M.bypass_sweep(nu, st, steps=steps, size_bin=b, ep_law=law):
                rows.append({"n_units": nu, "setting": st, "size_bin": b, "ep_law": law, **{k: clean(v) for k, v in asdict(r).items()}})
        best = {}
        for r in rows:
            k = f"{r['n_units']}台/{r['setting']}/{r['size_bin']}/{r['ep_law']}"
            if r.get("cadr") is not None and (k not in best or r["cadr"] > best[k]["cadr"]):
                best[k] = {"cadr": r["cadr"], "opening_ratio": r.get("opening_ratio")}
        summary = {"kind": kind, "cases": len(rows), "best_cadr_by_combination": best}
    elif kind == "zone":
        base = M.ZoneParams()
        grid = {k: [float(x) for x in v] for k, v in (p.get("grid") or {"q_recirc": [0, 300, 600, 950], "eta_ep": [0.6, 0.85, 0.95], "bypass_ratio": [0, 0.2, 0.4]}).items() if hasattr(base, k)}
        keys = list(grid)
        n = math.prod(len(v) for v in grid.values()) if grid else 0
        if n > MAX_SWEEP or not n:
            raise ValueError(f"組合せ数 {n} は上限 {MAX_SWEEP} を超えるか 0 です")
        fixed = {k: float(v) for k, v in (p.get("fixed") or {}).items() if hasattr(base, k)}
        for combo in itertools.product(*grid.values()):
            zp = M.ZoneParams(**{**asdict(base), **fixed, **dict(zip(keys, combo))})
            rows.append({**dict(zip(keys, combo)), "steady_state": clean(M.zone_steady_state(zp)), "io_ratio": clean(M.zone_io_ratio(zp)),
                         "cadr": clean(M.zone_cadr(zp)), "loss_rate": clean(M.zone_loss_rate(zp)), "t12_h": clean(M.time_to_fraction(zp, 0.12))})
        summary = {"kind": kind, "cases": len(rows), "grid": grid, "fixed": fixed,
                   "min_io_ratio": min((r["io_ratio"] for r in rows if r["io_ratio"] is not None), default=None)}
    else:
        raise ValueError(f"未知の sweep 種別: {kind}")
    with open(out / "sweep.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log(f"sweep {kind}: {len(rows)} cases")
    return {"summary": summary, "note": "Python 版モデル（backend/aqros/models.py）による計算結果。研究室の実測値ではない。"}


# ----------------------------------------------------------------------------- analysis
def job_analysis(job: dict, inp: Path, out: Path) -> dict:
    import numpy as np
    import pandas as pd

    from aqros import analysis as A

    p = job.get("params") or {}
    files = sorted((inp / "inputs").glob("*")) if (inp / "inputs").exists() else []
    if not files:
        raise ValueError("入力ファイルがありません")
    per: list[dict] = []
    frames: dict[str, pd.DataFrame] = {}
    for f in files:
        if f.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError(f"{f.name}: 200MB を超えています")
        sheets = A.read_table(f.read_bytes(), f.name)
        for sheet, df in sheets.items():
            if df.empty:
                continue
            label = f.name if len(sheets) == 1 else f"{f.name} [{sheet}]"
            tcol = A.detect_time_column(df)
            cols = A.numeric_columns(df, exclude=tcol)
            desc = df[cols].describe().T if cols else pd.DataFrame()
            entry = {"dataset": label, "rows": int(len(df)), "time_column": tcol, "numeric_columns": cols,
                     "quality": A.quality_report(df, cols),
                     "stats": {c: {k: clean(v) for k, v in desc.loc[c].items()} for c in cols}}
            ind, outd = p.get("indoor"), p.get("outdoor")
            if ind in df.columns and outd in df.columns:
                entry["io_ratio"] = {k: clean(v) for k, v in A.io_ratio(pd.to_numeric(df[ind], errors="coerce").to_numpy(float),
                                                                           pd.to_numeric(df[outd], errors="coerce").to_numpy(float)).items()}
            dc = p.get("decay_column")
            if dc in df.columns and tcol:
                t = pd.to_datetime(df[tcol], errors="coerce")
                ts = (t - t.min()).dt.total_seconds().to_numpy(float)
                try:
                    entry["decay"] = {k: clean(v) for k, v in A.fit_decay(ts, pd.to_numeric(df[dc], errors="coerce").to_numpy(float)).items()}
                except ValueError as e:
                    entry["decay"] = {"error": str(e)}
            per.append(entry)
            frames[label] = desc
    # 複数データの統合表（共通列の平均・中央値を並べる）
    common = sorted(set.intersection(*[set(e["numeric_columns"]) for e in per])) if per else []
    combined = [{"dataset": e["dataset"], "rows": e["rows"], **{f"{c}_mean": e["stats"][c].get("mean") for c in common},
                 **{f"{c}_50%": e["stats"][c].get("50%") for c in common}} for e in per]
    with pd.ExcelWriter(out / "analysis.xlsx", engine="openpyxl") as xw:
        pd.DataFrame(combined).to_excel(xw, sheet_name="統合", index=False)
        for i, (label, desc) in enumerate(frames.items()):
            desc.to_excel(xw, sheet_name=re.sub(r"[\[\]:*?/\\]", "_", f"{i + 1}_{label}")[:31])
    md = ["# クラウド解析結果（Python / pandas）", "", f"- データ数: {len(per)}", f"- 共通の数値列: {', '.join(common) or 'なし'}", ""]
    for e in per:
        md += [f"## {e['dataset']}", f"- 行数 {e['rows']}、時刻列 {e['time_column'] or 'なし'}、数値列 {len(e['numeric_columns'])}"]
        if "io_ratio" in e:
            md.append(f"- I/O比: {json.dumps(e['io_ratio'], ensure_ascii=False)}")
        if "decay" in e:
            md.append(f"- 減衰: {json.dumps(e['decay'], ensure_ascii=False)}")
        md.append("")
    (out / "analysis.md").write_text("\n".join(md), encoding="utf-8")
    log(f"analysis: {len(files)} files, {len(per)} sheets")
    _ = np  # numpy は pandas 経由で使用
    return {"summary": {"datasets": len(per), "common_numeric_columns": common, "per_dataset": per, "combined": combined}}


# ----------------------------------------------------------------------------- report
def job_report(job: dict, inp: Path, out: Path) -> dict:
    sections = None
    sec_file = inp / "inputs" / "report_sections.json"
    if sec_file.exists():
        sections = json.loads(sec_file.read_text(encoding="utf-8"))
    if not sections:
        sections = [{"title": f.stem, "body": f.read_text(encoding="utf-8")} for f in sorted((ROOT / "report").glob("*.md"))]
        source = "リポジトリの公開版報告書（report/*.md）"
    else:
        source = "スマホで編集した報告書"
    title = (job.get("params") or {}).get("title") or "Air Quality Research OS 総合研究報告書"
    from privacy_patterns import anonymize
    md = f"---\ntitle: \"{title}\"\nlang: ja-JP\n---\n\n" + anonymize("\n\n".join(s["body"] for s in sections))
    work = Path(tempfile.mkdtemp(prefix="aqros-report-"))
    (work / "report.md").write_text(md, encoding="utf-8")
    docx = out / "report.docx"
    cmd = ["pandoc", str(work / "report.md"), "-o", str(docx), "--toc", "--toc-depth=2", "--resource-path", str(ROOT / "report")]
    ref = ROOT / "cloud" / "reference.docx"
    if ref.exists():
        cmd += ["--reference-doc", str(ref)]
    subprocess.run(cmd, check=True, cwd=work)
    pdf_ok = False
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(out), str(docx)], check=True, capture_output=True, timeout=600)
        pdf_ok = (out / "report.pdf").exists()
    shutil.rmtree(work, ignore_errors=True)
    log(f"report: {len(sections)} sections, pdf={pdf_ok}")
    return {"summary": {"sections": len(sections), "source": source, "docx": True, "pdf": pdf_ok}}


# ----------------------------------------------------------------------------- ocr
def job_ocr(job: dict, inp: Path, out: Path) -> dict:
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract が見つかりません（ワークフローで tesseract-ocr-jpn を入れる）")
    files = sorted((inp / "inputs").glob("*"))
    if not files:
        raise ValueError("入力ファイルがありません")
    lang = (job.get("params") or {}).get("lang", "jpn+eng")
    if not re.fullmatch(r"[a-z_]+(\+[a-z_]+)*", lang):
        raise ValueError("lang が不正です")
    pages = 0
    texts = []
    for f in files:
        work = Path(tempfile.mkdtemp(prefix="aqros-ocr-"))
        if f.suffix.lower() == ".pdf":
            subprocess.run(["pdftoppm", "-r", "300", "-png", str(f), str(work / "p")], check=True, timeout=1800)
            imgs = sorted(work.glob("p*.png"))
        else:
            imgs = [f]
        for i, img in enumerate(imgs, 1):
            r = subprocess.run(["tesseract", str(img), "stdout", "-l", lang], capture_output=True, text=True, timeout=600)
            texts.append(f"===== {f.name} p.{i} =====\n{r.stdout}")
            pages += 1
        shutil.rmtree(work, ignore_errors=True)
    (out / "ocr.txt").write_text("\n".join(texts), encoding="utf-8")
    log(f"ocr: {len(files)} files, {pages} pages")
    return {"summary": {"files": len(files), "pages": pages, "lang": lang, "chars": sum(len(t) for t in texts)}}


def repo_is_private(job: dict) -> bool:
    """GitHub Actions 上では実際のリポジトリ設定（AQROS_REPO_PRIVATE）を使い、スマホの申告は信用しない。"""
    import os
    env = os.environ.get("AQROS_REPO_PRIVATE")
    if env is not None:
        return env.strip().lower() == "true"
    return bool(job.get("repo_private"))   # 手元実行（テスト）時のみ


JOBS = {"sweep": job_sweep, "analysis": job_analysis, "report": job_report, "ocr": job_ocr}


def run(job_id: str, root: Path = ROOT) -> dict:
    if not re.fullmatch(r"[0-9A-Za-z\-]{6,64}", job_id):
        raise SystemExit("不正なジョブ ID")
    inp = root / "cloud_jobs" / "inbox" / job_id
    out = root / "cloud_jobs" / "outbox" / job_id
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        job = json.loads((inp / "job.json").read_text(encoding="utf-8"))
        jt = job.get("type")
        if jt not in JOBS:
            raise ValueError(f"未知のジョブ種別: {jt}")
        declared = {i.get("name"): bool(i.get("sensitive", True)) for i in job.get("inputs") or []}
        files = [f.name for f in (inp / "inputs").iterdir()] if (inp / "inputs").exists() else []
        repo_private = repo_is_private(job)
        if any(declared.get(n, True) for n in files) and not repo_private:
            # スマホ側でも止めているが、公開リポジトリに研究データが来た場合はここでも処理しない
            raise PermissionError("公開リポジトリでは研究データを処理しません（入力は削除します）")
        if any(declared.get(n, True) for n in files) and not job.get("consent"):
            raise PermissionError("研究データの処理には利用者の同意（consent）が必要です")
        res = JOBS[jt](job, inp, out)
        result = {"status": "ok", "id": job_id, "type": jt, "elapsed_s": round(time.time() - t0, 1), **res,
                  "files": sorted(f.name for f in out.iterdir() if f.name != "result.json")}
    except Exception as e:  # noqa: BLE001
        log(f"error: {type(e).__name__}")
        result = {"status": "error", "id": job_id, "error": f"{type(e).__name__}: {e}", "elapsed_s": round(time.time() - t0, 1)}
        (out / "trace.txt").write_text(traceback.format_exc(), encoding="utf-8")
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    # 入力データは結果コミットで消す（ブランチ削除までは履歴に残る点に注意）
    if (inp / "inputs").exists():
        shutil.rmtree(inp / "inputs")
    log(f"done: {result['status']} in {result['elapsed_s']}s")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--branch")
    a = ap.parse_args()
    job_id = a.id or (a.branch or "").removeprefix("aqros-job/")
    r = run(job_id)
    return 0 if r["status"] == "ok" else 0  # 失敗も result.json で返す（ワークフローは結果のコミットまで進める）


if __name__ == "__main__":
    sys.exit(main())
