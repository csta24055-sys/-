"""第1回授業動画の音声をローカルで文字起こしする（外部APIへ音声は送信しない）。
usage: python transcribe.py <audio.wav(16kHz mono)> <out_dir> [model]
出力: transcript.jsonl（区間ごと、逐次追記）, transcript.txt（[mm:ss] 付き）
"""
import json, sys, os, time
import wave
import numpy as np
from faster_whisper import WhisperModel

audio, out = sys.argv[1], sys.argv[2]
model_name = sys.argv[3] if len(sys.argv) > 3 else "kotoba-tech/kotoba-whisper-v2.0-faster"
os.makedirs(out, exist_ok=True)
m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
w = wave.open(audio)
pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
segs, info = m.transcribe(pcm, language="ja", beam_size=5, vad_filter=True,
                          condition_on_previous_text=False,
                          initial_prompt="建築設備の授業です。空調、換気、給排水、衛生設備、電気設備、熱負荷。")
t0 = time.time()
def ts(s): return f"{int(s//3600):d}:{int(s%3600//60):02d}:{int(s%60):02d}"
with open(f"{out}/transcript.jsonl", "w") as fj, open(f"{out}/transcript.txt", "w") as ft:
    for s in segs:
        fj.write(json.dumps({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text}, ensure_ascii=False) + "\n")
        ft.write(f"[{ts(s.start)}] {s.text}\n"); fj.flush(); ft.flush()
print("done", info.duration, time.time() - t0)
