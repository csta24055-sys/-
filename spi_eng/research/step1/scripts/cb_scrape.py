import sys, re, json, time, html, urllib.parse, subprocess, os, csv, datetime
OUT = sys.argv[1]; LOG = sys.argv[2]
QUERIES = [
 "SPI 英語 テストセンター","SPI 英語 長文","テストセンター 英語 長文","SPI 英語検査","SPI 英語能力検査","テストセンター 英語検査",
 "SPI ENG","SPI 英語 長文 3つ","SPI 英語 長文 2つ","SPI 英語 長文 4つ","SPI 英語 高得点","SPI 英語 難しい",
 "テストセンター 英語 難しい","SPI 英語 出来なかった","SPI 英語 足切り","SPI 英語 何割","テストセンター 英語 何問",
 "SPI 英語 対策","SPI 英語 時間","テスセン 英語","テストセンター 英語 長文 出た","SPI 英語 同意語 反意語",
 "SPI 英語 並び替え","SPI 英語 英英辞典","SPI 英語 結果","SPI 英語 使い回し","SPI 英語 再受検","SPI3 英語",
 "SPI 英語 オンライン会場","テストセンター 英語 3タブ","SPI 英語 長文 出ない","SPI 英語 長文 多い","SPI 英語 手応え",
 "SPI 英語 落ちた","SPI 英語 通過","SPI 英語 商社","SPI 英語 航空","SPI 英語 外資","英語 テストセンター 受けた",
 "SPI 英語 長文 何題",
]
def get(url):
    r = subprocess.run(["curl","-s","-L","-m","30","-A","Mozilla/5.0",url],capture_output=True)
    return r.stdout.decode("utf-8","ignore")
ids_by_q = {}
with open(LOG,"w",newline="",encoding="utf-8") as lf:
    w = csv.writer(lf); w.writerow(["query","pages_fetched","ids_found","new_ids","ts"])
    seen = set()
    for q in QUERIES:
        found = []
        pages = 0
        for b in range(1, 101, 10):
            u = "https://chiebukuro.yahoo.co.jp/search?" + urllib.parse.urlencode({"p": q, "flg": 3, "b": b})
            t = get(u); pages += 1
            ids = list(dict.fromkeys(re.findall(r'question_detail/q(\d+)', t)))
            if not ids: break
            new_page = [i for i in ids if i not in found]
            if not new_page: break
            found += new_page
            time.sleep(0.7)
        new = [i for i in found if i not in seen]; seen.update(found)
        ids_by_q[q] = found
        w.writerow([q, pages, len(found), len(new), datetime.datetime.now().isoformat(timespec="seconds")])
        print(q, pages, len(found), len(new), flush=True)
json.dump(ids_by_q, open(os.path.join(OUT, "ids_by_query.json"), "w"), ensure_ascii=False)
