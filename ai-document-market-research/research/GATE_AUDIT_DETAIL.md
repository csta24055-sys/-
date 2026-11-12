# ゲート監査の詳細（機械生成）

生成時刻（UTC）：2026-11-12T14:43:54.150819+00:00

RESEARCH_STATUS = INCOMPLETE
最初に未達の工程：S1

- 実行した検索・アクセス：772
- 採用資料：152（うちS2精査済み 0、独立起源 0）
- テーマ（S1完了）：16
- 旧検索候補：{"NOT_EXECUTED": 848, "EXECUTED": 48}
- 競合候補（S1完了）：4、公式確認 19
- 計算ID：0

## 外部要因による未達

- 2 highest-priority competitors lack vendor-written confirmation

## S0 reaudit_and_scope_lock：PASS（13/13）

- PASS：scope lock: 325 topics / 32 axes (required 325 / 32)
- PASS：legacy query candidates: 896 (required 896)
- PASS：search plans cover every topic: 325
- PASS：competitor candidates: 80 (required 80)
- PASS：all original topics and candidates are preserved
- PASS：user reference images present and unmodified: 8/8
- PASS：manifest forbids app implementation
- PASS：ten stage records in research_status.json
- PASS：repository / environment re-audit recorded for this continuation
- PASS：status ledgers have a fixed row for every id: queries 896, topics 325, competitors 80
- PASS：status ledgers equal the recomputation from the primary ledgers (not hand-edited, not stale)
- PASS：full-scope execution plan exists
- PASS：earlier provisional deliverables are quarantined with a banner: 5

## S1 collection_all_topics_queries_competitors：FAIL（3/8）

- FAIL：topics with a complete research-unit collection: 16/325
  - 次の要求アクション：run the topic worker for the listed topics (legacy queries verbatim, primary / independent / counter routes, unit record)
  - 未達 309 件（先頭60件）：AXIS_01_T01: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_01_T02: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_01_T03: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_01_T04: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_01_T05: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_01_T06: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_01_T07: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_01_T08: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_03_T01: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_03_T02: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_03_T03: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_03_T04: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_03_T05: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_03_T06: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_03_T07: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_03_T08: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_04_T03: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_04_T04: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_04_T05: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_04_T06: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_04_T07: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_04_T08: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_05_T02: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_05_T03: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_05_T04: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_05_T05: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_05_T06: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_05_T07: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_05_T08: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_06_T01: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_06_T02: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_06_T03: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_06_T04: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_06_T05: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_06_T06: legacy queries not executed: 4; independent: ATTEMPTED_INSUFFICIENT; counter: ／ AXIS_06_T07: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_06_T08: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_07_T01: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_07_T02: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_07_T03: legacy queries not executed: 4; independent: ATTEMPTED_INSUFFICIENT; counter: ／ AXIS_07_T04: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_07_T05: legacy queries not executed: 4; no primary-route search; primary: ATTEMPTED_I ／ AXIS_07_T06: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_07_T07: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_07_T08: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_08_T01: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_08_T02: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_08_T03: legacy queries not executed: 4; independent: ATTEMPTED_INSUFFICIENT; counter: ／ AXIS_08_T04: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_08_T05: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_08_T06: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_08_T07: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_08_T08: legacy queries not executed: 4; no primary-route search; primary: NO; indepen ／ AXIS_09_T01: legacy queries not executed: 4; independent: ATTEMPTED_INSUFFICIENT; counter: ／ AXIS_09_T02: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_09_T03: legacy queries not executed: 4; no primary-route search; independent: ATTEMPT ／ AXIS_09_T04: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_09_T05: legacy queries not executed: 4; no primary-route search; independent: NO; cou ／ AXIS_09_T06: legacy queries not executed: 4; independent: NO; counter: NO; research unit r ／ AXIS_09_T07: legacy queries not executed: 4; no primary-route search; independent: NO; cou
