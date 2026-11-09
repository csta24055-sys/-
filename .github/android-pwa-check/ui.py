#!/usr/bin/env python3
"""Drive Chrome on an Android emulator with adb + UI Automator (no extra tools):
open the web app, install it to the home screen, launch it from the icon, and record whether Android
started it as a standalone web app (WebappActivity / WebAPK) instead of a normal Chrome tab.
Emulator check — not a physical phone."""
import os, re, subprocess, sys, time, xml.etree.ElementTree as ET

URL = os.environ.get('PWA_URL', 'https://tajima-lab.pages.dev/')
OUT = os.environ.get('OUT', 'out')
LABEL = '田嶋研究室'
os.makedirs(OUT, exist_ok=True)
log = open(os.path.join(OUT, 'android-check.log'), 'a', encoding='utf-8')

def sh(cmd, check=False):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'{cmd}: {r.stderr}')
    return r.stdout
def say(*a):
    msg = ' '.join(str(x) for x in a)
    print(msg, flush=True); log.write(msg + '\n'); log.flush()
def shot(name):
    with open(os.path.join(OUT, name + '.png'), 'wb') as f:
        f.write(subprocess.run('adb exec-out screencap -p', shell=True, capture_output=True).stdout)
    say('screenshot', name)
def nodes():
    sh('adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1')
    xml = sh('adb exec-out cat /sdcard/ui.xml')
    try:
        root = ET.fromstring(xml[xml.find('<'):])
    except ET.ParseError:
        return []
    out = []
    for n in root.iter('node'):
        m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', n.get('bounds', ''))
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            out.append({'text': n.get('text', ''), 'desc': n.get('content-desc', ''), 'id': n.get('resource-id', ''), 'pkg': n.get('package', ''), 'x': (x1 + x2) // 2, 'y': (y1 + y2) // 2, 'w': x2 - x1})
    return out
def find(patterns):
    for n in nodes():
        for p in patterns:
            if re.search(p, n['text']) or re.search(p, n['desc']) or re.search(p, n['id']):
                return n
    return None
def tap(patterns, timeout=15, what=''):
    end = time.time() + timeout
    while time.time() < end:
        n = find(patterns)
        if n:
            sh(f"adb shell input tap {n['x']} {n['y']}")
            say('tap', what or patterns[0], '->', n['text'] or n['desc'] or n['id'])
            time.sleep(2)
            return True
        time.sleep(1.5)
    say('not found:', what or patterns)
    return False
def resumed():
    out = sh('adb shell dumpsys activity activities')
    lines = [l.strip() for l in out.splitlines() if 'ResumedActivity' in l]
    return lines[0] if lines else ''

say('chrome', sh('adb shell dumpsys package com.android.chrome | grep -m1 versionName').strip())
sh('adb shell am force-stop com.android.chrome')
sh(f'adb shell am start -a android.intent.action.VIEW -d "{URL}" com.android.chrome')
time.sleep(8)
for _ in range(4):  # first-run screens of a fresh Chrome
    tap([r'^(Accept & continue|Use without an account|No thanks|No, thanks|Got it|Continue|Skip|Not now)$'], timeout=4, what='dismiss first-run')
time.sleep(15)
shot('01-chrome-first-visit')
say('page shows dashboard:', bool(find([r'研究ダッシュボード'])))

# Install: ⋮ → "Install app" (or "Add to home screen") → "Install"
tap([r'^(More options|Customize and control Google Chrome)$', r'menu_button'], timeout=20, what='Chrome menu')
shot('02-chrome-menu')
installed = tap([r'^Install app', r'^Add to (H|h)ome screen', r'^アプリをインストール', r'^ホーム画面に追加'], timeout=15, what='Install app')
shot('03-install-dialog')
tap([r'^Install$', r'^Add$', r'^インストール$', r'^追加$'], timeout=20, what='confirm install')
tap([r'^Add automatically$', r'^Add to home screen$', r'^Add$'], timeout=6, what='launcher confirm (optional)')
time.sleep(12)  # WebAPK minting / shortcut creation
shot('04-after-install')

# Home screen → icon → launch
sh('adb shell input keyevent KEYCODE_HOME'); time.sleep(3)
found = tap([rf'^{LABEL}$'], timeout=10, what='home screen icon')
if not found:  # look in the app drawer
    sh('adb shell input swipe 540 1800 540 300 300'); time.sleep(2)
    found = tap([rf'^{LABEL}$'], timeout=10, what='app drawer icon')
shot('05-home-or-drawer')
time.sleep(10)
shot('06-launched-from-icon')
act = resumed()
say('resumed activity:', act)
standalone = bool(re.search(r'WebappActivity|WebApkActivity|org\.chromium\.webapk|WebApk', act))
say('dashboard visible after launch:', bool(find([r'研究ダッシュボード'])))
say('RESULT installed_menu=%s icon=%s standalone=%s' % (installed, found, standalone))
sys.exit(0 if (found and standalone) else 1)
