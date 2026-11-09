#!/usr/bin/env python3
"""STEP 0/1: build the company-first folder tree and register 8 x 240 topic slots.

Idempotent and non-destructive: files that already exist are never overwritten,
except the per-axis root-question rows, which are *merged* by question_id so that
research-added questions survive a re-run.

    python3 research/tools/scaffold.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    AS_OF, ASOF_SNAPSHOT, TEMPLATE_MARKER, axes, companies, company_dir, read_jsonl,
    research_root, short_code, write_csv, write_jsonl,
)

DOC_DIRS = [
    "01_総合研究報告書", "02_歴史・制度形成", "03_事業・資産・商流", "04_財務・銀行・融資・資本",
    "05_国家政策・外交・地政学", "06_経営・組織・人事・職種", "07_将来シナリオ・戦略",
    "08_因果関係図・社内外ネットワーク", "09_出典台帳・観測・モデル・検証", "10_未解決論点・次回調査",
]

# 一次情報源探索の初期ルート（各社共通の道筋。会社固有の資料は研究時に追加する）
AXIS_SOURCE_ROUTES = {
    "AXIS_01": ["有価証券報告書「沿革」", "会社公式の社史・沿革ページ", "国立国会図書館デジタルコレクション（社史）", "学術論文（経営史学会等）"],
    "AXIS_02": ["有価証券報告書「事業の内容」「セグメント情報」", "統合報告書", "決算説明資料"],
    "AXIS_03": ["財務省貿易統計", "UN Comtrade", "WTO統計", "会社のトレーディング事業開示"],
    "AXIS_04": ["有価証券報告書（金属資源セグメント・権益一覧）", "JOGMEC資料", "豪州・チリ等の資源当局/取引所開示", "パートナー企業の年次報告"],
    "AXIS_05": ["有価証券報告書（エネルギーセグメント）", "IEA", "資源エネルギー庁", "JBIC/NEXIプレスリリース", "プロジェクトパートナー開示"],
    "AXIS_06": ["有価証券報告書（食料・生活産業）", "FAO", "農林水産省", "子会社・投資先の開示"],
    "AXIS_07": ["有価証券報告書（化学品・ウェルネス）", "投資先の上場開示", "厚生労働省/各国規制当局"],
    "AXIS_08": ["有価証券報告書（機械・インフラ/モビリティ）", "投資先の年次報告", "業界統計"],
    "AXIS_09": ["有価証券報告書（不動産・インフラ）", "国土交通省", "PPP/PFI公表資料", "REIT開示"],
    "AXIS_10": ["統合報告書（DX）", "特許DB（J-PlatPat等）", "投資先開示"],
    "AXIS_11": ["IMF WEO", "世界銀行WDI", "OECD", "内閣府/各国統計局"],
    "AXIS_12": ["有価証券報告書（市場リスク・感応度）", "日本銀行/FRB統計", "社債発行条件"],
    "AXIS_13": ["有価証券報告書「流動性と資金調達の源泉」「金融債務注記」", "JBICプレスリリース", "NEXIニュースリリース", "社債発行登録書・発行条件", "格付会社公表"],
    "AXIS_14": ["有価証券報告書（連結財務諸表・注記）", "決算短信", "決算説明資料"],
    "AXIS_15": ["適時開示（TDnet）", "有価証券報告書（重要な後発事象・企業結合）", "相手先・当局の開示"],
    "AXIS_16": ["経済産業省/内閣府", "各国政府の政策文書", "JBIC/NEXI政策関連案件"],
    "AXIS_17": ["有価証券報告書「事業等のリスク」", "外務省", "制裁リスト（OFAC等）", "国際機関"],
    "AXIS_18": ["有価証券報告書（訴訟・偶発債務）", "公正取引委員会", "各国当局の処分公表"],
    "AXIS_19": ["有価証券報告書（物流事業）", "国土交通省港湾統計", "UNCTAD海運統計"],
    "AXIS_20": ["有価証券報告書「関係会社の状況」「主な連結子会社/持分法適用会社」", "大量保有報告書", "相手先の開示"],
    "AXIS_21": ["コーポレート・ガバナンス報告書", "有価証券報告書「役員の状況」", "株主総会招集通知"],
    "AXIS_22": ["有価証券報告書「従業員の状況」", "統合報告書（人的資本）", "会社採用ページ"],
    "AXIS_23": ["サステナビリティレポート", "有価証券報告書（サステナビリティ）", "現地当局・NGOの一次資料"],
    "AXIS_24": ["有価証券報告書「大株主の状況」", "大量保有報告書", "株価・配当データ"],
    "AXIS_25": ["有価証券報告書「事業等のリスク」", "減損注記", "危機時の適時開示"],
    "AXIS_26": ["各社の有価証券報告書（同一基準で再計算）", "海外商品商社の年次報告"],
    "AXIS_27": ["中期経営計画", "IEAシナリオ", "政府長期計画"],
    "AXIS_28": ["会社採用ページ", "有価証券報告書「従業員の状況」", "就職四季報等（二次資料・要注意）"],
    "AXIS_29": ["会社ニュースリリース", "主要報道（二次資料）", "訂正・撤回の記録"],
    "AXIS_30": ["個別案件の会社リリース", "JBIC/NEXI/相手先/当局の案件資料", "有価証券報告書の案件記述"],
}


def topic_rows(company: dict) -> list[dict]:
    rows = []
    for a in axes():
        rows.append({
            "company_topic_id": f"{company['company_id']}__{a['topic_id']}",
            "company_id": company["company_id"],
            "axis_id": a["axis_id"],
            "topic_id": a["topic_id"],
            "axis_name": a["axis_name"],
            "topic_name": a["subtopic"],
            "priority": a["priority"],
            "declared_state": "NOT_STARTED",
            "applicability": "UNKNOWN",
            "na_reason": "",
            "na_source_ids": "",
            "notes": "",
        })
    return rows


TOPIC_FIELDS = ["company_topic_id", "company_id", "axis_id", "topic_id", "axis_name", "topic_name", "priority",
                "declared_state", "applicability", "na_reason", "na_source_ids", "notes"]


def root_question(company: dict, a: dict) -> dict:
    sc = short_code(company["company_id"])
    t = a["topic_id"].split("_")[-1]
    ax = a["axis_id"].split("_")[-1]
    name, en = company["name_ja"], company["name_en"]
    return {
        "question_id": f"Q-{sc}-A{ax}-{t}-00",
        "company_id": company["company_id"],
        "axis_id": a["axis_id"],
        "topic_id": a["topic_id"],
        "parent_question_id": None,
        "kind": "ROOT_RESEARCH_CARD",
        "question": f"{name}において「{a['subtopic']}」は何が観測でき、なぜそうなっているか（研究カード12項目：What/When/Where/Who/資金/モノ/決定権/Why/反証/定量/変化/接続）",
        "search_queries": [
            f"{name} {a['subtopic']}",
            f"{en} {a['subtopic']}",
            f"site:{company['ir_url'].split('/')[2]} {a['subtopic']}",
        ],
        "source_route": AXIS_SOURCE_ROUTES.get(a["axis_id"], []),
        "priority": a["priority"],
        "status": "NOT_STARTED",
        "discovery_reason": "STEP1 初期登録（company_axis_registry.csv）",
        "claim_ids": [],
    }


def create_if_missing(path: Path, text: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def axis_synthesis_template(company: dict, axis_id: str, axis_name: str, topics: list[dict]) -> str:
    lines = [
        TEMPLATE_MARKER,
        f"# {company['name_ja']} / {axis_id} {axis_name}：社内独立軸レポート",
        "",
        f"> COMPANY_ID: `{company['company_id']}` / AXIS: `{axis_id}` / 状態: **NOT_STARTED**（未着手） / 基準日: {AS_OF}",
        "",
        "この軸はまだ調査されていない。以下のテーマは登録のみで、証拠・主張・分析は存在しない。",
        "",
        "| topic_id | テーマ | 状態 |", "|---|---|---|",
    ]
    for t in topics:
        lines.append(f"| {t['topic_id']} | {t['subtopic']} | NOT_STARTED |")
    lines += ["", "## 現時点で分かったこと", "（未着手）", "", "## 未確認の重要事項", "（未着手）", "",
              "## この軸が会社全体へ与える影響", "（未着手）", ""]
    return "\n".join(lines)


def company_report_template(company: dict) -> str:
    return f"""{TEMPLATE_MARKER}