- FAIL：legacy queries handled: executed 48, attempted-but-blocked 0, not executed 848 (of 896)
  - 次の要求アクション：execute each listed legacy query verbatim once
  - 未達 400 件（先頭60件）：AXIS_01_T01_Q1 ／ AXIS_01_T01_Q2 ／ AXIS_01_T01_Q3 ／ AXIS_01_T01_Q4 ／ AXIS_01_T02_Q1 ／ AXIS_01_T02_Q2 ／ AXIS_01_T02_Q3 ／ AXIS_01_T02_Q4 ／ AXIS_01_T03_Q1 ／ AXIS_01_T03_Q2 ／ AXIS_01_T03_Q3 ／ AXIS_01_T03_Q4 ／ AXIS_01_T04_Q1 ／ AXIS_01_T04_Q2 ／ AXIS_01_T04_Q3 ／ AXIS_01_T04_Q4 ／ AXIS_01_T05_Q1 ／ AXIS_01_T05_Q2 ／ AXIS_01_T05_Q3 ／ AXIS_01_T05_Q4 ／ AXIS_01_T06_Q1 ／ AXIS_01_T06_Q2 ／ AXIS_01_T06_Q3 ／ AXIS_01_T06_Q4 ／ AXIS_01_T07_Q1 ／ AXIS_01_T07_Q2 ／ AXIS_01_T07_Q3 ／ AXIS_01_T07_Q4 ／ AXIS_01_T08_Q1 ／ AXIS_01_T08_Q2 ／ AXIS_01_T08_Q3 ／ AXIS_01_T08_Q4 ／ AXIS_03_T01_Q1 ／ AXIS_03_T01_Q2 ／ AXIS_03_T01_Q3 ／ AXIS_03_T01_Q4 ／ AXIS_03_T02_Q1 ／ AXIS_03_T02_Q2 ／ AXIS_03_T02_Q3 ／ AXIS_03_T02_Q4 ／ AXIS_03_T03_Q1 ／ AXIS_03_T03_Q2 ／ AXIS_03_T03_Q3 ／ AXIS_03_T03_Q4 ／ AXIS_03_T04_Q1 ／ AXIS_03_T04_Q2 ／ AXIS_03_T04_Q3 ／ AXIS_03_T04_Q4 ／ AXIS_03_T05_Q1 ／ AXIS_03_T05_Q2 ／ AXIS_03_T05_Q3 ／ AXIS_03_T05_Q4 ／ AXIS_03_T06_Q1 ／ AXIS_03_T06_Q2 ／ AXIS_03_T06_Q3 ／ AXIS_03_T06_Q4 ／ AXIS_03_T07_Q1 ／ AXIS_03_T07_Q2 ／ AXIS_03_T07_Q3 ／ AXIS_03_T07_Q4
