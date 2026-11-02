# 図表（出典付き）

`python scripts/make_figures.py` で再生成。各図の下部に出典（Box ID / 資料台帳 ID）と区分を記載。

| ファイル | 内容 | 区分・出典 |
|---|---|---|
| fig_bypass_cadr_fit.svg / _quadratic_ext.svg | バイパス開口率とCADR（抵抗則2種） | 【計算結果】入力: S-2026-01 |
| fig_bypass_power_*.svg | 開口率と送風機電力 | 【計算結果】入力: S-2026-01（電力は図6の直線近似【仮定】） |
| fig_ep_efficiency.svg | EP風量と集塵効率 | 端点【確認事実】S-2026-01、中間【仮定】 |
| fig_deposition.svg | 粒径と重力沈降β | 【計算結果】式: S-2021-01 |
| bypass_sweep.csv | 上記の数値表 | 【計算結果】 |
| ../screenshots/*.png | アプリ画面（E2Eテスト時） | — |
