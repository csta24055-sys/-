# ゲート監査の詳細（機械生成）

生成時刻（UTC）：2026-11-15T15:47:21.191167+00:00

RESEARCH_STATUS = INCOMPLETE
最初に未達の工程：S1

- 実行した検索・アクセス：2620
- 採用資料：901（うちS2精査済み 0、独立起源 0）
- テーマ（S1完了）：85
- 旧検索候補：{"NOT_EXECUTED": 560, "EXECUTED": 336}
- 競合候補（S1完了）：20、公式確認 55
- 計算ID：1023

## S0 reaudit_and_scope_lock：PASS（15/15）

- PASS：scope lock: 325 topics / 32 axes (required 325 / 32)
- PASS：legacy query candidates: 896 (required 896)
- PASS：search plans cover every topic: 325
- PASS：competitor candidates: 80 (required 80)
- PASS：added-hypothesis topics (outside the 325): 7 (required 7)
- PASS：scope content (topic wording, legacy query strings, candidate names / priority, added topics) equals the locked scope
- PASS：all original topics and candidates are preserved
- PASS：user reference images present and unmodified: 8/8
- PASS：manifest forbids app implementation
- PASS：ten stage records in research_status.json
- PASS：repository / environment re-audit recorded for this continuation
- PASS：status ledgers have a fixed row for every id: queries 896, topics 325, competitors 80
- PASS：status ledgers equal the recomputation from the primary ledgers (not hand-edited, not stale)
- PASS：full-scope execution plan exists
- PASS：earlier provisional deliverables are quarantined with a banner: 5

## S1 collection_all_topics_queries_competitors：FAIL（4/9）

