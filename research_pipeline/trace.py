"""追跡監査と3工程（資料収集→論文改訂→教材改訂）の連動。

- 指紋: 主張 = 台帳の行＋出典の主要列＋原文照合結果。論文段落 = 本文＋根拠主張の指紋。
  教材項目 = 本文＋由来する論文段落の指紋＋根拠主張の指紋。
- revisions/trace_lock.json に「最後に承認した指紋」を保存する。資料・主張・段落のどれかが
  変わると、下流の段落・教材項目が STALE（要改訂）になり、原因（どの主張・段落が変わったか）を示す。
- 教材は論文段落からの派生物: 教材が引く主張は、指定した論文段落の主張の部分集合でなければならない。
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from . import blocks as BL
from . import ledger as LG
from .common import digest, read_csv, read_json

LABELS = {
    "synthesis": "【本研究の整理（複数資料の統合。個々の資料の主張ではない）】",
    "derivation": "【本研究の読み取り（資料の数値・記述からの導出）】",
    "method": "【本研究の方法】",
    "proposal": "【本研究の提案・仮説（未実証）】",
    "limitation": "【限界・未確認事項】",
    "calc": "【本研究の計算（自動検算済み）】",
    "analogy": "【たとえ（教材上の説明。一次資料の主張ではありません）】",
    "tip": "【学習のコツ（本研究の教育的提案）】",
    "note": "【注記】",
}
PAPER_KINDS = {"evidence", "synthesis", "derivation", "method", "proposal", "limitation", "calc"}
EDU_KINDS = {"fact", "term", "step", "derivation", "synthesis", "objective", "analogy", "tip", "proposal",
             "limitation", "calc", "quiz", "note"}
NEEDS_CLAIMS = {"evidence", "synthesis", "derivation", "fact", "term", "quiz"}
NO_CLAIMS = {"analogy", "tip", "note", "method"}
UNIT_ID = re.compile(r"P\d+-U\d{3}")
SRC_KEYS = ("title", "author", "original_url", "canonical_url", "published_at", "access_status", "source_tier")
QUIZ_TYPES = {"choice", "tf", "calc", "short"}


# ---------- 安全な検算（eval を使わない） ----------
def number(s: str) -> Fraction:
    return Fraction(str(s).strip())


def safe_eval(expr: str) -> Fraction:
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            return Fraction(str(n.value))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
            if isinstance(n.op, ast.Pow) and b.denominator == 1 and abs(b) <= 64:
                return a ** int(b)
        raise ValueError(f"許可していない式: {ast.dump(n)[:60]}")
    return ev(ast.parse(expr, mode="eval"))


def check_calc(b: BL.Block, where: str, errors: list[str]) -> None:
    expr, expect = b.attrs.get("expr"), b.attrs.get("expect")
    if not expr or not expect:
        errors.append(f"{where}: 計算に expr と expect が必要")
        return
    try:
        got, want = safe_eval(expr), number(expect)
    except (ValueError, ZeroDivisionError, SyntaxError) as e:
        errors.append(f"{where}: 検算できない式 {expr!r}: {e}")
        return
    if got != want:
        errors.append(f"{where}: 検算不一致 {expr} = {got}（記載 {expect}）")


# ---------- 問題（理解度確認） ----------
def parse_quiz(b: BL.Block) -> dict:
    q = {"stem": [], "choices": [], "model": "", "explain": []}
    mode = "stem"
    for ln in b.text.splitlines():
        m = re.match(r"^([A-F])\)\s*(.+)$", ln.strip())
        if m and mode in ("stem", "choices"):
            q["choices"].append((m.group(1), m.group(2)))
            mode = "choices"
        elif ln.strip().startswith("解答例:"):
            q["model"], mode = ln.split(":", 1)[1].strip(), "model"
        elif ln.strip().startswith("解説:"):
            q["explain"].append(ln.split(":", 1)[1].strip())
            mode = "explain"
        elif mode == "explain":
            q["explain"].append(ln)
        elif mode == "model":
            q["model"] += "\n" + ln
        elif mode == "stem":
            q["stem"].append(ln)
    q["stem"] = "\n".join(q["stem"]).strip()
    q["explain"] = "\n".join(q["explain"]).strip()
    return q


QUIZ_STATUS = {"公開可", "要確認"}
QUIZ_DATA = {"原論文", "教材上の仮定値", "実データ再現", "観測値"}


def quiz_status(b: BL.Block) -> str:
    """第10部 10-5: 状態が無い・不正な問題は自動公開しない（要確認扱い）。"""
    return b.attrs.get("status") if b.attrs.get("status") in QUIZ_STATUS else "要確認"


def check_quiz(b: BL.Block, where: str, errors: list[str], warnings: list[str] | None = None) -> None:
    t, ans = b.attrs.get("type"), b.attrs.get("answer", "")
    if warnings is not None:
        if b.attrs.get("status") not in QUIZ_STATUS:
            warnings.append(f"{where}: 問題の状態 status=（公開可/要確認）が無い・不正。要確認として非公開")
        if b.attrs.get("data") not in QUIZ_DATA:
            warnings.append(f"{where}: 数値・内容の種類 data=（{'/'.join(sorted(QUIZ_DATA))}）が無い")
        if b.attrs.get("level") not in ("初級", "中級", "上級"):
            warnings.append(f"{where}: 難易度 level= が無い・不正")
    q = parse_quiz(b)
    if t not in QUIZ_TYPES:
        errors.append(f"{where}: type は {sorted(QUIZ_TYPES)} のいずれか")
        return
    if not q["stem"]:
        errors.append(f"{where}: 問題文が無い")
    if not q["explain"]:
        errors.append(f"{where}: 解説が無い")
    if not b.ids("lo"):
        errors.append(f"{where}: 学習目標 lo= が無い")
    if t == "choice":
        letters = [c[0] for c in q["choices"]]
        if len(letters) < 3 or ans not in letters or len(set(letters)) != len(letters):
            errors.append(f"{where}: 選択肢（3個以上・重複なし）と正答 answer= が不正")
    elif t == "tf" and ans not in ("○", "×"):
        errors.append(f"{where}: 正誤問題の answer は ○ か ×")
    elif t == "calc":
        check_calc(b, where, errors)
    elif t == "short" and not q["model"]:
        errors.append(f"{where}: 記述問題に「解答例:」が無い")


# ---------- 監査本体 ----------
@dataclass
class Item:
    key: str
    doc: BL.Doc
    block: BL.Block
    fp: str = ""
    parts: dict = field(default_factory=dict)
    status: str = "NEW"
    causes: list[str] = field(default_factory=list)


@dataclass
class Audit:
    root: Path
    led: LG.Ledgers
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    claim_fp: dict = field(default_factory=dict)
    verify: dict = field(default_factory=dict)
    papers: list = field(default_factory=list)
    edus: list = field(default_factory=list)
    units: dict = field(default_factory=dict)       # unit_id -> Item
    edu_items: dict = field(default_factory=dict)   # "doc#id" -> Item
    objectives: dict = field(default_factory=dict)  # LO -> Item
    paper_version: str = ""
    flashcards: int = 0

    def stale(self) -> list[Item]:
        return [it for it in [*self.units.values(), *self.edu_items.values()] if it.status != "OK"]


def load_verification(root: Path) -> dict:
    rows = read_csv(root / "audit" / "excerpt_verification.csv")
    return {r["claim_id"]: r for r in rows}


def claim_fingerprints(led: LG.Ledgers, verify: dict) -> dict:
    srcs = led.index("sources")
    out = {}
    for c in led.tables.get("claims", []):
        s = srcs.get(c["source_id"], {})
        v = verify.get(c["claim_id"])
        out[c["claim_id"]] = digest({
            "claim": c, "source": {k: s.get(k, "") for k in SRC_KEYS},
            "verify": {"found": v["found"], "section": v["detected_section"]} if v else None})
    return out


def _check_claims(a: Audit, where: str, b: BL.Block) -> None:
    claims = a.led.index("claims")
    srcs = a.led.index("sources")
    for cid in b.ids("claims"):
        c = claims.get(cid)
        if c is None:
            a.errors.append(f"{where}: 存在しない主張 {cid}")
            continue
        if c["verification_status"] not in LG.VERIFIED:
            a.warnings.append(f"{where}: 未照合の根拠 {cid}（{c['verification_status']}）")
        v = a.verify.get(cid)
        if c["verification_status"] == "verbatim_auto_verified" and (v is None or v["found"] != "true"):
            a.errors.append(f"{where}: {cid} は台帳上「自動照合済み」だが照合結果が無い/不一致")
        if srcs.get(c["source_id"], {}).get("source_tier") == "H1":
            a.warnings.append(f"{where}: {cid} は二次情報（H1）。中心証拠にしない")
    if b.attrs.get("assertion") == "effect":
        ok = any(claims.get(cid, {}).get("claim_type") == "実験" and
                 srcs.get(claims[cid]["source_id"], {}).get("source_tier") == "V1"
                 for cid in b.ids("claims") if cid in claims)
        if not ok:
            a.errors.append(f"{where}: 効果の主張には独立実証（V1・実験）の根拠が必要")


def audit(root: Path) -> Audit:
    led = LG.load(root)
    a = Audit(root, led, errors=list(led.errors), warnings=list(led.warnings))
    a.verify = load_verification(root)
    a.claim_fp = claim_fingerprints(led, a.verify)
    lock = read_json(root / "revisions" / "trace_lock.json", {"paper": {}, "education": {}})

    # 論文
    for path in sorted((root / "papers").rglob("*.src.md")):
        d = BL.parse(path)
        a.papers.append(d)
        a.errors += d.errors
        for b in d.blocks:
            where = f"{path.relative_to(root)}:{b.line}"
            if b.kind not in PAPER_KINDS:
                a.errors.append(f"{where}: 論文で使えない種類 {b.kind}")
                continue
            if not UNIT_ID.fullmatch(b.id):
                a.errors.append(f"{where}: 段落ID（例 P8-U001）が無い/不正 {b.id!r}")
                continue
            if b.id in a.units:
                a.errors.append(f"{where}: 段落ID重複 {b.id}")
            if b.kind in NEEDS_CLAIMS and not b.ids("claims"):
                a.errors.append(f"{where}: 根拠 claims= が無い")
            if b.kind == "synthesis" and len(b.ids("claims")) < 2:
                a.errors.append(f"{where}: 統合（synthesis）は2件以上の主張が必要")
            if b.kind in NO_CLAIMS and b.ids("claims"):
                a.errors.append(f"{where}: {b.kind} に根拠を付けない（主張と混同させない）")
            if b.kind == "calc":
                check_calc(b, where, a.errors)
            _check_claims(a, where, b)
            parts = {"text": digest({"k": b.kind, "t": b.text, "a": {k: v for k, v in b.attrs.items() if k != "id"}}),
                     "claims": {c: a.claim_fp.get(c, "missing") for c in b.ids("claims")}}
            a.units[b.id] = Item(b.id, d, b, digest(parts), parts)

    # 教材
    for path in sorted((root / "education").rglob("*.src.md")):
        d = BL.parse(path)
        a.edus.append(d)
        a.errors += d.errors
        for b in d.blocks:
            where = f"{path.relative_to(root)}:{b.line}"
            if b.kind not in EDU_KINDS:
                a.errors.append(f"{where}: 教材で使えない種類 {b.kind}")
                continue
            if not b.id:
                a.errors.append(f"{where}: id= が無い")
                continue
            key = f"{path.stem.replace('.src', '')}#{b.id}"
            if key in a.edu_items:
                a.errors.append(f"{where}: ID重複 {b.id}")
            units = b.ids("units")
            unknown = [u for u in units if u not in a.units]
            if unknown:
                a.errors.append(f"{where}: 存在しない論文段落 {unknown}")
            needs_units = b.kind in NEEDS_CLAIMS | {"objective", "derivation"} or (
                b.kind == "step" and b.attrs.get("basis") != "proposal")
            if needs_units and not units:
                a.errors.append(f"{where}: 由来する論文段落 units= が無い（教材は論文からの派生）")
            if (b.kind in NEEDS_CLAIMS or (b.kind == "step" and b.attrs.get("basis") != "proposal")) \
                    and not b.ids("claims"):
                a.errors.append(f"{where}: 根拠 claims= が無い")
            if b.kind in NO_CLAIMS and b.ids("claims"):
                a.errors.append(f"{where}: {b.kind} に根拠を付けない（たとえ・コツを主張と混同させない）")
            allowed = {c for u in units if u in a.units for c in a.units[u].block.ids("claims")}
            extra = [c for c in b.ids("claims") if c not in allowed]
            if extra and units:
                a.errors.append(f"{where}: 論文段落 {units} に無い主張 {extra} を教材が使っている")
            if b.kind == "calc":
                check_calc(b, where, a.errors)
            if b.kind == "quiz":
                check_quiz(b, where, a.errors, a.warnings)
            if b.kind == "objective":
                if not re.fullmatch(r"LO-\d{2}", b.id):
                    a.errors.append(f"{where}: 学習目標IDは LO-01 形式")
                a.objectives[b.id] = None
            _check_claims(a, where, b)
            parts = {"text": digest({"k": b.kind, "t": b.text, "a": {k: v for k, v in b.attrs.items() if k != "id"}}),
                     "units": {u: a.units[u].fp for u in units if u in a.units},
                     "claims": {c: a.claim_fp.get(c, "missing") for c in b.ids("claims")}}
            it = Item(key, d, b, digest(parts), parts)
            a.edu_items[key] = it
            if b.kind == "objective":
                a.objectives[b.id] = it

    paper_versions = {d.meta.get("version", "") for d in a.papers}
    a.paper_version = sorted(paper_versions)[-1] if paper_versions else ""
    for d in a.edus:
        pv = d.meta.get("paper_version", "")
        if not pv:
            a.warnings.append(f"{d.path.relative_to(root)}: paper_version（準拠する論文の版）が無い")
        elif pv not in paper_versions:
            a.warnings.append(f"{d.path.relative_to(root)}: 論文旧版準拠（教材 {pv} / 論文 {a.paper_version}）。"
                              "整合するまで検証済み最新版と呼ばない")
    for fc in sorted((root / "education").rglob("flashcards*.csv")):
        for i, r in enumerate(read_csv(fc), start=2):
            us = LG.split_ids(r.get("unit_ids", ""))
            cs = LG.split_ids(r.get("claim_ids", ""))
            where = f"{fc.relative_to(root)}:{i}"
            if not us or not cs or not r.get("front") or not r.get("back"):
                a.errors.append(f"{where}: front/back/unit_ids/claim_ids のいずれかが空")
                continue
            bad_u = [u for u in us if u not in a.units]
            allowed = {c for u in us if u in a.units for c in a.units[u].block.ids("claims")}
            bad_c = [c for c in cs if c not in allowed]
            if bad_u or bad_c:
                a.errors.append(f"{where}: 存在しない段落 {bad_u} / 段落に無い主張 {bad_c}")
            a.flashcards += 1
    quizzes = [it for it in a.edu_items.values() if it.block.kind == "quiz"]
    for it in quizzes:
        for lo in it.block.ids("lo"):
            if lo not in a.objectives:
                a.errors.append(f"{it.key}: 未定義の学習目標 {lo}")
    if a.edus:
        for lo in a.objectives:
            if not any(lo in it.block.ids("lo") for it in quizzes):
                a.errors.append(f"学習目標 {lo} を確かめる問題が無い")

    _compare_lock(a, lock)
    return a


def _compare_lock(a: Audit, lock: dict) -> None:
    for scope, items in (("paper", a.units), ("education", a.edu_items)):
        for key, it in items.items():
            old = lock.get(scope, {}).get(key)
            if old is None:
                it.status, it.causes = "NEW", ["未承認（新規）"]
                continue
            if old["fp"] == it.fp:
                it.status = "OK"
                continue
            it.status = "STALE"
            op = old.get("parts", {})
            if op.get("text") != it.parts["text"]:
                it.causes.append("本文・属性が変更された（再承認が必要）")
            for group, label in (("units", "論文段落"), ("claims", "根拠主張")):
                o, n = op.get(group, {}), it.parts.get(group, {})
                for k in sorted(set(o) | set(n)):
                    if k not in n:
                        it.causes.append(f"{label} {k} が外された")
                    elif k not in o:
                        it.causes.append(f"{label} {k} が追加された")
                    elif o[k] != n[k]:
                        it.causes.append(f"{label} {k} が変更された（上流の改訂）")


def approve(a: Audit, lock: dict, scope: str, keys: list[str], reason: str, when: str) -> list[str]:
    items = a.units if scope == "paper" else a.edu_items
    done = []
    for k in keys:
        it = items[k]
        lock.setdefault(scope, {})[k] = {"fp": it.fp, "parts": it.parts, "approved_at": when, "reason": reason}
        done.append(k)
    return done
