#!/usr/bin/env python3
"""Generate a Figma Plugin API script (for the use_figma MCP tool) that builds the
4-category token & screen-structure board from the prototypes' :root tokens.

Usage: python3 design-research/tools/build_figma_board.py > /path/to/figma_board.js
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

CATS = [
    {
        "key": "A", "dir": "A-research-lab", "title": "A 研究室内部用（研究支援）",
        "nav": "sidebar",
        "screens": {
            "ダッシュボード": ["測定サマリー（PM2.5/CO2/ISOクラス）", "異常値アラート ▲", "最近の計算ジョブ", "データ来歴"],
            "主要機能（計算条件入力）": ["計算条件フォーム（単位・範囲チェック）", "エンジン選択 SymPy/Sage/MATLAB", "高密度データ表", "実行・再現"],
            "詳細・結果": ["結果グラフ＋データ表", "計算根拠・入力の来歴", "変更履歴", "CSV / Excel / PDF"],
            "設定・管理": ["ロール（教授/院生/学部生）", "単位・桁数", "ショートカット一覧", "エンジン接続"],
        },
    },
    {
        "key": "B", "dir": "B-public", "title": "B 国家規模・公共向け",
        "nav": "top",
        "screens": {
            "ダッシュボード": ["注意報レベル（色＋文言＋アイコン）", "地域選択", "出典・更新日時", "一般/専門家 切替"],
            "主要機能（地域データ）": ["地域別の大気質", "公共建築物のCO2・LCA", "算出方法へのリンク", "やさしい日本語"],
            "詳細・結果": ["時系列グラフ＋表", "方法論・判断基準", "データ公開範囲", "CSV / API"],
            "設定・管理": ["言語 ja/en/やさしい", "文字サイズ", "災害時軽量モード", "プライバシー"],
        },
    },
    {
        "key": "C", "dir": "C-commercial", "title": "C 収益追求型の商用SaaS",
        "nav": "sidebar",
        "screens": {
            "ダッシュボード": ["オンボーディング 3ステップ", "サンプルデータで即体験", "使用量メーター", "次のおすすめ"],
            "主要機能（レポート作成）": ["空気質モニタ", "LCAレポート自動作成", "コマンドパレット ⌘K", "空状態からの誘導"],
            "詳細・結果": ["レポート詳細", "共有・書き出し", "アップグレード提案（控えめ）", "計測イベント"],
            "設定・管理（料金）": ["料金比較 Free/Pro/Team", "月額/年額・税込", "体験終了日・自動更新の明示", "ワンクリック解約"],
        },
    },
    {
        "key": "D", "dir": "D-enterprise", "title": "D 大企業品質（多組織プラットフォーム）",
        "nav": "sidebar",
        "screens": {
            "ダッシュボード": ["組織切替", "運用KPI", "承認待ち", "システム状態"],
            "主要機能（データ運用）": ["大規模テーブル（列固定・一括操作）", "フィルタ・保存ビュー", "ページング", "コマンドパレット"],
            "詳細・結果（承認フロー）": ["申請→レビュー→承認/差戻し", "状態タイムライン", "コメント", "監査ログ"],
            "設定・管理": ["ロール×権限マトリクス", "SSO / 2要素認証", "セッション管理", "ライト/ダーク"],
        },
    },
]

HEX = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{6})\b")
PX = re.compile(r"--((?:font|fs|text|type)[a-zA-Z0-9_-]*)\s*:\s*([0-9.]+)(px|rem)")


def tokens(cat):
    f = ROOT / cat["dir"] / "prototype.html"
    if not f.exists():
        return [], []
    src = f.read_text(encoding="utf-8")
    m = re.search(r":root\s*\{(.*?)\}", src, re.S)
    block = m.group(1) if m else src[:20000]
    seen, colors = set(), []
    for name, hx in HEX.findall(block):
        if name in seen:
            continue
        seen.add(name)
        colors.append({"name": name, "hex": hx.lower()})
    sizes = []
    for name, val, unit in PX.findall(block):
        px = float(val) * (16 if unit == "rem" else 1)
        if 10 <= px <= 64:
            sizes.append({"name": name, "px": round(px)})
    return colors[:28], sizes[:8]


def main():
    data = []
    for c in CATS:
        colors, sizes = tokens(c)
        data.append({**c, "colors": colors, "sizes": sizes})
    js = (ROOT / "tools" / "figma_board_template.js").read_text(encoding="utf-8")
    print(js.replace("/*__DATA__*/[]", json.dumps(data, ensure_ascii=False)))


if __name__ == "__main__":
    main()
