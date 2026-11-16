"""研究台帳（CSV）の定義と検証。指示書 第6部の最低限の列＋追跡用の列。

ID 規則: SRC-000001 / CLAIM-000001 / PERSON-000001 / MODEL-000001 / EXP-000001 など（6桁固定）。
未知の列・欠けた列・重複ID・存在しないIDへの参照は「エラー」として扱い、先へ進めない。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .common import read_csv

SCHEMAS: dict[str, tuple[str, list[str], str, str]] = {
    "sources": ("sources/sources.csv", [
        "source_id", "title", "author", "person_id", "affiliation_at_time", "role_in_development",
        "source_tier", "medium", "original_language", "original_url", "canonical_url", "published_at",
        "observed_at", "access_status", "copyright_status", "exact_location", "transcript_type",
        "checksum_if_downloaded", "tags", "notes"], "source_id", r"SRC-\d{6}"),
    "claims": ("claims/claims.csv", [
        "claim_id", "source_id", "person_id", "original_position", "original_language_excerpt_short",
        "translation_ja", "statement_summary", "claim_type", "firsthand_or_hearsay", "conditions",
        "model_version", "task", "evidence_level", "contradictions", "verification_status", "chapter"],
        "claim_id", r"CLAIM-\d{6}"),
    "people": ("people/people.csv", [
        "person_id", "name_as_shown", "aliases", "affiliation_at_time", "role_in_development",
        "person_tier", "involvement_verified", "evidence_source_ids", "notes"], "person_id", r"PERSON-\d{6}"),
    "organizations": ("organizations/organizations.csv", [
        "org_id", "name", "kind", "adoption_reason", "conflict_of_interest_notes", "evidence_source_ids"],
        "org_id", r"ORG-\d{6}"),
    "products": ("catalog/products.csv", [
        "product_id", "organization", "product_name", "access_channel", "verification_status",
        "evidence_source_ids", "notes"], "product_id", r"PRODUCT-\d{6}"),
    "models": ("catalog/models.csv", [
        "model_id", "organization", "product", "family", "public_model_name", "official_model_id",
        "version", "release_date", "retired_date", "access_channel", "pricing_asof", "context_length",
        "modalities", "tools", "effort_options", "region_plan_limits", "evidence_source_ids",
        "verification_status"], "model_id", r"MODEL-\d{6}"),
    "experiments": ("data/experiments.csv", [
        "experiment_id", "task", "sample", "comparison_group", "human_participation", "model_id",
        "exact_settings", "tools", "date", "trials", "metric", "raw_result", "baseline", "variance",
        "confidence_interval", "costs", "limitations", "source_id", "claim_ids"],
        "experiment_id", r"EXP-\d{6}"),
    "forecasts": ("data/forecasts.csv", [
        "forecast_id", "speaker", "statement_date", "forecast_horizon", "prediction", "assumptions",
        "measurement_rule", "resolved_status", "actual_result", "source_id", "claim_ids"],
        "forecast_id", r"FC-\d{6}"),
    "contradictions": ("claims/contradictions.csv", [
        "contradiction_id", "claim_ids", "category", "description", "resolution_status"],
        "contradiction_id", r"CON-\d{6}"),
    "search_log": ("sources/search_log.csv", [
        "query_id", "searched_at", "channel", "query", "result_count", "adopted", "reason"],
        "query_id", r"Q-\d{6}"),
    # --- 是正命令（2026-11-16）P-1・P-3 で追加した台帳 ---
    "source_access": ("sources/source_access.csv", [
        "source_id", "source_namespace", "reach", "read_scope", "reader", "read_at", "http_status",
        "final_url", "robots_check", "snapshot_sha256", "identity_axis", "involvement_axis",
        "text_verification_axis", "independence_axis", "commentary_path", "notes"],
        "source_id", r"SRC-\d{6}"),
    "role_evidence": ("people/role_evidence.csv", [
        "role_evidence_id", "person_id", "source_id", "evidence_kind", "excerpt", "location",
        "verification_status", "identity_status", "involvement", "determined_tier", "notes"],
        "role_evidence_id", r"ROLE-\d{6}"),
    "validations": ("claims/validations.csv", [
        "validation_id", "claim_id", "speaker_person_ids", "statement_mode", "identity_basis",
        "role_level", "firsthand", "cross_check_claim_ids", "relation", "notes"],
        "validation_id", r"VAL-\d{6}"),
    "candidates": ("sources/candidates.csv", [
        "candidate_id", "url", "title", "person_names", "organization", "found_via", "status", "reach",
        "reason", "observed_at"], "candidate_id", r"CAND-\d{6}"),
    "crosswalk": ("sources/id_crosswalk.csv", [
        "crosswalk_id", "namespace_a", "id_a", "namespace_b", "id_b", "match_basis", "notes"],
        "crosswalk_id", r"XW-\d{6}"),
}

CLAIM_TYPES = {"経験", "主張", "実験", "広報", "推測"}
FIRSTHAND = {"一次", "伝聞", "不明"}
VERIFIED = {"verbatim_auto_verified", "manual_verified"}
VERIFICATION = VERIFIED | {"paraphrase_only", "unverified", "failed"}
TIERS = {"S1", "S2", "S3", "S4", "S5", "V1", "H1"}
PERSON_TIERS = TIERS | {"CANDIDATE_UNVERIFIED"}
STATEMENT_MODES = {"断定", "推測", "予測", "宣伝", "測定"}
REACH = {"全文", "公開部分のみ", "要旨のみ", "説明欄のみ", "取得不可"}
IDENTITY = {"CONFIRMED", "CANDIDATE_UNVERIFIED"}
RELATIONS = {"一致", "対立", "条件付き一致", "比較不可", "未確認"}
CANDIDATE_STATUS = {"CANDIDATE_UNVERIFIED", "取得不可", "未着手", "採用済み", "不採用"}
MAX_EXCERPT_WORDS, MAX_EXCERPT_CHARS = 30, 220  # 著作権: 短い引用のみ


def split_ids(value: str) -> list[str]:
    return [v.strip() for v in re.split(r"[;,]", value or "") if v.strip()]


@dataclass
class Ledgers:
    root: Path
    tables: dict[str, list[dict]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def index(self, name: str) -> dict[str, dict]:
        key = SCHEMAS[name][2]
        return {r[key]: r for r in self.tables.get(name, [])}


def load(root: Path) -> Ledgers:
    led = Ledgers(root)
    for name, (rel, cols, key, pattern) in SCHEMAS.items():
        path = root / rel
        if not path.exists():
            led.warnings.append(f"{rel}: 未作成")
            led.tables[name] = []
            continue
        with path.open(encoding="utf-8") as fh:
            header = fh.readline().rstrip("\r\n").split(",")
        if header != cols:
            led.errors.append(f"{rel}: 列が定義と一致しない（期待 {cols}）")
        rows = read_csv(path)
        led.tables[name] = rows
        seen = set()
        for i, r in enumerate(rows, start=2):
            rid = r.get(key, "")
            if not re.fullmatch(pattern, rid or ""):
                led.errors.append(f"{rel}:{i}: ID形式が不正 {rid!r}")
            if rid in seen:
                led.errors.append(f"{rel}:{i}: ID重複 {rid}")
            seen.add(rid)
    _cross_check(led)
    return led


def _refs(led: Ledgers, table: str, column: str, target: str) -> None:
    known = set(led.index(target))
    key = SCHEMAS[table][2]
    for r in led.tables.get(table, []):
        for ref in split_ids(r.get(column, "")):
            if ref not in known:
                led.errors.append(f"{table} {r[key]}: {column} が存在しないID {ref} を参照")


def _cross_check(led: Ledgers) -> None:
    for table, column, target in [
        ("claims", "source_id", "sources"), ("claims", "person_id", "people"),
        ("sources", "person_id", "people"), ("people", "evidence_source_ids", "sources"),
        ("organizations", "evidence_source_ids", "sources"), ("products", "evidence_source_ids", "sources"),
        ("models", "evidence_source_ids", "sources"), ("experiments", "source_id", "sources"),
        ("experiments", "model_id", "models"), ("experiments", "claim_ids", "claims"),
        ("forecasts", "source_id", "sources"), ("forecasts", "claim_ids", "claims"),
        ("contradictions", "claim_ids", "claims"), ("claims", "contradictions", "contradictions"),
        ("source_access", "source_id", "sources"), ("role_evidence", "person_id", "people"),
        ("role_evidence", "source_id", "sources"), ("validations", "claim_id", "claims"),
        ("validations", "speaker_person_ids", "people"), ("validations", "cross_check_claim_ids", "claims"),
    ]:
        _refs(led, table, column, target)
    for s in led.tables.get("sources", []):
        if s["source_tier"] not in TIERS:
            led.errors.append(f"{s['source_id']}: source_tier {s['source_tier']!r} は未定義")
        if not s["observed_at"]:
            led.errors.append(f"{s['source_id']}: observed_at（観測日）が空")
    for c in led.tables.get("claims", []):
        cid = c["claim_id"]
        if not c["source_id"]:
            led.errors.append(f"{cid}: source_id が空（出典のない主張は登録できない）")
        if not c["original_position"]:
            led.errors.append(f"{cid}: original_position（原文位置）が空")
        if c["claim_type"] not in CLAIM_TYPES:
            led.errors.append(f"{cid}: claim_type {c['claim_type']!r} は {sorted(CLAIM_TYPES)} 以外")
        if c["firsthand_or_hearsay"] not in FIRSTHAND:
            led.errors.append(f"{cid}: firsthand_or_hearsay {c['firsthand_or_hearsay']!r} が不正")
        if c["verification_status"] not in VERIFICATION:
            led.errors.append(f"{cid}: verification_status {c['verification_status']!r} が不正")
        ex = c["original_language_excerpt_short"]
        if ex and (len(ex.split()) > MAX_EXCERPT_WORDS or len(ex) > MAX_EXCERPT_CHARS):
            led.errors.append(f"{cid}: 原文抜粋が長すぎる（短い引用のみ保存する）")
        if ex and not c["translation_ja"]:
            led.errors.append(f"{cid}: 原文抜粋に日本語訳が無い（原文・翻訳・要約を分離する）")
        if c["verification_status"] in VERIFIED and not ex:
            led.errors.append(f"{cid}: 照合済みなのに原文抜粋が無い")
    _check_person_evidence(led)


def _check_person_evidence(led: Ledgers) -> None:
    """本人性の4軸（P-1）: S1〜S4 を名乗る資料・人物には、検証済みの役割根拠が必要。"""
    roles = led.tables.get("role_evidence", [])
    by_person: dict[str, list[dict]] = {}
    for r in roles:
        rid = r["role_evidence_id"]
        by_person.setdefault(r["person_id"], []).append(r)
        if r["identity_status"] not in IDENTITY:
            led.errors.append(f"{rid}: identity_status {r['identity_status']!r} が不正")
        if r["determined_tier"] not in PERSON_TIERS:
            led.errors.append(f"{rid}: determined_tier {r['determined_tier']!r} が不正")
        if r["determined_tier"] in {"S1", "S2", "S3", "S4"}:
            if r["identity_status"] != "CONFIRMED":
                led.errors.append(f"{rid}: 本人性が未確認なのに {r['determined_tier']} と判定している")
            if r["verification_status"] not in VERIFIED or not r["excerpt"]:
                led.errors.append(f"{rid}: 役割の根拠が原文照合されていない（S1〜S4 に数えられない）")
        ex = r["excerpt"]
        if ex and (len(ex.split()) > MAX_EXCERPT_WORDS or len(ex) > MAX_EXCERPT_CHARS):
            led.errors.append(f"{rid}: 根拠の抜粋が長すぎる")
    for p in led.tables.get("people", []):
        tier = p["person_tier"]
        if tier in {"S1", "S2", "S3", "S4"}:
            ok = [r for r in by_person.get(p["person_id"], []) if r["determined_tier"] == tier
                  and r["identity_status"] == "CONFIRMED" and r["verification_status"] in VERIFIED]
            if not ok:
                led.errors.append(f"{p['person_id']}: person_tier={tier} だが、照合済みの役割根拠（role_evidence）が無い")
    acc = led.index("source_access") if led.tables.get("source_access") else {}
    for s in led.tables.get("sources", []):
        if s["source_tier"] in {"S1", "S2", "S3", "S4"}:
            a = acc.get(s["source_id"])
            if not a:
                led.errors.append(f"{s['source_id']}: {s['source_tier']} だが到達範囲（source_access）の記録が無い")
            elif a["reach"] in {"説明欄のみ", "取得不可"}:
                led.errors.append(f"{s['source_id']}: 本文に到達していないのに {s['source_tier']} として数えている")
            pids = split_ids(s["person_id"])
            if not any(r["source_id"] == s["source_id"] and r["determined_tier"] in {"S1", "S2", "S3", "S4"}
                       for pid in pids for r in by_person.get(pid, [])):
                led.errors.append(f"{s['source_id']}: {s['source_tier']} だが、この資料に紐づく照合済みの役割根拠が無い")
    for a in led.tables.get("source_access", []):
        if a["reach"] not in REACH:
            led.errors.append(f"{a['source_id']}: reach {a['reach']!r} が不正")
    for v in led.tables.get("validations", []):
        if v["statement_mode"] not in STATEMENT_MODES:
            led.errors.append(f"{v['validation_id']}: statement_mode {v['statement_mode']!r} が不正")
        if v["relation"] not in RELATIONS:
            led.errors.append(f"{v['validation_id']}: relation {v['relation']!r} が不正")
    for c in led.tables.get("candidates", []):
        if c["status"] not in CANDIDATE_STATUS:
            led.errors.append(f"{c['candidate_id']}: status {c['status']!r} が不正")

