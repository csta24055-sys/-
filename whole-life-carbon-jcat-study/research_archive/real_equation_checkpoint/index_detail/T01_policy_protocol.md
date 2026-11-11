# 索引の詳細 T01：統制文書と手順書

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R1-01](#ck-r1-01) | 2 | 指示書の写し 2 点（開発方針指示書、追加・変更指示 第1号） |
| [CK-R1-02](#ck-r1-02) | 2 | 研究プロトコル EVALUATION_PROTOCOL.md（v1.4 草稿。使われた規則と草稿の部分） |
| [CK-R1-03](#ck-r1-03) | 3 | 手順書 v1.4 で定めるとした規則と、台帳・順位・報告の未実施の修正設計 |
| [CK-R1-04](#ck-r1-04) | 4 | 手順書・指示書に対する未達と、書かれた規則と実際の食い違い |

<a id="ck-r1-01"></a>

## CK-R1-01　指示書の写し 2 点（開発方針指示書、追加・変更指示 第1号）

- **区分**：2　暫定・未検証成果
- **内容**：2026-11-11 に受領した指示書 2 点を、第9章の統制文書として保存した写し。研究の成果ではなく、旧研究が従った指示の記録である。追加・変更指示 第1号は「2 軸それぞれの上位 30％ だけを研究対象にする」制限を撤廃し、2 軸の評価を着手順序の決定だけに使うと定めた。
- **所在**：
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md)
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE_AMENDMENT_01.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE_AMENDMENT_01.md)
- **確かめ方**：保存した担当が各ファイルの冒頭に「受領した文面のまま」「受領した追加・変更指示の全文」と記載した。原文と照合した記録はない。第2回の検査は、この 2 文書を基準にして成果物の適合を点検した（文書そのものの検査ではない）。
- **確かめた者**：作成者のみ
- **言える範囲**：旧研究（09_APPROX_STUDY）に対する指示。2026-11-11 の停止の指示で旧研究は終了しており、新研究には新しい指示書が優先する。
- **関係する第2回の指摘**：REP-5、REP-6
- **第2回の指摘の影響**：文書そのものへの指摘はない。指示への適合の不足（近似の段階の未測定、近似候補の負荷と入力数の未測定）は CK-R1-04 に記載した。
- **今の時点で言ってよいこと**：旧研究はこの 2 文書を統制文書として保存し、成果物 1〜9 の構成と進捗台帳の 6 状態をこれに合わせた。第2回の検査は、成果物 1〜9 がすべて存在すること、70 単位すべてが研究対象であること（research_target_count 70）、6 状態の表示が追加・変更指示の文言と同じであること、アプリ・UI・Web のコードがないことを確認した。
- **使ってはいけない記述**：
  - この 2 文書が現在も有効な指示である（旧研究の終了により、経緯の記録になった）
  - 指示書 第6章の資源配分（75％・15％・10％）が守られた（どこにも報告がなく、第2回の検査も評価できなかった）
  - 「受領した文面のまま」が第三者に確かめられている（確かめた記録はない）
- **新研究での再利用**：候補にしない
  - 理由・注意：01_COMPLIANCE の禁止事項（原版ファイル・式・原単位・マクロを置かない、流用しない）は新研究でも有効で、この 2 文書の第1章・6項と同じ内容である。DIRECTIVE.md には外部リポジトリの URL が書かれている。
- **分類の根拠**：
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md):3-4（受領した文面のまま）
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md):225-230（資源配分の表）
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE_AMENDMENT_01.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE_AMENDMENT_01.md):3-4, 10-27（上位30％の撤廃、2 軸は着手順序だけ）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 5. Directive compliance）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):130（COULD NOT CHECK: resource allocation 75 / 15 / 10 %）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-02"></a>

## CK-R1-02　研究プロトコル EVALUATION_PROTOCOL.md（v1.4 草稿。使われた規則と草稿の部分）

