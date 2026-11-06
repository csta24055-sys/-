#!/usr/bin/env python3
"""SPI英語 診断・演習の採点と記録。

使い方:
  python3 grade.py diag1 "A1=2o A2=1o A3=3d ..." --times "VOC=60,SYN=50,..."
  確信度: o=確信 / d=半信半疑 / g=勘   （省略時は d 扱い）

記録先: data/results.csv（1行=1問）, data/sessions.csv（1行=1回）
"""
import argparse, base64, csv, datetime, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# SPI英語の推定出題比重（形式ごとの出現しやすさ×1問あたり得点への寄与）。
# 公式非公開のため、対策本・体験談からの推定値。実戦(11/8)後に更新する。
EST_WEIGHT = {"VOC": 0.10, "SYN": 0.15, "ANT": 0.12, "DEF": 0.13,
              "GRM": 0.15, "ERR": 0.10, "RDG": 0.25}
# 4日間での伸びやすさ（暗記で上がる系は高い、読解は低い）推定
EST_TRAINABLE = {"VOC": 1.0, "SYN": 0.9, "ANT": 0.9, "DEF": 0.8,
                 "GRM": 0.7, "ERR": 0.5, "RDG": 0.3}


def load(test_id):
    bank = json.load(open(os.path.join(HERE, f"bank_{test_id}.json"), encoding="utf-8"))
    key = json.loads(base64.b64decode(open(os.path.join(HERE, f"key_{test_id}.b64")).read()))
    return bank, key


def parse_answers(s):
    out = {}
    for tok in re.split(r"[\s,]+", s.strip()):
        if not tok:
            continue
        m = re.fullmatch(r"([A-Za-z]\d+)=([1-5A-Ea-e?])([odg]?)", tok)
        if not m:
            sys.exit(f"解答の書式エラー: {tok}  (例: A1=2o)")
        out[m.group(1).upper()] = (m.group(2).upper(), m.group(3) or "d")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("test_id")
    ap.add_argument("answers")
    ap.add_argument("--times", default="", help="カテゴリ別所要秒 VOC=60,SYN=40")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    bank, key = load(a.test_id)
    ans = parse_answers(a.answers)
    times = dict(kv.split("=") for kv in a.times.split(",") if "=" in kv)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    os.makedirs(DATA, exist_ok=True)

    stats = defaultdict(lambda: {"n": 0, "ok": 0, "solid": 0, "lucky": 0, "wrong_sure": 0})
    rows, wrong = [], []
    for it in bank["items"]:
        iid, cat = it["id"], it["cat"]
        correct, expl = key[iid]
        given, conf = ans.get(iid, ("?", "g"))
        ok = given == correct
        s = stats[cat]
        s["n"] += 1
        s["ok"] += ok
        s["solid"] += ok and conf in "od"         # 実力での正解
        s["lucky"] += ok and conf == "g"           # 偶然の正解
        s["wrong_sure"] += (not ok) and conf == "o"  # 思い込み誤答（危険）
        rows.append([now, a.test_id, iid, cat, it["level"], given, correct, int(ok), conf])
        if not ok or conf == "g":
            wrong.append((iid, cat, given, correct, conf, expl))

    path = os.path.join(DATA, "results.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "test", "item", "cat", "level", "given", "correct", "ok", "conf"])
        w.writerows(rows)

    total = sum(s["n"] for s in stats.values())
    ok = sum(s["ok"] for s in stats.values())
    solid = sum(s["solid"] for s in stats.values())
    print(f"=== {bank['title']}  {now} ===")
    print(f"正答 {ok}/{total} ({ok/total:.0%})   実力正答（勘を除く） {solid}/{total} ({solid/total:.0%})\n")
    print(f"{'分野':<14}{'正答':>6}{'実力':>6}{'偶然':>6}{'確信誤答':>8}{'秒':>6}  優先度")
    prio = []
    for cat, name in bank["categories"].items():
        s = stats[cat]
        if not s["n"]:
            continue
        acc = s["solid"] / s["n"]
        p = (1 - acc) * EST_WEIGHT[cat] * EST_TRAINABLE[cat]
        prio.append((p, cat, name))
        print(f"{name:<14}{s['ok']:>4}/{s['n']}{s['solid']:>5}{s['lucky']:>6}{s['wrong_sure']:>8}"
              f"{times.get(cat, '-'):>6}  {p:.3f}")
    print("\n伸ばす優先順位（失点×出題比重×4日での伸びやすさ・推定）:")
    for i, (p, cat, name) in enumerate(sorted(prio, reverse=True), 1):
        print(f"  {i}. {name} ({p:.3f})")
    print("\n要復習（誤答・勘）:")
    for iid, cat, g, c, conf, expl in wrong:
        print(f"  {iid} [{cat}] あなた={g}({conf}) 正解={c}  … {expl}")

    spath = os.path.join(DATA, "sessions.csv")
    new = not os.path.exists(spath)
    with open(spath, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "test", "n", "ok", "solid", "times", "note"])
        w.writerow([now, a.test_id, total, ok, solid, a.times, a.note])


if __name__ == "__main__":
    main()