- FAIL：topics with a complete research-unit collection: 85/325
  - 次の要求アクション：run the topic worker for the listed topics (legacy queries verbatim, primary / independent / counter routes, unit record)
  - 未達 240 件（先頭60件）：AXIS_01_T01: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_01_T02: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_01_T03: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_01_T04: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_01_T05: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_01_T06: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_01_T07: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_01_T08: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_03_T01: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_03_T02: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_03_T03: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_03_T04: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_03_T05: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_03_T06: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_03_T07: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_03_T08: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_05_T02: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_05_T03: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_05_T04: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_05_T05: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_05_T06: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_05_T07: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_05_T08: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_06_T01: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_06_T02: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_06_T03: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_06_T04: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_06_T05: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_06_T06: legacy queries not executed: 4; independent: ATTEMPTED_INSUFFICIENT (own quer ／ AXIS_06_T07: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_06_T08: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_12_T05: independent: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 14); counter ／ AXIS_13_T05: independent: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 16); counter ／ AXIS_13_T06: primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 9); independent: ／ AXIS_13_T07: primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 10); independent ／ AXIS_13_T08: independent: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 5); counter: ／ AXIS_14_T01: primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 7); independent: ／ AXIS_14_T02: primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 7); independent: ／ AXIS_14_T03: independent: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 7); counter: ／ AXIS_14_T04: primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pages read 8); independent: ／ AXIS_14_T05: legacy queries not executed: 4; primary: ATTEMPTED_INSUFFICIENT (own queries  ／ AXIS_14_T06: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_14_T07: legacy queries not executed: 4; independent: ATTEMPTED_INSUFFICIENT (own quer ／ AXIS_14_T08: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_15_T01: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_15_T02: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_15_T03: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_15_T04: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_15_T05: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_15_T06: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_15_T07: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_15_T08: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_16_T01: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_16_T02: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_16_T03: legacy queries not executed: 4; primary: ATTEMPTED_INSUFFICIENT (own queries  ／ AXIS_16_T04: legacy queries not executed: 4; no primary-route search; independent: NO (own ／ AXIS_16_T05: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_16_T06: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_16_T07: legacy queries not executed: 4; no primary-route search; primary: NO (own que ／ AXIS_16_T08: legacy queries not executed: 4; no primary-route search; primary: NO (own que
- FAIL：legacy queries handled: executed 336, attempted-but-blocked 0, not executed 560 (of 896)
  - 次の要求アクション：execute each listed legacy query verbatim once
  - 未達 400 件（先頭60件）：AXIS_01_T01_Q1 ／ AXIS_01_T01_Q2 ／ AXIS_01_T01_Q3 ／ AXIS_01_T01_Q4 ／ AXIS_01_T02_Q1 ／ AXIS_01_T02_Q2 ／ AXIS_01_T02_Q3 ／ AXIS_01_T02_Q4 ／ AXIS_01_T03_Q1 ／ AXIS_01_T03_Q2 ／ AXIS_01_T03_Q3 ／ AXIS_01_T03_Q4 ／ AXIS_01_T04_Q1 ／ AXIS_01_T04_Q2 ／ AXIS_01_T04_Q3 ／ AXIS_01_T04_Q4 ／ AXIS_01_T05_Q1 ／ AXIS_01_T05_Q2 ／ AXIS_01_T05_Q3 ／ AXIS_01_T05_Q4 ／ AXIS_01_T06_Q1 ／ AXIS_01_T06_Q2 ／ AXIS_01_T06_Q3 ／ AXIS_01_T06_Q4 ／ AXIS_01_T07_Q1 ／ AXIS_01_T07_Q2 ／ AXIS_01_T07_Q3 ／ AXIS_01_T07_Q4 ／ AXIS_01_T08_Q1 ／ AXIS_01_T08_Q2 ／ AXIS_01_T08_Q3 ／ AXIS_01_T08_Q4 ／ AXIS_03_T01_Q1 ／ AXIS_03_T01_Q2 ／ AXIS_03_T01_Q3 ／ AXIS_03_T01_Q4 ／ AXIS_03_T02_Q1 ／ AXIS_03_T02_Q2 ／ AXIS_03_T02_Q3 ／ AXIS_03_T02_Q4 ／ AXIS_03_T03_Q1 ／ AXIS_03_T03_Q2 ／ AXIS_03_T03_Q3 ／ AXIS_03_T03_Q4 ／ AXIS_03_T04_Q1 ／ AXIS_03_T04_Q2 ／ AXIS_03_T04_Q3 ／ AXIS_03_T04_Q4 ／ AXIS_03_T05_Q1 ／ AXIS_03_T05_Q2 ／ AXIS_03_T05_Q3 ／ AXIS_03_T05_Q4 ／ AXIS_03_T06_Q1 ／ AXIS_03_T06_Q2 ／ AXIS_03_T06_Q3 ／ AXIS_03_T06_Q4 ／ AXIS_03_T07_Q1 ／ AXIS_03_T07_Q2 ／ AXIS_03_T07_Q3 ／ AXIS_03_T07_Q4
- FAIL：competitor candidates explored: 20/80
  - 次の要求アクション：run the competitor worker for the listed candidates
  - 未達 60 件（先頭60件）：C010 SlidesAI: no counter / independent search with results and no third-party-backed coun ／ C012 Claude: no counter / independent search with results and no third-party-backed counte ／ C013 Gemini: no counter / independent search with results and no third-party-backed counte ／ C014 Perplexity: no counter / independent search with results and no third-party-backed co ／ C015 Google Slides without AI: no counter / independent search with results and no third-p ／ C017 Pitch: no counter / independent search with results and no third-party-backed counter ／ C018 Prezi AI: no counter / independent search with results and no third-party-backed coun ／ C019 Decktopus: no counter / independent search with results and no third-party-backed cou ／ C020 Presentations.AI: no counter / independent search with results and no third-party-bac ／ C021 Slidesgo AI Presentation Maker: no counter / independent search with results and no t ／ C022 MagicSlides: no counter / independent search with results and no third-party-backed c ／ C024 Alai: no counter / independent search with results and no third-party-backed counter  ／ C025 Chronicle: no counter / independent search with results and no third-party-backed cou ／ C029 PageOn.ai: no counter / independent search with results and no third-party-backed cou ／ C030 Slidebean: no counter / independent search with results and no third-party-backed cou ／ C032 Visme: no counter / independent search with results and no third-party-backed counter ／ C033 Zoho Show Zia: no counter / independent search with results and no third-party-backed ／ C035 Figma Slides: no counter / independent search with results and no third-party-backed  ／ C037 AskYourPDF: attributes not recorded: official_site,features_processing,pricing_limits ／ C038 PDF.ai: no counter / independent search with results and no third-party-backed counte ／ C039 Humata: no counter / independent search with results and no third-party-backed counte ／ C040 UPDF AI: attributes not recorded: official_site,features_processing,pricing_limits,io ／ C041 Foxit PDF AI: no vendor page read (read 0, blocked attempts on distinct vendor pages  ／ C042 Smallpdf AI PDF: no counter / independent search with results and no third-party-back ／ C044 SciSpace: no counter / independent search with results and no third-party-backed coun ／ C045 Elicit: no counter / independent search with results and no third-party-backed counte ／ C046 Consensus: no counter / independent search with results and no third-party-backed cou ／ C047 Scholarcy: no counter / independent search with results and no third-party-backed cou ／ C048 Jenni AI: no counter / independent search with results and no third-party-backed coun ／ C049 Paperpal: no counter / independent search with results and no third-party-backed coun ／ C050 scite: no counter / independent search with results and no third-party-backed counter ／ C052 Kimi AI: no counter / independent search with results and no third-party-backed count ／ C053 Notion AI: no counter / independent search with results and no third-party-backed cou ／ C054 Coda AI: attributes not recorded: official_site,features_processing,pricing_limits,io ／ C055 Jasper: no counter / independent search with results and no third-party-backed counte ／ C056 Grammarly: attributes not recorded: official_site,features_processing,pricing_limits, ／ C057 Glean: no counter / independent search with results and no third-party-backed counter ／ C058 StudyFetch: attributes not recorded: official_site,features_processing,pricing_limits ／ C059 Knowt: attributes not recorded: official_site,features_processing,pricing_limits,io_f ／ C060 Quizlet AI: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/ ／ C061 Mindgrasp: attributes not recorded: official_site,features_processing,pricing_limits, ／ C062 LibreOffice Impress: no vendor page read (read 0, blocked attempts on distinct vendor ／ C063 Zapier AI Workflows: no vendor page read (read 0, blocked attempts on distinct vendor ／ C064 n8n Workflows: no vendor page read (read 0, blocked attempts on distinct vendor pages ／ C065 SlidesPilot: attributes not recorded: official_site,features_processing,pricing_limit ／ C066 Smallppt: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, ／ C067 AIPPT: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, se ／ C068 Piktochart AI: no vendor page read (read 0, blocked attempts on distinct vendor pages ／ C069 Napkin AI: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2 ／ C070 Storydoc: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, ／ C071 DeckRobot: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2 ／ C072 Templafy: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, ／ C073 MagicSchool AI: no vendor page read (read 0, blocked attempts on distinct vendor page ／ C074 Brisk Teaching: no vendor page read (read 0, blocked attempts on distinct vendor page ／ C075 Curipod: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2,  ／ C076 StudyPocket: no vendor page read (read 0, blocked attempts on distinct vendor pages 0 ／ C077 Marp: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, sea ／ C078 Quarto: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, s ／ C079 Pandoc: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, s ／ C080 Docling: no vendor page read (read 0, blocked attempts on distinct vendor pages 0/2, 
- FAIL：additional-hypothesis topics (outside the 325) explored: 0/7
  - 次の要求アクション：run the topic worker for the listed additional topics
  - 未達 7 件（先頭7件）：ADD_N01_T01: no primary-route search; primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pa ／ ADD_N01_T02: no primary-route search; primary: ATTEMPTED_INSUFFICIENT (own queries 0/2, pa ／ ADD_N01_T03: no primary-route search; primary: NO (own queries 0/2, pages read 0); indepen ／ ADD_N01_T04: no primary-route search; primary: NO (own queries 0/2, pages read 0); indepen ／ ADD_N02_T01: no primary-route search; primary: NO (own queries 0/2, pages read 0); indepen ／ ADD_N03_T01: no primary-route search; primary: NO (own queries 0/2, pages read 0); indepen ／ ADD_SPD_T01: no primary-route search; primary: NO (own queries 0/2, pages read 0); indepen
- PASS：search log integrity (dated, unique ids, valid same-action references): 3416 rows
- PASS：every logged worker execution matches a call in the transcript-derived execution manifest (0 unmatched; manifest rows 3106)
- PASS：every accepted source was opened; sweep sources carry a quote found in the fetched page: 901 accepted
- PASS：no reference points to a source that is missing from the ledger: 0 dangling
- FAIL：coverage audit is current (EXECUTED_ACTIONS = 2620)
  - 次の要求アクション：regenerate research/COLLECTION_COVERAGE_AUDIT.md after the last merge

## S2 source_review_all：FAIL（0/5）

- FAIL：every accepted source reviewed: verified 0, pending 901
  - 次の要求アクション：run the source-review workers for the pending sources
  - 未達 400 件（先頭60件）：S001 ／ S002 ／ S003 ／ S004 ／ S005 ／ S006 ／ S007 ／ S008 ／ S009 ／ S010 ／ S011 ／ S012 ／ S013 ／ S014 ／ S015 ／ S016 ／ S017 ／ S018 ／ S019 ／ S020 ／ S021 ／ S022 ／ S023 ／ S024 ／ S025 ／ S026 ／ S027 ／ S028 ／ S029 ／ S030 ／ S031 ／ S032 ／ S033 ／ S034 ／ S035 ／ S036 ／ S037 ／ S038 ／ S039 ／ S040 ／ S041 ／ S042 ／ S043 ／ S044 ／ S045 ／ S046 ／ S047 ／ S048 ／ S049 ／ S050 ／ S051 ／ S052 ／ S053 ／ S054 ／ S055 ／ S056 ／ S057 ／ S058 ／ S059 ／ S060
- FAIL：verified sources carry quote, location, kind, origin and date: 0/0
- FAIL：every source-to-unit mapping reviewed: 0/2306
  - 未達 400 件（先頭60件）：M00001 ／ M00002 ／ M00003 ／ M00004 ／ M00005 ／ M00006 ／ M00007 ／ M00008 ／ M00009 ／ M00010 ／ M00011 ／ M00012 ／ M00013 ／ M00014 ／ M00015 ／ M00016 ／ M00017 ／ M00018 ／ M00019 ／ M00020 ／ M00021 ／ M00022 ／ M00023 ／ M00024 ／ M00025 ／ M00026 ／ M00027 ／ M00028 ／ M00029 ／ M00030 ／ M00031 ／ M00032 ／ M00033 ／ M00034 ／ M00035 ／ M00036 ／ M00037 ／ M00038 ／ M00039 ／ M00040 ／ M00041 ／ M00042 ／ M00043 ／ M00044 ／ M00045 ／ M00046 ／ M00047 ／ M00048 ／ M00049 ／ M00050 ／ M00051 ／ M00052 ／ M00053 ／ M00054 ／ M00055 ／ M00056 ／ M00057 ／ M00058 ／ M00059 ／ M00060
- FAIL：dependency ledger covers every verified source and the stated independent-origin count (None) equals the recomputation (0)
  - 次の要求アクション：rebuild registry/source_dependencies.csv and restate INDEPENDENT_ORIGINS in research/SOURCE_DEPENDENCY_AUDIT.md
- FAIL：contradictions reviewed for the current evidence set

## S3 representativeness_and_axis_model：FAIL（0/4）

- FAIL：representativeness graded for every measured source: 0/0
- FAIL：axis relation model covers all axes: 0/32
  - 未達 32 件（先頭32件）：AXIS_01 ／ AXIS_02 ／ AXIS_03 ／ AXIS_04 ／ AXIS_05 ／ AXIS_06 ／ AXIS_07 ／ AXIS_08 ／ AXIS_09 ／ AXIS_10 ／ AXIS_11 ／ AXIS_12 ／ AXIS_13 ／ AXIS_14 ／ AXIS_15 ／ AXIS_16 ／ AXIS_17 ／ AXIS_18 ／ AXIS_19 ／ AXIS_20 ／ AXIS_21 ／ AXIS_22 ／ AXIS_23 ／ AXIS_24 ／ AXIS_25 ／ AXIS_26 ／ AXIS_27 ／ AXIS_28 ／ AXIS_29 ／ AXIS_30 ／ AXIS_31 ／ AXIS_32
- FAIL：unidentifiable quantities are listed with reason and required data: 0
- FAIL：segment analysis rewritten on the verified evidence set

## S4 competitor_audit_all：FAIL（2/4）

- PASS：every candidate is classed comparable / not comparable with a reason: 80/80
- FAIL：every confirmed competitor attribute is backed by a verified source: 509 unbacked
  - 未達 400 件（先頭60件）：C001.data_handling ／ C001.features_processing ／ C001.fit_school_work ／ C001.free_alternative_strength ／ C001.io_formats ／ C001.official_site ／ C001.pricing_limits ／ C001.quality_claims ／ C001.source_verification ／ C001.speed_claims ／ C002.data_handling ／ C002.features_processing ／ C002.fit_school_work ／ C002.free_alternative_strength ／ C002.io_formats ／ C002.official_site ／ C002.pptx_editability ／ C002.pricing_limits ／ C002.quality_claims ／ C002.source_verification ／ C003.data_handling ／ C003.features_processing ／ C003.fit_school_work ／ C003.free_alternative_strength ／ C003.io_formats ／ C003.official_site ／ C003.pptx_editability ／ C003.pricing_limits ／ C003.quality_claims ／ C004.data_handling ／ C004.features_processing ／ C004.fit_school_work ／ C004.free_alternative_strength ／ C004.io_formats ／ C004.official_site ／ C004.pptx_editability ／ C004.pricing_limits ／ C004.quality_claims ／ C004.source_verification ／ C004.speed_claims ／ C005.data_handling ／ C005.features_processing ／ C005.fit_school_work ／ C005.free_alternative_strength ／ C005.io_formats ／ C005.official_site ／ C005.pptx_editability ／ C005.pricing_limits ／ C005.quality_claims ／ C005.source_verification ／ C005.speed_claims ／ C006.data_handling ／ C006.features_processing ／ C006.fit_school_work ／ C006.free_alternative_strength ／ C006.io_formats ／ C006.official_site ／ C006.pptx_editability ／ C006.pricing_limits ／ C006.quality_claims
- PASS：highest-priority candidates confirmed from vendor-written material: 21/21
- FAIL：competitor comparison rewritten on the verified evidence set

## S5 calculations_all：FAIL（1/5）

- PASS：every topic has at least one calculation id: 325/325
- FAIL：every calculation id is in a justified terminal state: 0/1023
  - 未達 400 件（先頭60件）：CALC_AXIS_01_T01_C00 ／ CALC_AXIS_01_T02_C00 ／ CALC_AXIS_01_T03_C00 ／ CALC_AXIS_01_T04_C00 ／ CALC_AXIS_01_T05_C00 ／ CALC_AXIS_01_T06_C00 ／ CALC_AXIS_01_T07_C00 ／ CALC_AXIS_01_T08_C00 ／ CALC_AXIS_02_T01_C01 ／ CALC_AXIS_02_T01_C02 ／ CALC_AXIS_02_T01_C03 ／ CALC_AXIS_02_T01_C04 ／ CALC_AXIS_02_T01_C05 ／ CALC_AXIS_02_T01_C06 ／ CALC_AXIS_02_T01_C07 ／ CALC_AXIS_02_T01_C08 ／ CALC_AXIS_02_T01_N01 ／ CALC_AXIS_02_T01_N02 ／ CALC_AXIS_02_T01_N03 ／ CALC_AXIS_02_T01_N04 ／ CALC_AXIS_02_T01_N05 ／ CALC_AXIS_02_T01_N06 ／ CALC_AXIS_02_T01_N07 ／ CALC_AXIS_02_T01_N08 ／ CALC_AXIS_02_T01_N09 ／ CALC_AXIS_02_T01_N10 ／ CALC_AXIS_02_T02_C01 ／ CALC_AXIS_02_T02_C02 ／ CALC_AXIS_02_T02_C03 ／ CALC_AXIS_02_T02_C04 ／ CALC_AXIS_02_T02_C05 ／ CALC_AXIS_02_T02_N01 ／ CALC_AXIS_02_T02_N02 ／ CALC_AXIS_02_T02_N03 ／ CALC_AXIS_02_T02_N04 ／ CALC_AXIS_02_T02_N05 ／ CALC_AXIS_02_T03_C01 ／ CALC_AXIS_02_T03_C02 ／ CALC_AXIS_02_T03_C03 ／ CALC_AXIS_02_T03_C04 ／ CALC_AXIS_02_T03_C05 ／ CALC_AXIS_02_T03_N01 ／ CALC_AXIS_02_T03_N02 ／ CALC_AXIS_02_T03_N03 ／ CALC_AXIS_02_T03_N04 ／ CALC_AXIS_02_T03_N05 ／ CALC_AXIS_02_T04_C01 ／ CALC_AXIS_02_T04_C02 ／ CALC_AXIS_02_T04_C03 ／ CALC_AXIS_02_T04_C04 ／ CALC_AXIS_02_T04_C05 ／ CALC_AXIS_02_T04_C06 ／ CALC_AXIS_02_T04_C07 ／ CALC_AXIS_02_T04_C08 ／ CALC_AXIS_02_T04_N01 ／ CALC_AXIS_02_T04_N02 ／ CALC_AXIS_02_T04_N03 ／ CALC_AXIS_02_T04_N04 ／ CALC_AXIS_02_T04_N05 ／ CALC_AXIS_02_T04_N06
- FAIL：reported numbers are classified and traceable to verified sources: 6/22
  - 未達 16 件（先頭16件）：QR01 ／ QR02 ／ QR03 ／ QR04 ／ QR05 ／ QR06 ／ QR07 ／ QR08 ／ QR09 ／ QR10 ／ QR11 ／ QR12 ／ QR13 ／ QR14 ／ QR15 ／ QR16
- FAIL：recalculation output matches the current calculation inventory
  - 次の要求アクション：python3 scripts/quant_recompute.py
- FAIL：quantitative report and reproducibility notes rewritten

## S6 cross_axis_integration：FAIL（0/2）

- FAIL：axis syntheses exist for every axis: 0/32
  - 未達 32 件（先頭32件）：AXIS_01 ／ AXIS_02 ／ AXIS_03 ／ AXIS_04 ／ AXIS_05 ／ AXIS_06 ／ AXIS_07 ／ AXIS_08 ／ AXIS_09 ／ AXIS_10 ／ AXIS_11 ／ AXIS_12 ／ AXIS_13 ／ AXIS_14 ／ AXIS_15 ／ AXIS_16 ／ AXIS_17 ／ AXIS_18 ／ AXIS_19 ／ AXIS_20 ／ AXIS_21 ／ AXIS_22 ／ AXIS_23 ／ AXIS_24 ／ AXIS_25 ／ AXIS_26 ／ AXIS_27 ／ AXIS_28 ／ AXIS_29 ／ AXIS_30 ／ AXIS_31 ／ AXIS_32
- FAIL：integrated model refers to every axis

## S7 options_A_to_G：FAIL（0/2）

- FAIL：options A-G and the added hypotheses compared on the verified evidence set
- FAIL：decision analysis is conditional, covers downside and regret, and cites only verified sources
  - 未達 20 件（先頭20件）：S003 ／ S004 ／ S012 ／ S015 ／ S018 ／ S020 ／ S025 ／ S031 ／ S034 ／ S035 ／ S036 ／ S040 ／ S041 ／ S044 ／ S046 ／ S047 ／ S048 ／ S049 ／ S050 ／ S053

## S8 coverage_audit：FAIL（0/3）

- FAIL：final audit records that no application code was changed
- FAIL：every user requirement and added hypothesis is traced to evidence or to a stated unknown: 0/20
  - 未達 20 件（先頭20件）：N01 ／ N02 ／ N03 ／ R01 ／ R02 ／ R03 ／ R04 ／ R05 ／ R06 ／ R07 ／ R08 ／ R09 ／ R10 ／ R11 ／ R12 ／ R13 ／ R14 ／ R15 ／ R16 ／ R17
- FAIL：product claims cite only verified sources: 0/12
  - 未達 12 件（先頭12件）：PC01 ／ PC02 ／ PC03 ／ PC04 ／ PC05 ／ PC06 ／ PC07 ／ PC08 ／ PC09 ／ PC10 ／ PC11 ／ PC12

## S9 formal_deliverables：FAIL（1/3）

- FAIL：formal deliverables present: 0/5
- FAIL：final report cites verified sources and covers the fixed requirements
- PASS：no formal deliverable exists before S0-S8 pass

機械検査は、文書や台帳の整合を確かめるだけで、出典の真偽や標本の代表性を保証しない。