- **区分**：2　暫定・未検証成果
- **内容**：指示書 2 点を、評価単位の定義（P2）、台帳の様式（P3）、軸 A（P4）、軸 B（P5）、着手順序（P6）、検証手順（P7）、6 段階の検討（P8）、進捗台帳の 6 状態（P10）に落とした手書きの手順書。HEAD にある版はコミット 60e720f の v1.4 草稿で、コミットの説明に「作業途中」と書かれている。
- **所在**：
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
- **確かめ方**：第2回の検査が、順位（P4〜P6）と進捗の状態（P10）を規則どおりに再計算し、保存された値と差 0 を確認した。P8 の裏付けの規則と統合の基準は、記録・コードと照合して不一致が見つかった。v1.4 の差分（60e720f、16 行追加・11 行削除）は停止前に主担当が書いたもので、検査を受けていない。
- **確かめた者**：独立検査（第2回）で再現（P4〜P6 と P10 の計算規則だけ）。v1.4 の差分は作成者のみ
- **言える範囲**：独立概念モデルの 70 評価単位と架空データに対する手順。P1 が明記するとおり、原版 3,818,483 数式ノードの調査手順ではなく、順位付けも「確定できた評価単位」についてのものである。
- **関係する第2回の指摘**：REP-10、REP-3、REC-5、REC-2、REP-4、REP-2、REC-1
- **第2回の指摘の影響**：REP-10 が古いと指摘した手順書の 3 点（P7 の採否の語彙 5 語がどの記録にも使われていない、P4 の a2 の説明が実際と違う、未測定の規則と UNDEFINED_MODEL に該当する単位がない）は、v1.4 草稿の本文で直してある。P8 の「SUCCESS の裏付け 3 条件を記録の生成時に機械的に確かめる」と「統合に数える基準」は、REP-3・REC-5・REC-2・REP-4 により、書かれたとおりには守られていないと分かった（本文は未修正）。P7 の「厳密同値は相対 1e-9 を超える差が 1 件でもあれば不合格」に当たる反例が REC-1（周期 1.000000001 年）で見つかっている。
- **今の時点で言ってよいこと**：実際に運用され、第2回の再計算で保存値と合った規則は次のとおり。P2（評価単位 70、根拠区分 53・9・6・2）。P4（重み a1 0.35、a2 0.15、a3〜a7 各 0.10。70 単位すべて測定。重みを変えた 3 通りの順位）。P5（3 者の観点別中央値の合計。3 者の合計の差が 6 点以上の単位を「割れ」とする）。P6（優先スコアの式、着手群 3、旧・上位 30％ は参考表示）。P10（6 状態の判定規則。第2回の 2 つの検査が記録から状態を再計算し、70 単位とも保存値と同じ）。v1.4 草稿が書き換えたのは、改訂履歴 1.4 の行、P3 の 4 行（inputs の注記、inputs_read_by_reference の行の追加、computable_in_reference の注記、構造分類 UNDEFINED_MODEL の注記）、P4 の 2 行（a2 の説明、未測定の規則の注記）、P7 の採否の語彙の表だけである。P0・P1・P2・P5・P6・P8・P9・P10 の本文は v1.3 のままである。
- **使ってはいけない記述**：
  - 改訂履歴 1.4 の行「時間の判定を正確な有理数演算で行うこと、統合に数える条件を…測定で確かめること、仕組みの確認を統合モデルの外側からの計数に改めること、近似候補の測定の範囲…を区別することを定めた」（本文 P7・P8 にこれらの規則は書かれていない。対応する実装は自己申告だけか、途中で止まっている）
  - P3 の `inputs_read_by_reference`・`n_inputs_read`・`inputs_declared_not_read`・`inputs_read_not_declared`（台帳 70 単位のどれにもこの項目はない。作る段階 b3 は未着手）
  - P8「SUCCESS の記録は (1) 出力の一致 (2) 仕組みの計数 (3) 導出 を、記録の生成時に機械的に確かめる」（SUCCESS 118 件のうち 3 つともあるのは 96 件。なくても生成は失敗しない）
  - P8「M2（統合）に数えるのは、値を共有の表から読むか、共有のパラメータ付き関数で求める単位だけ」が 66 単位すべてで満たされているという読み方
  - P1「01〜08章（PR #5 の既存研究資料） 全件確認済み」（リポジトリの内容からは確かめられない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究の評価手順を書くときのひな形にする。使える部分：検証状態の語彙（導出と架空データの両方／架空データだけ／未検証）、厳密同値の合否（相対 1e-9 を超える差が 1 件でもあれば不合格）、誤差の符号を保って過小評価を別に集計する規則、同一言語・同一実行方式どうしで負荷を比べる規則、進捗の 6 状態と判定規則。
  - 条件・注意：v1.4 は草稿で、改訂履歴の 1.4 の行と本文が合っていない。P8 の裏付けの規則は機械的な強制になっていなかったので、そのまま写さない。新研究の指示書が優先する。
- **分類の根拠**：
  - git show 60e720f -- [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)（差分は 16 行追加・11 行削除。コミットの説明「work in progress」）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):12（改訂履歴 1.4）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):34-35（全式調査は独立概念モデルが対象）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):65-66, 79, 98, 107, 115, 185-194（v1.4 で書き換えた行）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):211-212（P8 の裏付けの条件と統合の基準。v1.3 のまま）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):64-69（REP-10）、15-20（REP-3）、128（P10 の状態を再計算して差 0）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):49-59（REC-5: 96 of the 118 SUCCESS records carry all three backings）、110（progress_ledger.py implements P10 as written）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)（70 単位の項目名に inputs_read_by_reference がない。JSON の解析で確認）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-03"></a>

