#!/usr/bin/env python3
"""多軸評価・パレート分析・感度分析・ルート期待値の再現可能なモデル。

使い方:
  python3 tools/strategy_model.py --catalog data/options_catalog.csv \
      [--overlay PERSONAL_OVERLAY.csv] [--routes ROUTES.csv] --out OUTDIR

- catalog: 選択肢ごとの客観寄りの評価軸（1〜5）。公開可能。
- overlay: 個人適合(fit)・到達可能性(reach_now/reach_prep)・失敗時の損失の小ささ(downside)。個人資料のため公開リポジトリに置かない。
- routes : 複合ルート（primary/fallback と成功確率の範囲）。個人資料。
注意: 点数は分析者の主観評価であり、採用確率ではない。成功確率の範囲も根拠を示した主観確率である。
"""
import argparse, csv, json, os, random, statistics

AXES = ["pay", "stability", "worklife", "scale", "expertise", "autonomy", "prestige", "mobility", "freedom"]
PERSONAL = ["fit", "reach_now", "reach_prep", "downside"]

# 指令Ⅻの14の評価体系。重みは相対値（合計で正規化）。
VALUE_SYSTEMS = {
    "V01_生涯収入": {"pay": 5, "stability": 1, "mobility": 1},
    "V02_現時点の採用現実性": {"reach_now": 5, "fit": 1},
    "V03_社会的影響力": {"scale": 5, "prestige": 1, "fit": 1},
    "V04_規模・知名度": {"prestige": 4, "scale": 3},
    "V05_専門性・技術的成長": {"expertise": 5, "mobility": 1, "fit": 1},
    "V06_昇進・経営参加": {"autonomy": 3, "scale": 2, "prestige": 2, "pay": 1},
    "V07_本人の興味・行動特性": {"fit": 5, "worklife": 1},
    "V08_安定性・福利厚生": {"stability": 5, "worklife": 2, "pay": 1},
    "V09_自由時間・働き方": {"worklife": 5, "stability": 1},
    "V10_転職・進路変更の自由度": {"mobility": 4, "freedom": 2, "expertise": 2},
    "V11_時間・費用の効率": {"reach_now": 3, "reach_prep": 1, "downside": 2, "pay": 1},
    "V12_失敗時の損失最小": {"downside": 5, "reach_now": 2, "stability": 2},
    "V13_到達可能な上限": {"pay": 2, "scale": 2, "prestige": 2, "reach_prep": 2, "fit": 1},
    "V14_総合（均衡）": {"pay": 2, "stability": 2, "worklife": 2, "scale": 2, "expertise": 1, "autonomy": 1,
                       "prestige": 1, "mobility": 1, "freedom": 1, "fit": 3, "reach_prep": 2, "downside": 1},
}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(catalog, overlay):
    rows = {r["id"]: r for r in csv.DictReader(open(catalog, encoding="utf-8"))}
    if overlay and os.path.exists(overlay):
        for r in csv.DictReader(open(overlay, encoding="utf-8")):
            if r["id"] in rows:
                rows[r["id"]].update({k: r[k] for k in PERSONAL})
    opts = {}
    for k, r in rows.items():
        v = {a: num(r.get(a)) for a in AXES + PERSONAL}
        if v["pay"] is None:  # 進学など「手段」の行は評価対象から除く
            continue
        opts[k] = {"name": f'{r["organization"]}／{r["role_or_track"]}', "v": v}
    return opts


def score(v, w):
    tot = sum(x for a, x in w.items() if v.get(a) is not None)
    if tot == 0:
        return None
    return sum(v[a] * x for a, x in w.items() if v.get(a) is not None) / tot


def pareto(opts, axes):
    ids = [k for k in opts if all(opts[k]["v"].get(a) is not None for a in axes)]
    front = []
    for i in ids:
        dominated = False
        for j in ids:
            if i == j:
                continue
            a, b = opts[i]["v"], opts[j]["v"]
            if all(b[x] >= a[x] for x in axes) and any(b[x] > a[x] for x in axes):
                dominated = True
                break
        if not dominated:
            front.append(i)
    return front


