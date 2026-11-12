# S1・P0未完了6競合の詳細調査（2026-11-13）
RESEARCH_STATUS = INCOMPLETE / FIRST_UNMET_GATE = S1
対応ID：C008 Beautiful.ai、C009 Plus AI、C023 SlideSpeak、C028 MiriCanvas、C034 WPS AI Presentation、C036 ChatPDF
参照：`PHASE1C_P0_COMPETITOR_CONSTRAINT_SOURCES_20261113.csv` と `PHASE1C_P0_COMPETITOR_OFFICIAL_AMENDMENTS_20261113.csv`
**本研究は外部資料精読であり、競合の実機操作・同条件品質ベンチマーク・実際のPPTX検証は未実施。個別のS1完了を宣言しない。**

## C008 Beautiful.ai
- 類型：AI資料生成＋Smart Slideテンプレート。公式 https://support.beautiful.ai/hc/en-us/articles/30629528652685-Exporting-your-slides-and-presentations
- 出力：Pro/Team/Enterpriseで編集可能なPPTXとGoogle Slides。別途PowerPoint画像スライド出力は非編集形式。発表者ノートは含み得る。**エクスポート先でアニメーション/トランジションは失われ、未導入フォントでレイアウト変更**（公式明記）。PDFも提供。
- 料金：有料Pro等が必要だが契約周期・通貨別詳細価格は追加検証が必要。読み込みはWord等が利用者レビューにあるが対象形式/最大サイズの原文を公式で再確認できていない。
- 反証・独立な利用者声：G2個別レビュー https://www.g2.com/products/beautiful-ai-beautiful-ai/reviews には細かい位置移動に制約、PowerPoint出力後の文字・枠・フォント修正が必要との複数自己申告がある。一方、時間削減を評価する声もある。**G2の掲載レビューは自発的サンプルで、不具合発生率として統計化しない。**
- 結論保留：出典・数値検証能力、機密データ保存、保証されたレイアウト精度、日本語OCR、生成時間の分位点、ユーザーの定量的困難率は未特定。

## C009 Plus AI
- 類型：PowerPoint/Google Slidesアドイン。公式 https://guide.plusai.com/plus-ai/troubleshooting
- 公式が列挙する制約：1回の新規生成最大30スライド、PowerPoint Web版では生成内容のフォーマットが正しく出ないことがある。元のPPTXをファイルとしてアップロードして再生成すると、**原内容が並べ替え・書換えされ、既存のレイアウトを保持する目的には不向き**。プロンプトによる詳細デザイン指示の直接反映には制約あり。
- 支払プランはBasic/Pro/Team等。金額は https://plusai.com/pricing の取得時点値を別に確認済み。ただし契約サイクルによる金額差がある。
- 反証：上記自社公式の『Troubleshooting』が直接の失敗・制約証拠。他社運営の利用者レビューからの独立な定量反証は未取得。
- 未確認：ファイル容量とページ数上限、原資料と数値の自動一致検査、日本語OCR品質、送信先の詳細、会社/学校それぞれの実ユーザー需要、実機の編集性。

## C023 SlideSpeak
- 類型：PDF/Word/PPTX/Excel等を素材にAIプレゼン生成。公式 https://slidespeak.co/help/articles/what-file-types-can-i-use-to-create-my-ai-presentation
- PPTX再構成：既存PPTXのRedesignは100MB上限、Freeは50MB。AI 4.0は1 credit/slide、AI 5.0は5 credit/slideと公表。複雑なアニメーションは維持されない。元ファイルの編集用Importは再生成と別処理。 https://slidespeak.co/help/articles/how-do-i-redesign-an-existing-powerpoint
- 出力：一般にはPremium/Premium Plus/Lifetimeで編集可能なPPTX/PDF/Google Slidesへのエクスポート、翻訳機能で作った資料は無料の例外。未導入フォントで見た目が変わり得る。 https://slidespeak.co/help/articles/how-do-i-download-my-presentation
- 料金：プランページ https://slidespeak.co/pricing はFree、Premium、Premium Plus、Enterpriseを区別。2026-11取得表示はPremium $29/月、Plus $34/月、Academic 25%割引の宣伝あり。ただし他のヘルプの価格・クレジット表記と相違があり、最新の表示・契約画面の突合が必要。
- データ保護：公式privacy https://slidespeak.co/privacy は保存180日を基本としAIサービスへの委託あり、学習不使用を主張。ChatGPT連携プレビューに認証不要URLが発生し、一部プレビューは元資料削除後も残る可能性があると明記。**公式声明をセキュリティ監査済みと同一視しない。**
- 反証・独立ユーザー：G2 https://www.g2.com/products/slidespeak/reviews は2026時点レビュー4件に限られ、2024年の1件で研究資料の重要事項の欠落が報告されている。別人の肯定的レビューもある。統計的故障率の推定に使えない。
- 未確認：同一文書での再現性、数値検算、PPTX編集要素比率、公開数値の生成時間、機密文書利用の契約条件、セキュリティ独立監査。