- FAIL：competitor candidates explored: 4/80
  - 次の要求アクション：run the competitor worker for the listed candidates
  - 未達 76 件（先頭60件）：C005 Gemini Notebook / NotebookLM: attributes not recorded: official_site,features_process ／ C006 Genspark AI Slides: attributes not recorded: official_site,features_processing,pricin ／ C007 Canva: attributes not recorded: official_site,features_processing,pricing_limits,io_f ／ C008 Beautiful.ai: attributes not recorded: official_site,features_processing,pricing_limi ／ C009 Plus AI: no official-site attempt recorded; attributes not recorded: official_site,fe ／ C010 SlidesAI: no official-site attempt recorded; attributes not recorded: official_site,f ／ C011 ChatGPT: no official-site attempt recorded; attributes not recorded: official_site,fe ／ C012 Claude: no official-site attempt recorded; attributes not recorded: official_site,fea ／ C013 Gemini: no official-site attempt recorded; attributes not recorded: official_site,fea ／ C014 Perplexity: no official-site attempt recorded; attributes not recorded: official_site ／ C015 Google Slides without AI: no official-site attempt recorded; attributes not recorded: ／ C016 PowerPoint without AI: no official-site attempt recorded; attributes not recorded: of ／ C017 Pitch: no official-site attempt recorded; attributes not recorded: official_site,feat ／ C018 Prezi AI: no official-site attempt recorded; attributes not recorded: official_site,f ／ C019 Decktopus: no official-site attempt recorded; attributes not recorded: official_site, ／ C020 Presentations.AI: no official-site attempt recorded; attributes not recorded: officia ／ C021 Slidesgo AI Presentation Maker: no official-site attempt recorded; attributes not rec ／ C022 MagicSlides: no official-site attempt recorded; attributes not recorded: official_sit ／ C023 SlideSpeak: no official-site attempt recorded; attributes not recorded: official_site ／ C024 Alai: no official-site attempt recorded; attributes not recorded: official_site,featu ／ C025 Chronicle: no official-site attempt recorded; attributes not recorded: official_site, ／ C026 Felo AI Slides: no official-site attempt recorded; attributes not recorded: official_ ／ C027 イルシル: no official-site attempt recorded; attributes not recorded: official_site,featu ／ C028 MiriCanvas AI Presentation: no official-site attempt recorded; attributes not recorde ／ C029 PageOn.ai: no official-site attempt recorded; attributes not recorded: official_site, ／ C030 Slidebean: no official-site attempt recorded; attributes not recorded: official_site, ／ C031 Adobe Express: no official-site attempt recorded; attributes not recorded: official_s ／ C032 Visme: no official-site attempt recorded; attributes not recorded: official_site,feat ／ C033 Zoho Show Zia: no official-site attempt recorded; attributes not recorded: official_s ／ C034 WPS AI Presentation: no official-site attempt recorded; attributes not recorded: offi ／ C035 Figma Slides: no official-site attempt recorded; attributes not recorded: official_si ／ C036 ChatPDF: no official-site attempt recorded; attributes not recorded: official_site,fe ／ C037 AskYourPDF: no official-site attempt recorded; attributes not recorded: official_site ／ C038 PDF.ai: no official-site attempt recorded; attributes not recorded: official_site,fea ／ C039 Humata: no official-site attempt recorded; attributes not recorded: official_site,fea ／ C040 UPDF AI: no official-site attempt recorded; attributes not recorded: official_site,fe ／ C041 Foxit PDF AI: no official-site attempt recorded; attributes not recorded: official_si ／ C042 Smallpdf AI PDF: no official-site attempt recorded; attributes not recorded: official ／ C043 PDFelement AI: no official-site attempt recorded; attributes not recorded: official_s ／ C044 SciSpace: no official-site attempt recorded; attributes not recorded: official_site,f ／ C045 Elicit: no official-site attempt recorded; attributes not recorded: official_site,fea ／ C046 Consensus: no official-site attempt recorded; attributes not recorded: official_site, ／ C047 Scholarcy: no official-site attempt recorded; attributes not recorded: official_site, ／ C048 Jenni AI: no official-site attempt recorded; attributes not recorded: official_site,f ／ C049 Paperpal: no official-site attempt recorded; attributes not recorded: official_site,f ／ C050 scite: no official-site attempt recorded; attributes not recorded: official_site,feat ／ C051 Microsoft Copilot Chat: no official-site attempt recorded; attributes not recorded: o ／ C052 Kimi AI: no official-site attempt recorded; attributes not recorded: official_site,fe ／ C053 Notion AI: no official-site attempt recorded; attributes not recorded: official_site, ／ C054 Coda AI: no official-site attempt recorded; attributes not recorded: official_site,fe ／ C055 Jasper: no official-site attempt recorded; attributes not recorded: official_site,fea ／ C056 Grammarly: no official-site attempt recorded; attributes not recorded: official_site, ／ C057 Glean: no official-site attempt recorded; attributes not recorded: official_site,feat ／ C058 StudyFetch: no official-site attempt recorded; attributes not recorded: official_site ／ C059 Knowt: no official-site attempt recorded; attributes not recorded: official_site,feat ／ C060 Quizlet AI: no official-site attempt recorded; attributes not recorded: official_site ／ C061 Mindgrasp: no official-site attempt recorded; attributes not recorded: official_site, ／ C062 LibreOffice Impress: no official-site attempt recorded; attributes not recorded: offi ／ C063 Zapier AI Workflows: no official-site attempt recorded; attributes not recorded: offi ／ C064 n8n Workflows: no official-site attempt recorded; attributes not recorded: official_s
- FAIL：additional-hypothesis topics (outside the 325) explored: 0/7
  - 次の要求アクション：run the topic worker for the listed additional topics
  - 未達 7 件（先頭7件）：ADD_N01_T01: no primary-route search; primary: ATTEMPTED_INSUFFICIENT; independent: ATTEMP ／ ADD_N01_T02: no primary-route search; primary: ATTEMPTED_INSUFFICIENT; independent: ATTEMP ／ ADD_N01_T03: no primary-route search; primary: NO; independent: NO; counter: NO; research  ／ ADD_N01_T04: no primary-route search; primary: NO; independent: NO; counter: NO; research  ／ ADD_N02_T01: no primary-route search; primary: NO; independent: NO; counter: NO; research  ／ ADD_N03_T01: no primary-route search; primary: NO; independent: NO; counter: NO; research  ／ ADD_SPD_T01: no primary-route search; primary: NO; independent: NO; counter: NO; research 
