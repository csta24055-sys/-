"""重要区間を別モデル(Whisper large-v3)で再文字起こしし、一次文字起こしと照合するためのスクリプト。
usage: python verify_segments.py <audio.wav> <out.txt>
"""
import sys, wave
import numpy as np
from faster_whisper import WhisperModel

SEGS = [  # (開始秒, 終了秒, 確認目的)
    (60, 330, "授業方針・評価・試験形式"),
    (1240, 1300, "非常用電源・受電電圧"),
    (1420, 1520, "BCP・トイレ"),
    (1670, 1830, "給湯・レジオネラ・貯湯温度"),
    (1840, 2060, "排水・トラップ・封水・通気"),
    (2830, 2960, "節水便器の水量・合流式"),
    (3820, 3910, "コレラ・衛生の母"),
    (4020, 4100, "東京の水源比率・渇水"),
    (4590, 4660, "敷地のインフラ・電柱"),
    (4980, 5130, "責任分界点・プリント設問"),
]
w = wave.open(sys.argv[1]); sr = w.getframerate()
pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
m = WhisperModel("Systran/faster-whisper-large-v3", device="cpu", compute_type="int8", cpu_threads=4)
with open(sys.argv[2], "w") as f:
    for a, b, why in SEGS:
        segs, _ = m.transcribe(pcm[a*sr:b*sr], language="ja", beam_size=5, vad_filter=True,
                               condition_on_previous_text=False)
        f.write(f"\n## {a//60}:{a%60:02d}-{b//60}:{b%60:02d} {why}\n")
        for s in segs:
            t = a + s.start
            f.write(f"[{int(t//3600)}:{int(t%3600//60):02d}:{int(t%60):02d}] {s.text}\n"); f.flush()
