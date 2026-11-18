# 監査用スクリプト（保護データはローカルのみ）

- 研究上の**安全な構造メタデータ**を集計・検算するためのスクリプト。
- 元J-CATファイル、原版の計算式本文、係数、マクロ、PDF、全セル値を公開Gitに追加しない。
- `local-only/`、`restricted-originals/`、`raw-licensed-data/`、`raw-formula-extraction/` は .gitignore で除外する。
- スクリプト自体は原版のExcelやVBAを実行しない。計算結果の数値的な正しさは証明しない。
- 数式の件数は共有数式を含むXMLノード数として数える。個別表現は権利確認前に公開しない。

詳しくは[第1章の禁止事項](../01_COMPLIANCE/README.md)。