def sensitivity(opts, base, n=4000, conc=8.0, seed=20261101):
    """基準重みの周りでディリクレ摂動を与え、上位5位に入る頻度と順位の中央値を求める。"""
    rnd = random.Random(seed)
    keys = list(base)
    tot = sum(base.values())
    ranks = {k: [] for k in opts}
    top5 = {k: 0 for k in opts}
    for _ in range(n):
        g = [rnd.gammavariate(conc * base[k] / tot + 1e-3, 1) for k in keys]
        s = sum(g)
        w = {k: g[i] / s for i, k in enumerate(keys)}
        sc = sorted(((score(o["v"], w) or 0, k) for k, o in opts.items()), reverse=True)
        for r, (_, k) in enumerate(sc, 1):
            ranks[k].append(r)
            if r <= 5:
                top5[k] += 1
    return {k: (top5[k] / n, statistics.median(ranks[k])) for k in opts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--overlay")
    ap.add_argument("--routes")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    opts = load(a.catalog, a.overlay)
    personal = a.overlay and os.path.exists(a.overlay)
    # 公開モードでは、個人軸の重みが半分以上を占める評価体系を除外し、残りは客観寄りの軸だけで評価する
    systems = VALUE_SYSTEMS if personal else {
        k: {x: y for x, y in w.items() if x in AXES} for k, w in VALUE_SYSTEMS.items()
        if sum(y for x, y in w.items() if x in PERSONAL) * 2 < sum(w.values())}
    systems = {k: w for k, w in systems.items() if w}

    # 1) 評価体系別の順位
    table = []
    for sname, w in systems.items():
        sc = sorted(((score(o["v"], w), k) for k, o in opts.items() if score(o["v"], w) is not None), reverse=True)
        for r, (s, k) in enumerate(sc, 1):
            table.append({"system": sname, "rank": r, "id": k, "name": opts[k]["name"], "score": round(s, 3)})
    with open(os.path.join(a.out, "rankings_by_value_system.csv"), "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["system", "rank", "id", "name", "score"]); wr.writeheader(); wr.writerows(table)

    # 2) パレート分析
    pa = ["pay", "stability", "worklife", "scale"] + (["fit", "reach_prep"] if personal else ["expertise"])
    front = pareto(opts, pa)
    with open(os.path.join(a.out, "pareto_front.json"), "w", encoding="utf-8") as f:
        json.dump({"axes": pa, "front": {k: opts[k]["name"] for k in front}}, f, ensure_ascii=False, indent=1)

    # 3) 感度分析（総合の重みの周り）
    sens = sensitivity(opts, systems["V14_総合（均衡）"])
    with open(os.path.join(a.out, "sensitivity_balanced.csv"), "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f); wr.writerow(["id", "name", "top5_frequency", "median_rank"])
        for k, (p, m) in sorted(sens.items(), key=lambda x: -x[1][0]):
            wr.writerow([k, opts[k]["name"], round(p, 3), m])

    # 4) ルートの期待値・最悪値・後悔（総合スコアを効用とみなす）
    if a.routes and os.path.exists(a.routes):
        U = {k: score(o["v"], systems["V14_総合（均衡）"]) for k, o in opts.items()}
        best = max(U.values())
        out = []
        for r in csv.DictReader(open(a.routes, encoding="utf-8")):
            pl, ph = num(r["p_low"]), num(r["p_high"])
            up, uf = U.get(r["primary_target"]), U.get(r["fallback_target"])
            if pl is None or up is None or uf is None:
                continue
            pm = (pl + ph) / 2
            ev = pm * up + (1 - pm) * uf
            out.append({"route_id": r["route_id"], "type": r["strategy_type"], "status": r["status"],
                        "p_mid": round(pm, 2), "U_primary": round(up, 2), "U_fallback": round(uf, 2),
                        "EV": round(ev, 3), "EV_pessimistic": round(pl * up + (1 - pl) * uf, 3),
                        "worst": round(min(up, uf), 2), "max_regret": round(best - min(up, uf), 2),
                        "years": r["years_to_target"]})
        out.sort(key=lambda x: -x["EV"])
        with open(os.path.join(a.out, "route_evaluation.csv"), "w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(out[0])); wr.writeheader(); wr.writerows(out)
    print("wrote", a.out, "options:", len(opts), "personal:", bool(personal))


if __name__ == "__main__":
    main()