- PASS：search log integrity (dated, unique ids, valid same-action references): 988 rows
- PASS：every accepted source was opened; sweep sources carry a quote found in the fetched page: 152 accepted
- PASS：no reference points to a source that is missing from the ledger: 0 dangling
- FAIL：coverage audit is current (EXECUTED_ACTIONS = 772)
  - 次の要求アクション：regenerate research/COLLECTION_COVERAGE_AUDIT.md after the last merge

## S2 source_review_all：FAIL（0/5）

- FAIL：every accepted source reviewed: verified 0, pending 152
  - 次の要求アクション：run the source-review workers for the pending sources
  - 未達 152 件（先頭60件）：S001 ／ S002 ／ S003 ／ S004 ／ S005 ／ S006 ／ S007 ／ S008 ／ S009 ／ S010 ／ S011 ／ S012 ／ S013 ／ S014 ／ S015 ／ S016 ／ S017 ／ S018 ／ S019 ／ S020 ／ S021 ／ S022 ／ S023 ／ S024 ／ S025 ／ S026 ／ S027 ／ S028 ／ S029 ／ S030 ／ S031 ／ S032 ／ S033 ／ S034 ／ S035 ／ S036 ／ S037 ／ S038 ／ S039 ／ S040 ／ S041 ／ S042 ／ S043 ／ S044 ／ S045 ／ S046 ／ S047 ／ S048 ／ S049 ／ S050 ／ S051 ／ S052 ／ S053 ／ S054 ／ S055 ／ S056 ／ S057 ／ S058 ／ S059 ／ S060
- FAIL：verified sources carry quote, location, kind, origin and date: 0/0
- FAIL：every source-to-unit mapping reviewed: 0/395
  - 未達 395 件（先頭60件）：M00001 ／ M00002 ／ M00003 ／ M00004 ／ M00005 ／ M00006 ／ M00007 ／ M00008 ／ M00009 ／ M00010 ／ M00011 ／ M00012 ／ M00013 ／ M00014 ／ M00015 ／ M00016 ／ M00017 ／ M00018 ／ M00019 ／ M00020 ／ M00021 ／ M00022 ／ M00023 ／ M00024 ／ M00025 ／ M00026 ／ M00027 ／ M00028 ／ M00029 ／ M00030 ／ M00031 ／ M00032 ／ M00033 ／ M00034 ／ M00035 ／ M00036 ／ M00037 ／ M00038 ／ M00039 ／ M00040 ／ M00041 ／ M00042 ／ M00043 ／ M00044 ／ M00045 ／ M00046 ／ M00047 ／ M00048 ／ M00049 ／ M00050 ／ M00051 ／ M00052 ／ M00053 ／ M00054 ／ M00055 ／ M00056 ／ M00057 ／ M00058 ／ M00059 ／ M00060
- FAIL：dependency ledger covers every verified source and the stated independent-origin count (None) equals the recomputation (0)
  - 次の要求アクション：rebuild registry/source_dependencies.csv and restate INDEPENDENT_ORIGINS in research/SOURCE_DEPENDENCY_AUDIT.md
- FAIL：contradictions reviewed for the current evidence set

## S3 representativeness_and_axis_model：FAIL（0/4）

- FAIL：representativeness graded for every measured source: 0/0
- FAIL：axis relation model covers all axes: 0/32
  - 未達 32 件（先頭32件）：AXIS_01 ／ AXIS_02 ／ AXIS_03 ／ AXIS_04 ／ AXIS_05 ／ AXIS_06 ／ AXIS_07 ／ AXIS_08 ／ AXIS_09 ／ AXIS_10 ／ AXIS_11 ／ AXIS_12 ／ AXIS_13 ／ AXIS_14 ／ AXIS_15 ／ AXIS_16 ／ AXIS_17 ／ AXIS_18 ／ AXIS_19 ／ AXIS_20 ／ AXIS_21 ／ AXIS_22 ／ AXIS_23 ／ AXIS_24 ／ AXIS_25 ／ AXIS_26 ／ AXIS_27 ／ AXIS_28 ／ AXIS_29 ／ AXIS_30 ／ AXIS_31 ／ AXIS_32