## CK-R1-03　手順書 v1.4 で定めるとした規則と、台帳・順位・報告の未実施の修正設計

- **区分**：3　研究途中の数式・仮説
- **内容**：第2回の指摘を受けて決めた修正の設計のうち、手順書・台帳・順位・報告に関するもの。手順書の改訂履歴 1.4 の行と、保存された作業指示（SPEC_B3.md、STAGE_C_NOTES.md）に書かれている。段階 b3（台帳の入力項目の実測）と、記録・報告の再生成は着手されていない。
- **所在**：
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
  - [`materials/interrupted_fix/specs/SPEC_B3.md`](../materials/interrupted_fix/specs/SPEC_B3.md)
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md)
- **確かめ方**：なし。設計の文書だけである。(a)〜(d) に当たるコードの一部は 65ff124 にあるが、段階 a1・b2 は作業担当の自己申告だけ、a2 は途中で止まっており、どれも独立の検査を受けていない。(e)〜(k) は未着手。内訳：(a) 時間の判定を正確な有理数演算で行う。(b) 統合の所属を「共有の表・関数を壊すと、その単位の出力が変わる」ことの測定で確かめる。(c) 仕組みの確認を統合モデルの外側からの計数にする。(d) 近似候補の測定の範囲を単位・段階・建物全体に分けて記録する。(e) 基準計算が読んだ入力を単位ごとに追跡して台帳に書く。(f) structure_class_counts を単位から毎回計算する。(g) シート族の状態を規則で付ける（数式 0 件の族は常に NON_CALCULATION、既存単位と追加単位の両方が関連する族は COVERED_BY_BOTH）。(h) A13-04 の台帳の文面を現状に合わせる。(i) 評価者の提案の対照を P5 の観点どおりに付け直す（b1→M1、b2・b3・b4→M2、b5・b6→M3、b8→M4 と M5、b7 は入力削減として別に扱う）。(j) 順位の文面を「軸 A 22 件、ほかに重みを変えた場合だけ入るもの 6 件、軸 B 30 件、和集合 42 件（A と B だけなら 38 件）」に直す。(k) 全測定と記録・報告の再生成の順序。
- **確かめた者**：なし
- **言える範囲**：設計案。実施されていない。
- **関係する第2回の指摘**：REP-1、REP-2、REP-7、REP-8、REP-10、REP-11、REP-18、REC-1、REC-2、REC-4、REC-5、REP-5
- **第2回の指摘の影響**：これらの指摘への対応として書かれた設計である。指摘そのものは解消していない。
- **今の時点で言ってよいこと**：第2回の指摘のうち台帳・順位・手順書に関するものについて、どう直すかの設計が文書として残っている。実施はされていない。
- **使ってはいけない記述**：
  - 手順書の改訂履歴 1.4 の行を、規則が実施済みであるという意味に読むこと
  - SPEC_B3.md の項目（inputs_read_by_reference など）が台帳に入っているという読み方
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で検証の裏付けを設計するときの案として使う：共有部品を壊して出力の変化を見る所属の確認、外側からの演算の計数、測定の範囲の 3 区分（単位・段階・建物全体）、単位ごとの入力の追跡。
  - 条件・注意：設計だけで、有効かどうかは確かめられていない。旧研究の修正の続きとして実行しない。(a) は基準計算の時間の規則を変えるので、新研究の「基準計算を変えない」条件に触れる。
- **分類の根拠**：
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):12
  - [`materials/interrupted_fix/specs/SPEC_B3.md`](../materials/interrupted_fix/specs/SPEC_B3.md):20-57（b3 の変更 1〜5）
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md):10-18, 31-32, 40-44, 49-50, 60-63
  - [`STOP_STATUS.md`](../STOP_STATUS.md):50-62（a1・b2 は完了報告だけ、a2 は途中、b3 と再生成は未着手）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-04"></a>

## CK-R1-04　手順書・指示書に対する未達と、書かれた規則と実際の食い違い