# {company['name_ja']}：独立総合インテリジェンス研究書

> COMPANY_ID: `{company['company_id']}` / REPORT_STATUS: `NOT_STARTED` / 調査基準日: {AS_OF}

**これは研究成果ではない。** 原資料の調査・検証が行われるまで各章は空欄であり、他社の報告書から転記してはならない。

## 1. 会社の成立・歴史・経路依存
（未調査）
## 2. 全事業・商流・所有資産・グループ会社
（未調査）
## 3. 事業別の資本配分・収益構造・投資実行・撤退
（未調査）
## 4. 銀行融資・政策金融・金利・為替・財務
（未調査）
## 5. 政府・国家・規制・外交・国際金融
（未調査）
## 6. 世界情勢・市場・資源・物流・リスク
（未調査）
## 7. 経営者・ガバナンス・部門・人事・採用・意思決定
（未調査）
## 8. AI・技術革新・不動産・産業設備・環境
（未調査）
## 9. 個別案件の資金・製品・サービス・権限の流れ
（未調査）
## 10. 統計分析・数理モデル・競合仮説・反証
（未調査）
## 11. 2030・2035・2040・2050年の複数シナリオ
（未調査）
## 12. 社内30軸の分析をつなぐ会社固有の因果モデル
（未調査）
## 13. 他社・銀行・政府との立証済み関係リンク
（未調査）
## 14. 確認できない内容と追加調査
（未調査）
## 15. 2026-11-01版と月次版の差分／会社別研究ゲート
（未調査）
"""


def next_steps_template(company: dict) -> str:
    sc = short_code(company["company_id"])
    return f"""# {company['name_ja']}：次回再開手順（NEXT_STEPS）

