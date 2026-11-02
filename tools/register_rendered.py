#!/usr/bin/env python3
"""Playwright等で描画した本文を一次資料として登録する。
使い方: python3 tools/register_rendered.py ID TEXTFILE URL "題名" "発行者" "日付"
data/text/ID.txt に保存し、source_registry.csv に行を追加（既存IDは置換）。"""
import sys, hashlib, csv, datetime, pathlib, shutil
ID, src, url, title, pub, date = sys.argv[1:7]
root = pathlib.Path(__file__).resolve().parent.parent
dst = root / 'data/text' / f'{ID}.txt'
shutil.copyfile(src, dst)
b = dst.read_bytes()
reg = root / 'research/09_資料台帳・証拠管理/source_registry.csv'
rows = list(csv.reader(reg.open(encoding='utf-8')))
rows = [r for r in rows if not r or r[0] != ID]
rows.append([ID, title, pub + '（Playwrightで描画）', date, url, datetime.date.today().isoformat(),
             hashlib.sha256(b).hexdigest(), str(len(b)), '取得済(描画text)'])
with reg.open('w', encoding='utf-8', newline='') as f:
    csv.writer(f).writerows(rows)
print('registered', ID, len(b))
