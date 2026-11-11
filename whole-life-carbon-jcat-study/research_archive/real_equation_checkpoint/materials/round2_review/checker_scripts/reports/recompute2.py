import json, collections, re
R='/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/'
L=lambda p: json.load(open(R+p))
C=collections.Counter
units=L('01_LEDGER/units.json'); U=units['units']
txt=open(R+'01_LEDGER/README.md').read()
rows=re.findall(r'^\| ([A-Z0-9\-]+) \| (.+?) \| (.+?) \| (.+?) \| (既存|追加) \| (あり|なし) \|$',txt,flags=re.M)
print(len(rows), C(r[3] for r in rows))
lab={}
for r in rows: lab[r[0]]=r[3]
# which unit(s) are RATIO/LSP ambiguous
for u in U:
    print(u['id'],u['structure_class'],u.get('structure_subclass'),lab[u['id']]) if u['id'] in('X-16','X-12','X-13','A13-04','A13-05','B2-01','SUM-04','SUM-05','SUM-06','SUM-07','SUM-08') else None
import subprocess
