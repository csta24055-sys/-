# チャット側1,000候補の全量取込み監査（機械生成）

生成時刻（UTC）：2026-11-15T16:13Z　／　生成：`python3 scripts/import_chat1000.py --cache <fetch cache>` → `python3 scripts/build_chat1000_docs.py`

> 本書は研究途中の監査記録であり、正式な最終報告ではない。RESEARCH_STATUS = INCOMPLETE。

## 1. 読み込んだ原本（CSVパーサで全行）

| 区分 | ファイル | 行数 |
|---|---|---:|
| チャット初回 | `external_handoff/BROAD_POOL_20261113_PRIMARY_SOURCES_BATCH01.csv` | 15 |
| チャット初回 | `external_handoff/BROAD_POOL_20261113_USER_EVIDENCE_BATCH02.csv` | 6 |
| チャット初回 | `external_handoff/BROAD_POOL_20261114_VERIFIED_DISCOVERY_BATCH03.csv` | 30 |
| チャット初回 | `external_handoff/BROAD_POOL_20261114_POLICY_SURVEYS_METHODS_BATCH04.csv` | 19 |
| チャット初回 | `external_handoff/CHAT500_WEB_ORIGINAL_SOURCES_20261114.csv` | 22 |
| チャット初回 | `external_handoff/CHAT500_PRIOR_SEARCH_LOG_INDEXED_BATCH05_20261114.csv` | 417 |
| チャット追加 | `external_handoff/CHAT_EXTRA500_WEB_DISCOVERY_20261114.csv` | 37 |
| チャット追加 | `external_handoff/CHAT_EXTRA500_WEB_DISCOVERY_BATCH02_20261114.csv` | 21 |
| チャット追加 | `external_handoff/CHAT_EXTRA500_PRIOR_LOG_SCREENED_BATCH03_20261114.csv` | 442 |

- 初回の行数：**509**、追加の行数：**500**、合計 **1009** 行（全行を `registry/chat1000_candidate_review.csv` に元ファイル名・行番号・元IDのまま収録）。
- 基礎479件＝`registry/source_evidence.csv` の 4af49d9 時点（464行、他チャットが監査した時点の版を `git show` で再現）＋補助2ファイル15行。

## 2. 件数の再計算（他チャットの正規化規則をそのまま再現）

| 項目 | 件数 |
|---|---:|
| 初回：異なるURLキー | 508 |
| 初回：基礎479と同じURLキー | 8 |
| 初回：内部の別名（同一キーが複数行） | 1 |
| **初回：基礎から見た新規URLキー** | **500** |
| 追加：異なるURLキー | 500 |
| 追加：基礎・初回と重なるキー | 0 |
| **追加：新規URLキー** | **500** |
| **チャット側の新規URLキー合計（基礎479基準）** | **1000** |

### 「502行／重複2」と「509行／重複8＋別名1」の食い違い

- 旧報告（`research/CHAT500_AUTOMATION500_SPLIT_PROGRESS_20261114.md`）の時点の版（コミット f4bc158）を `git show` で読むと、初回6ファイルは **502 行**、異なるURLキー 501。
- そのうち基礎479とURL文字列が完全一致するのは **2 件**（旧報告の「BPOOL042・BPOOL051の2件」）。arXivの abs/pdf/html・版番号などを同一視する正規化をかけると基礎との重複は **8 件**になる。
- その後、他チャットは `CHAT500_WEB_ORIGINAL_SOURCES_20261114.csv` に7行を追加（15→22行、コミット b64b569・c33211b「6件の見落とし別名を原著で置換」）し、**509 行・重複8・内部別名1・新規500** とした。
- 結論：**509行が現行ファイルの正しい行数**であり、502行は7行追加前の版の数。重複2は完全一致比較、重複8は正規化比較の結果で、正規化比較が正しい。新規500は「目標500に合わせた」結果ではなく、置換行を足した結果として500に一致している（追加行の経緯はコミット履歴に残る）。

### 現在の台帳との関係（基礎479以降に本パイプラインが追加した資料）

- 本パイプラインの台帳の採用資料は現在 **1224** 件（他チャット監査時の464件から増加）。チャット1,000候補のうち **169** 件は、本パイプラインの作業員が独自に取得・原文照合して既に台帳にある。
- このため `scripts/audit_chat_only_1000.py` を**現在の**台帳で実行すると新規キーは965件、`LEDGER_STRUCTURAL_PASS=false` となる（実行ログは本書 §6）。これは候補が減ったのではなく、基礎が増えたため。

## 3. 予定タスク側38件との照合（参照・重複除去専用。1,000件には算入しない）

- 読込：`BROAD_POOL_20261114_AUTOMATION_BATCH05.csv`（BPOOL071〜076）と `AUTOMATION500_BATCH01〜09_20261114.csv`（AUTO500_0001〜0032）、計 **38** 行。
- 照合キー：正規化URL、論文キー（DOI・arXiv ID・ACL ID）、`origin_group`。旧スクリプトはBPOOL071〜076の6件しか比較していなかった。

| 予定タスクID | URL | 1,000件側の一致 | 基礎479 | 現台帳 |
|---|---|---|---|---|
| AUTO500_0017 | https://www.nist.gov/publications/2025-nist-genai-text-challenge-evaluation-plan | CH1000_0513 | なし | なし |

- 一致した候補は1,000件側に残し（チャット側の行として収録済み）、予定タスク側は参照扱い。二重計上しない。