## C028 MiriCanvas
- 類型：デザイン編集＋AI Presentation。公式 https://help.miricanvas.com/hc/en-us/articles/60023640658201--How-to-Use-AI-Presentation-Easy-Guide
- **AI資料生成の素材添付はPro限定、1ファイル最大50MB**。PDF/DOCX/PPTX/XLSX/CSV/MD/TXT対応。資料からアウトラインを生成し、枚数・テンプレートを選びエディタで修正できると明記。文字欄は最大20,000字。
- **別ワークフロー**のPDF/PPTXエディタインポートはPDF最大50MB・100ページ、PPTX最大50MB・300ページと公式案内。両者の上限を混同しない。 https://help.miricanvas.com/hc/ja/articles/49787329928729-PDF-PPTXインポート機能の使い方ガイド
- 出力の選択肢：PPTXの『テキスト編集可能』『要素画像化』『各ページ1画像化』は編集可能性が全く違う。素材ライセンスによりテンプレ再配布禁止、フォントが未導入で表示が変わる場合がある。 https://help.miricanvas.com/hc/en-us/articles/45166181544089-How-to-Download-Your-Presentation-as-a-PPT-File
- 独立反証：G2 https://www.g2.com/products/miricanvas/reviews?qs=pros-and-cons にはテンプレート価格/限定的な編集柔軟性/読み込み遅延の利用者コメントがある。サンプルは任意投稿であり、AIプレゼン機能固有の失敗率ではない。
- 未確認：Proの日本向け価格の確定、個人データの保持と委託先、実機での数式・グラフ・PDF精読精度。

## C034 WPS AI Presentation
- 類型：オフィススイート内蔵のAIスライド。日本語公式 https://www.wps.com/ja-JP/office/presentation/ と https://ai.wps.com/ja-JP/
- 公式機能：Word/PDF等の資料・アウトラインからスライド生成、内容書換え・画像・スピーカーノート、PPTX/PDF出力。WPS PresentationはPPTX/PPT/PPSXの編集対応。AI生成サイトは推奨上限120MB以内、文字15万字未満と記載。**推奨値を必ず処理できる最大値と扱わない**。
- 公式の『100%互換』『ワンクリック』はマーケティング主張であり実機検証結果ではない。
- 反証：ChatGPTによる公式サイト原文の確認では限定機能・失敗時の割合を示す一次情報がまだない。独立のPPTX編集崩れ評価・日本語OCRテスト・AIプラン別利用枠が必要。
- 未確認：料金/クレジットと個別のAI利用制限、データ処理国と保管、外部AI委託、機密保持条件、速度のパーセンタイル、数値/出典検証。

## C036 ChatPDF
- 類型：PDF引用付きチャット／マルチファイルと**別途AI Slidesサービスが存在**。公式 https://www.chatpdf.com/ja と https://www.chatpdf.com/ai-slides
- AI SlidesはPDF/Word/テキストのアップロードからアウトライン生成→編集→PPTX出力を公式に案内。無料版の日次制限、Plusで無制限生成との主張あり。これにより『ChatPDFは資料生成しない』という古い判断を撤回し、潜在的な直接競合とも認定する必要がある。
- バックエンドの**PDF質問APIは別製品経路**で最大2,000ページまたは32MB/ファイル、Source ID付きのstateless会話と記述。 https://www.chatpdf.com/docs/api/backend この数値をAI Slidesの全形式・最大ページ数に適用してはいけない。
- 反証：実際のPPTX編集性、生成した文章の引用元追跡、料金・トライアル・制限、データ保持国、未成年/法人向け規約は追加の一次資料確認が必要。PDFチャットは引用対応を掲げるが、生成したスライドの全主張が自動照合される証拠はない。
- 未確認：AI Slidesの生成時間の分布、PPTXのフォント再現性と図表オブジェクト編集、学校/仕事の導入実測、利用者の不満・実機エラー。

## 非重複と研究ゲート
- 公式の同じ制約を複数記事で引用しても証拠の起源は**1事業者**。G2のユーザーレビューは投稿者間で別人でも調査設計上の無作為標本ではない。
- 6競合とも少なくとも独立サイトと公式規約の当初未着手部分を調べたが、必要11属性のすべてと独立な性能検証を満たしていない。**公式確認済み／性能実測済み／S1完了を混同しない**。
- 元の80候補を削除・別の製品に統合しない。C008/009/023/028/034/036のステータスは更新前の正本では`S1_INCOMPLETE`のまま。本ファイルを中間証拠として差分導入し、再度ゲートスクリプトを実行する必要がある。
