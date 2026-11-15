# スキーマ（値・候補・プロジェクトの保存）

## 値（`wlcstudio/provenance.py` の `Value`）

| 項目 | 意味 |
|---|---|
| field_id | 入力欄の ID（`wlcstudio/fields.py`） |
| state | 7 つの状態：confirmed（取得・確認済み）／from_drawing（図面から計算）／statistical（統計推定）／assumption（仮定）／not_obtained（未取得）／not_applicable（適用外）／not_computable（計算不能） |
| value, unit | 値と単位（値のある状態だけが値を持つ。値の無い状態は値を持てない＝0 にできない） |
| method | 取り方（手入力、PLATEAU の属性、数量表の合計、RASMI × 延床面積 …） |
| source_id, source_detail | 出典の ID（`sources/registry.json` か資料の ID）と、その中の場所（シート・行・列、IFC の部材、ページ・行、建物 ID、表の行） |
| retrieved_at, factor_version, permission | 取得日、使ったデータ・原単位の版、利用許諾（例：CC-BY-4.0、政府標準利用規約2.0） |
| uncertainty | kind（none／interval／scenario／unknown＝根拠のある幅を付けられない推定）、low、high、level（信頼水準）、calibrated（独立のデータで当たり率を測ったか）、basis（範囲の作り方） |
| note, scope, depends, updated_at, updated_by | 説明、推定が欄の名前より広い範囲を含むこと（whole_building＝基礎を含む建物全体、all_steel＝鉄筋と鉄骨の全量。二重計上の防止に使う）、推定の前提（延床面積・構造・用途の区分。変わると結果に「概算し直す」）、保存の時刻、保存した人（候補を採用したときは「user（候補を採用: 出所）」） |

検査（`Value.check`）：値のある状態には値と取り方が要る；値の無い状態は値を持てない；統計推定には区間と出典が要る；図面からの計算には出典（資料）が要る；範囲は有限で下限 ≤ 上限。

## 入力欄（`wlcstudio/fields.py`）

4 画面に 75 項目（基本情報 19・材料 23・設備 20・運用 13）。各項目は、画面・グループ・5 大分類（building／construction／equipment／operation／assessment）・型・単位（受け付ける別の単位）・届くエンジンの入力・橋渡しでの使い方・必須か・「適用外」の意味（zero／absent／skip）・概算できるか・許す範囲・個人情報か、を持つ。既定値は持たない（係数を作らない）。

## プロジェクトの保存（`var/projects.sqlite3`、`wlcstudio/project.py`）

| 表 | 中身 |
|---|---|
| projects | id、名前、構造、data_kind（user／fictional_demo）、作成・更新時刻、既存アプリのプロジェクト id、最後の評価期間、位置（座標・PLATEAU の建物 id） |
| field_values | 値の履歴（追記だけ。今の値は最後に保存したもの） |
| candidates | 候補（自動調査・資料・概算）。採用するまで計算に使わない。状態 open／accepted／dismissed |
| later_flags | 「あとで確認」 |
| documents | 読み込んだ資料の名前・形式・SHA-256・大きさ・要約。原本は `--keep-uploads` のときだけ `var/uploads/`（権限 600） |
| research_log | 自動調査・概算の記録（出典 ID・件数。住所の文字列は残さない） |
| runs | 計算の結果の表示用の記録（入力の指紋・評価期間・状態） |

プロジェクトを削除すると、上の全部の行と保存した原本が消え、既存アプリの保存（`var/engine.sqlite3`）の変換した入力の版・条件・計算の記録と、メモリの準備済みの計算も消える（先に計算側を消すので、失敗してもやり直せる）。両方の保存は `secure_delete` で、消した部分を上書きする。

## エンジンへの文書（lca-input/1、`wlcstudio/bridge.py`）

既存アプリの入力形式そのもの（`12_APP_BASE/README.md`）。カテゴリーは 5 大分類、項目の ID はエンジンのモデルの名前。材料・設備・冷媒は表の行（`materials`・`equipment`・`refrigerants`）、燃料は `construction.fuels`、状態は `<所有者>.states` と `provenance` の表。参照セット（原単位）は `reference_set` で指定する。