- 補足：`NEW_ORIGINAL_EVIDENCE_20261113_UX_MOBILE_WORKBENCH.csv`（8行）はどちらの会計にも名前が出ない第3の補助ファイル。基礎・1,000件と重なるのは 1 件。1,000件にも基礎479にも算入せず、別途の候補として扱う。

## 4. 1,000候補の読了深度・状態（他チャットの申告と、本パイプラインの記録を分けて集計）

### 他チャットの申告した読了深度（申告であり、本パイプラインの読了記録ではない）

| 区分 | 件数 |
|---|---:|
| SEARCH_RESULT_URL_ONLY | 727 |
| CLAIMED_LANDING_OR_ABSTRACT_READ | 148 |
| PRIOR_LOG_FETCH_NOT_RECHECKED | 132 |
| UNSTATED | 1 |
| CLAIMED_FULL_TEXT_READ | 1 |

- SEARCH_RESULT_URL_ONLY 727件＝検索結果のURLだけで原文未閲覧（初回300＋追加427）。PRIOR_LOG_FETCH_NOT_RECHECKED 132件＝本リポジトリの過去の検索ログに取得記録があるが再確認なし（初回117＋追加15）。これらを一次資料・原文確認済みに昇格させない。

### 本パイプラインのフェッチキャッシュでの状態（実際の取得記録）

| 状態 | 件数 |
|---|---:|
| NOT_IN_CACHE | 540 |
| HTTP_200_TEXT | 383 |
| BLOCKED_HTTP_403 | 40 |
| BLOCKED_HTTP_404 | 15 |
| BLOCKED_HTTP_200 | 13 |
| BLOCKED_HTTP_0 | 10 |
| BLOCKED_HTTP_406 | 5 |
| BLOCKED_HTTP_401 | 1 |
| BLOCKED_HTTP_503 | 1 |
| BLOCKED_HTTP_410 | 1 |

### 審査状態（`registry/chat1000_candidate_review.csv` の review_state）

| 状態 | 件数 | 意味 |
|---|---:|---|
| NOT_READ | 538 | 本パイプラインは未取得。作業員が原文を開いて判定する（HOLD扱い） |
| IN_LEDGER_QUOTE_VERIFIED_FOR_TOPIC | 111 | 本パイプラインが申告テーマについて原文引用を照合済み（S2精査待ち） |
| READ_NOT_YET_ASSESSED | 105 | 取得済みだが、申告テーマへの適合と引用は未判定（HOLD扱い） |
| BLOCKED_FETCH | 85 | 取得不可（HTTPエラー・本文なし） |
| REJECT_OFF_TOPIC | 65 | 作業員が原文を開き、テーマ不適合と判定 |
| IN_LEDGER_OTHER_TOPIC | 31 | 台帳にあるが別テーマ用。申告テーマへの適合は未判定 |
| DUPLICATE_ORIGIN | 26 | 1,000件内で同一URLキーまたは同一論文 |
| HOLD_QUOTE_NOT_ACCEPTED | 22 | 作業員は使うと報告したが引用が原文に見つからず不採用 |
| HOLD_NOT_ORIGINAL | 11 | 作業員が原文を開き、転載・要約と判定 |
| HOLD_VENDOR_PROMOTION | 11 | 作業員が原文を開き、データの無い宣伝と判定 |
| REJECT_NOT_A_SOURCE | 4 | サイトマップ等、資料ではない |

- S1に使える候補（本パイプラインが原文引用を照合済み、S2待ち）：**111** 件。残りはURL候補であって証拠ではない。
- 競合候補の公式ドメインに一致した候補：156 件（32 社）。他チャットが `AXIS_17_T08`（競合の記録用の仮テーマ）に付けた候補は、公式ドメインが一致する競合の調査単位へ割り当て直した。
- 未判定の候補を受け持つ調査単位：118。作業員1件あたり1回8件まで割り当て、読了・判定を `registry/candidate_assessments.csv` に記録する（自分で開いたページの判定だけを有効とする）。
- 作業員による判定済み：310 件（うち本人が実際に開いたもの 310）。

## 5. 単純なURLと実証根拠の差

| 段階 | 件数 | 根拠 |
|---|---:|---|
| URL候補（チャット側の新規キー） | 1000 | 本書 §2 |
| 本パイプラインが原文を取得できた（HTTP 200・本文あり） | 383 | フェッチキャッシュ |
| 台帳に採用（原文引用の機械照合済み、どのテーマ用かを問わず） | 169 | `registry/source_evidence.csv` |
| 申告テーマについて引用照合済み（S1に使える、S2待ち） | 111 | `registry/source_topic_map.csv` |
| S2で精査済み（正式な分析集合） | 0 | S2未着手（S1未通過のため） |
| 異なる起源グループ（重複・非資料を除く、暫定） | 975 | 論文キー・申告起源・URLキーによる暫定値。独立性はS2で確定 |

## 6. 他チャットの監査スクリプトの実行記録

`python3 scripts/audit_chat_only_1000.py` を実行（2026-11-15、本セッション）。現在の台帳を基礎として読むため `total_net_chat_url_candidates = 965`、`LEDGER_STRUCTURAL_PASS = false`（終了コード2）。原因は §2 のとおり基礎台帳の増加で、候補ファイル側の欠落ではない。他チャット監査時点の基礎（464行）で再計算すると新規1,000件と一致する（本書 §2）。スクリプトは変更していない。

