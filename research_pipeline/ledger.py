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
}

CLAIM_TYPES = {"経験", "主張", "実験", "広報", "推測"}
FIRSTHAND = {"一次", "伝聞", "不明"}
VERIFIED = {"verbatim_auto_verified", "manual_verified"}
VERIFICATION = VERIFIED | {"paraphrase_only", "unverified", "failed"}
TIERS = {"S1", "S2", "S3", "S4", "S5", "V1", "H1"}
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
