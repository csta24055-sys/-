# Regenerate the READMEs in memory (write() is replaced; nothing is written to the repository) and diff with disk.
import sys, difflib
sys.dont_write_bytecode=True
import tools.build_reports as br
import tools.progress_ledger as pl
from pathlib import Path
out={}
br.write=lambda rel,text: out.__setitem__(rel, text.rstrip()+"\n")
br.print=lambda *a,**k: None
br.main()
for rel,text in out.items():
    disk=(br.S/rel).read_text(encoding='utf-8')
    same = disk==text
    print(rel,'IDENTICAL' if same else 'DIFFERS')
    if not same:
        for l in list(difflib.unified_diff(disk.splitlines(),text.splitlines(),'disk','regen',lineterm='',n=0))[:20]: print('   ',l[:200])