- **区分**：4　不具合・未解決事項
- **内容**：手順書と指示書が求める内容のうち、第2回の検査で実際とずれていると分かった点、および確かめる手段がない点の一覧。どれも HEAD に残っている（修正は中断、記録と報告の再生成は未着手）。
- **所在**：
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md)
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md)
- **確かめ方**：第2回の「報告書の監査」「記録の監査」の検査が、記録（03_MODELS/records）、進捗台帳、コードを手順書の文面と照合した。記録の監査の指摘には反証役の検証者が付き、REC-2・REC-5 は CONFIRMED。報告書の監査（REP）には第2の検証者は付かず、全体の調整役が検査のスクリプトを再実行して同じ結果を得た。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：独立概念モデルの記録と報告（43ba5d7 の版）についての指摘。
- **関係する第2回の指摘**：REP-3、REP-4、REP-5、REP-6、REP-10、REP-15、REC-2、REC-5
- **第2回の指摘の影響**：(1) P8 の裏付け 3 条件：SUCCESS 118 件のうち、仕組みの確認がないもの 18 件、導出がないもの 5 件、両方ないもの 1 件（EX-QA-04-M1）。3 つともあるのは 96 件。なくても記録の生成は失敗しない（REC-5、REP-3）。(2) P8 の統合の基準：66 の所属のうち少なくとも 3（X-13、B1-01、SYS-03）は基準を満たさず、A13-05 は基準の文面にない読み方をした場合だけ満たす。裏付けられる数は 62〜63 単位（REC-2 の検証者の見積り）。K5 の 8 単位を含む 14 単位は、M1 が該当なしで M2 の裏付けが出力の一致だけ（REP-4）。(3) 追加・変更指示 3 項と指示書 第4章・第8章：M3〜M6 の 280（単位×段階）のうち 204 が測定なしの NOT_APPLICABLE。測定した近似候補が 1 つもない 17 単位が「検証完了」と表示されている（REP-5）。(4) 指示書 第5章：近似候補 32 種には誤差だけが記録され、時間・メモリ・命令数・入力数の測定がない。材料区分別の内訳は 7 種だけ（REP-6）。(5) 手順書 P3 が述べる入力の実測の 4 項目は台帳にない。改訂履歴 1.4 の行が挙げる 4 規則は本文にない（この読み取りで確認）。(6) 第2回の検査の結果は INDEPENDENT_REVIEW.md に書かれていない。この文書は今も「対応後の版に対する独立した検査は、まだ行っていない」と述べる。09_APPROX_STUDY/README.md の本文は、成果物 6 に「独立した検査」を限定なしで挙げる（REP-15。冒頭の手書きの追記は、本文が第2回の指摘を反映していないと断っている）。
- **今の時点で言ってよいこと**：上の (1)〜(6) は第2回の検査の記録どおりである。確かめる手段がない点：分析担当・軸 B の評価者・第1回の検査担当が互いの出力を見ずに作業したかどうか、01〜08 章を全件確認したかどうか（P1）、資源配分 75％・15％・10％。進捗台帳の状態の判定そのものは P10 の規則どおりに行われている（再計算で 70 単位とも同じ）が、B1-01・A13-05・X-13 の状態は、基準を満たさないとされた M2 の記録に依存している。その記録を除くと B1-01 は「未検証」、A13-05 と X-13 は「検証完了・近似不採用」になる（REC-2 の検証者の再計算）。
- **使ってはいけない記述**：
  - 「66 単位が 7 つの統合モデルに、結果を変えずにまとまった」「計算の定義の数 70 → 11」（所属の一部は基準を満たさない）
  - 「SUCCESS は、出力の一致・仕組みの計数・導出の 3 つに裏付けがあるものだけ（裏付けがなければ生成が失敗する）」
  - 「M4 … 保留 39 単位」「このうち 44 単位は、近似の段階に実データ待ちの保留がある」を、単位ごとに近似候補を調べた数として読むこと（39 のうち 26 は建物全体の代理モデル AP-15 だけが記録）
  - INDEPENDENT_REVIEW.md が検査の全体を記録しているという読み方（第2回の 59 件は未記載）
- **新研究での再利用**：候補にしない
  - 理由・注意：Route A で旧研究の統合の結果を使う場合、所属と裏付けは REC-2・REC-5 を前提に読む。詳細は 03_MODELS と 05_DECISIONS を担当する読み取りの結果を参照。
- **分類の根拠**：
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):13-23（REC-2、CORRECTED: about 62-63 units）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):49-59（REC-5）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):15-20（REP-3）、22-27（REP-4）、29-34（REP-5）、36-41（REP-6）、99-104（REP-15）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):7（対応後の版に対する独立した検査は、まだ行っていない）
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):3-9（終了と、本文が第2回の指摘を反映していない旨の追記）、64（成果物 6）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):130（COULD NOT CHECK）
- **分類した観点**：R1（統制文書・台帳・順位）