- FAIL：unidentifiable quantities are listed with reason and required data: 0
- FAIL：segment analysis rewritten on the verified evidence set

## S4 competitor_audit_all：FAIL（1/4）

- PASS：every candidate is classed comparable / not comparable with a reason: 80/80
- FAIL：every confirmed competitor attribute is backed by a verified source: 40 unbacked
  - 未達 40 件（先頭40件）：C001.data_handling ／ C001.features_processing ／ C001.fit_school_work ／ C001.free_alternative_strength ／ C001.io_formats ／ C001.official_site ／ C001.pricing_limits ／ C001.quality_claims ／ C001.source_verification ／ C001.speed_claims ／ C002.data_handling ／ C002.features_processing ／ C002.fit_school_work ／ C002.free_alternative_strength ／ C002.io_formats ／ C002.official_site ／ C002.pptx_editability ／ C002.pricing_limits ／ C002.quality_claims ／ C002.source_verification ／ C003.data_handling ／ C003.features_processing ／ C003.fit_school_work ／ C003.free_alternative_strength ／ C003.io_formats ／ C003.official_site ／ C003.pptx_editability ／ C003.pricing_limits ／ C003.quality_claims ／ C004.data_handling ／ C004.features_processing ／ C004.fit_school_work ／ C004.free_alternative_strength ／ C004.io_formats ／ C004.official_site ／ C004.pptx_editability ／ C004.pricing_limits ／ C004.quality_claims ／ C004.source_verification ／ C004.speed_claims
- FAIL：highest-priority candidates confirmed from vendor-written material: 19/21
  - 次の要求アクション：obtain a vendor-written page for the listed candidates or keep the study BLOCKED for them
  - 未達 2 件（先頭2件）：C007 Canva ／ C011 ChatGPT
- FAIL：competitor comparison rewritten on the verified evidence set

## S5 calculations_all：FAIL（0/5）

- FAIL：every topic has at least one calculation id: 0/325
  - 未達 325 件（先頭60件）：AXIS_01_T01 ／ AXIS_01_T02 ／ AXIS_01_T03 ／ AXIS_01_T04 ／ AXIS_01_T05 ／ AXIS_01_T06 ／ AXIS_01_T07 ／ AXIS_01_T08 ／ AXIS_02_T01 ／ AXIS_02_T02 ／ AXIS_02_T03 ／ AXIS_02_T04 ／ AXIS_02_T05 ／ AXIS_02_T06 ／ AXIS_02_T07 ／ AXIS_02_T08 ／ AXIS_03_T01 ／ AXIS_03_T02 ／ AXIS_03_T03 ／ AXIS_03_T04 ／ AXIS_03_T05 ／ AXIS_03_T06 ／ AXIS_03_T07 ／ AXIS_03_T08 ／ AXIS_04_T01 ／ AXIS_04_T02 ／ AXIS_04_T03 ／ AXIS_04_T04 ／ AXIS_04_T05 ／ AXIS_04_T06 ／ AXIS_04_T07 ／ AXIS_04_T08 ／ AXIS_05_T01 ／ AXIS_05_T02 ／ AXIS_05_T03 ／ AXIS_05_T04 ／ AXIS_05_T05 ／ AXIS_05_T06 ／ AXIS_05_T07 ／ AXIS_05_T08 ／ AXIS_06_T01 ／ AXIS_06_T02 ／ AXIS_06_T03 ／ AXIS_06_T04 ／ AXIS_06_T05 ／ AXIS_06_T06 ／ AXIS_06_T07 ／ AXIS_06_T08 ／ AXIS_07_T01 ／ AXIS_07_T02 ／ AXIS_07_T03 ／ AXIS_07_T04 ／ AXIS_07_T05 ／ AXIS_07_T06 ／ AXIS_07_T07 ／ AXIS_07_T08 ／ AXIS_08_T01 ／ AXIS_08_T02 ／ AXIS_08_T03 ／ AXIS_08_T04
- FAIL：every calculation id is in a justified terminal state: 0/0
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
