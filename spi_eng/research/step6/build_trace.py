import csv, os, json
H = os.path.dirname(os.path.abspath(__file__))
rows = [
 ["η1(GS当日の英語)の分布", "step4/results.json(model.py)", "口コミの題数データ(8独立単位) + STEP3の主張の統合", "実データ+仮定"],
 ["評価制度の仮説の確率 H1〜H4", "step5/hypotheses.json(r_scale=1.0,rho=0.9)", json.dumps(json.load(open(os.path.join(H, "results.json"), encoding="utf-8"))["hyp_weights_used"], ensure_ascii=False), "実データ(公式FAQ・体験談・主張)+仮定(信頼性)"],
 ["基礎能力 上位25%以内", "本人申告", "順位で一様", "本人申告の条件"],
 ["再受検の効果 g2,g3", "仮定", "なし/小/中/疲労", "仮定(SPI英語の実測なし)"],
 ["ENGの信頼性 r", "仮定", "0.8/0.9", "仮定"],
 ["評価制度の具体化(足切り位置・重み)", "仮定", "H2:5,10% H3:20,35% H4:w=0.05,0.10", "仮定"],
 ["応募者集団 μ・通過率 π", "仮定", "μ=0,0.5 π=0.3,0.5", "仮定(INPEXの実数は非公開)"],
 ["Eの手応えの精度", "仮定", "誤差SD 0.5/1.0", "仮定"],
 ["送信は最新の結果のみ", "公式FAQの内容を引用した二次情報・知恵袋CB11の回答「常に上書き」", "最高点の選択は不可", "制度上の制約"],
]
with open(os.path.join(H, "trace.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["input", "source", "value", "type"]); w.writerows(rows)
print(len(rows))