1. `python3 research/research_gates.py --company {company['company_id']}` で現状のゲートを確認する。
2. 優先順位：P1テーマのうち AXIS_13（銀行・政策金融）/AXIS_14（財務）/AXIS_20（所有ネットワーク）から着手し、
   `axes/AXIS_XX/QUESTIONS.jsonl` のROOT問い `Q-{sc}-AXX-TYY-00` を原子的な問いに分割する。
3. 一次資料（有価証券報告書・統合報告書・決算短信・JBIC/NEXI等）を取得し、`ledger/sources.jsonl` に
   sha256・取得日時・公開日を記録、`ledger/passages.jsonl` にページ位置を記録する。
4. `ledger/search_log.jsonl` に検索クエリ・結果件数・採否理由を必ず追記する。
5. 基準日 {AS_OF} より後に公開された資料は `snapshot` を `monthly_YYYY-MM` として別扱いにする。
6. 他社フォルダの主張・出典IDを引用しない（ゲートがFAILになる）。
"""


def main() -> int:
    root = research_root()
    all_axes = axes()
    by_axis: dict[str, list[dict]] = {}
    for a in all_axes:
        by_axis.setdefault(a["axis_id"], []).append(a)

    for c in companies():
        cdir = company_dir(c)
        cdir.mkdir(parents=True, exist_ok=True)
        for d in DOC_DIRS:
            create_if_missing(cdir / d / "README.md",
                              f"# {c['name_ja']} / {d}\n\n会社内文書分類。内容は `axes/` の軸レポートと `INTEGRATED_COMPANY_REPORT.md` を正本とし、ここには該当章の補助資料を置く。\n")
        for d in ("datasets", "models", f"snapshots/{ASOF_SNAPSHOT}"):
            (cdir / d).mkdir(parents=True, exist_ok=True)
            create_if_missing(cdir / d / ".gitkeep", "")
        for led in ("sources", "passages", "observations", "relations", "search_log", "claim_status_events"):
            create_if_missing(cdir / "ledger" / f"{led}.jsonl", "")
        create_if_missing(cdir / "INTEGRATED_COMPANY_REPORT.md", company_report_template(c))
        create_if_missing(cdir / "NEXT_STEPS.md", next_steps_template(c))
        create_if_missing(cdir / "UPDATE_HISTORY.md", f"# {c['name_ja']}：月次更新履歴\n\n| UPDATE_ID | 実行日 | 結果 | 詳細 |\n|---|---|---|---|\n")

        tpath = cdir / "TOPIC_STATUS.csv"
        if not tpath.exists():
            write_csv(tpath, topic_rows(c), TOPIC_FIELDS)

        for axis_id, topics in by_axis.items():
            adir = cdir / "axes" / axis_id
            adir.mkdir(parents=True, exist_ok=True)
            create_if_missing(adir / "SYNTHESIS.md", axis_synthesis_template(c, axis_id, topics[0]["axis_name"], topics))
            create_if_missing(adir / "CLAIMS.jsonl", "")
            create_if_missing(adir / "HYPOTHESES.jsonl", "")
            qpath = adir / "QUESTIONS.jsonl"
            existing = {q["question_id"]: q for q in read_jsonl(qpath)}
            merged = []
            for t in topics:
                rq = root_question(c, t)
                merged.append(existing.pop(rq["question_id"], rq))
            merged.extend(existing.values())  # research-added questions are preserved
            write_jsonl(qpath, merged)
    print(f"scaffolded {len(companies())} companies x {len(by_axis)} axes x {len(all_axes)} topics under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
