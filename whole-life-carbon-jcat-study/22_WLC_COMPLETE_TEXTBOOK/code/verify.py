"""計算問題の検算（structlab.exam.questions の「解いて、答えを元の式に代入して確かめる」考え方を引き継ぐ）。

元の questions.py は sympy で式を解き、代入して両辺の一致を確かめた。この環境には sympy が無いので、
有理数（fractions.Fraction）で厳密に計算し、次の 3 つを確かめる：
  1. 独立な 2 通りの計算が一致する（閉じた式 と 年ごとに数え上げる素朴な計算 など）
  2. 逆問題は、求めた値を順方向の計算に代入すると与えられた値に戻る
  3. 次元（単位）が合い、定義域（周期 > 0、割合 0〜1、評価期間 > 0 など）に入っている
数値は説明用の架空の値（実在の原単位・J-CAT の値ではない）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction as Fr

# ---------------------------------------------------------------- 単位
BASE = {  # 名前 → (倍率, 次元)
    "kgCO2e": (Fr(1), {"CO2e": 1}), "tCO2e": (Fr(1000), {"CO2e": 1}), "gCO2e": (Fr(1, 1000), {"CO2e": 1}),
    "kg": (Fr(1), {"kg": 1}), "t": (Fr(1000), {"kg": 1}), "g": (Fr(1, 1000), {"kg": 1}),
    "m": (Fr(1), {"m": 1}), "km": (Fr(1000), {"m": 1}), "m2": (Fr(1), {"m": 2}), "m3": (Fr(1), {"m": 3}),
    "kWh": (Fr(1), {"kWh": 1}), "MWh": (Fr(1000), {"kWh": 1}), "MJ": (Fr(5, 18), {"kWh": 1}),
    "yr": (Fr(1), {"yr": 1}), "年": (Fr(1), {"yr": 1}), "回": (Fr(1), {}), "1": (Fr(1), {}), "%": (Fr(1, 100), {}),
    "台": (Fr(1), {}), "人": (Fr(1), {}), "L": (Fr(1), {"L": 1}), "tkm": (Fr(10 ** 6), {"kg": 1, "m": 1}),
}


def parse_unit(u: str) -> tuple[Fr, dict]:
    """"kgCO2e/(m2·yr)" "kgCO2e/kWh" "t·km" などを (倍率, 次元) に。"""
    u = u.replace(" ", "").replace("*", "·").replace("(", "").replace(")", "")
    if not u or u == "1":
        return Fr(1), {}
    num, _, den = u.partition("/")
    scale, dims = Fr(1), {}
    for part, sgn in ((num, 1), (den, -1)):
        if not part:
            continue
        for tok in part.split("·"):
            exp = 1
            if "^" in tok:
                tok, e = tok.split("^")
                exp = int(e)
            if tok not in BASE:
                raise ValueError(f"知らない単位 {tok}")
            s, d = BASE[tok]
            scale *= s ** (exp * sgn)
            for k, v in d.items():
                dims[k] = dims.get(k, 0) + v * exp * sgn
    return scale, {k: v for k, v in dims.items() if v}


@dataclass(frozen=True)
class Q:
    """量（値は基本単位での有理数、dims は次元）。"""
    v: Fr
    dims: tuple = ()

    @staticmethod
    def of(value, unit: str = "1") -> "Q":
        s, d = parse_unit(unit)
        return Q(Fr(value) * s, tuple(sorted(d.items())))

    def d(self) -> dict:
        return dict(self.dims)

    def _same(self, o: "Q"):
        if self.dims != o.dims:
            raise ValueError(f"次元が違うものを足し引き・比較した: {self.d()} と {o.d()}")

    def __add__(self, o):
        o = o if isinstance(o, Q) else Q.of(o)
        self._same(o)
        return Q(self.v + o.v, self.dims)

    __radd__ = __add__

    def __sub__(self, o):
        o = o if isinstance(o, Q) else Q.of(o)
        self._same(o)
        return Q(self.v - o.v, self.dims)

    def __neg__(self):
        return Q(-self.v, self.dims)

    def __mul__(self, o):
        if not isinstance(o, Q):
            return Q(self.v * Fr(o), self.dims)
        d = self.d()
        for k, x in o.d().items():
            d[k] = d.get(k, 0) + x
        return Q(self.v * o.v, tuple(sorted((k, x) for k, x in d.items() if x)))

    __rmul__ = __mul__

    def __truediv__(self, o):
        if not isinstance(o, Q):
            return Q(self.v / Fr(o), self.dims)
        return self * Q(1 / o.v, tuple((k, -x) for k, x in o.dims))

    def __eq__(self, o):
        return isinstance(o, Q) and self.dims == o.dims and self.v == o.v

    def __lt__(self, o):
        self._same(o)
        return self.v < o.v

    def __le__(self, o):
        self._same(o)
        return self.v <= o.v

    def to(self, unit: str) -> Fr:
        s, d = parse_unit(unit)
        if tuple(sorted(d.items())) != self.dims:
            raise ValueError(f"単位 {unit} に直せない（次元 {self.d()}）")
        return self.v / s

    def __hash__(self):
        return hash((self.v, self.dims))


# ---------------------------------------------------------------- 時間の基本関数（教材の原理 3）
def n_events(T, L) -> int:
    """評価期間 T の中で起きる更新の回数 #{n ≥ 1 : nL < T}（T ちょうどの更新は数えない約束）。"""
    T, L = Fr(T), Fr(L)
    if L <= 0:
        raise ValueError("周期は正")
    k = math.ceil(T / L) - 1
    return max(k, 0)


def n_events_loop(T, L) -> int:
    """数え上げで同じ回数（n_events の独立な確認）。"""
    T, L = Fr(T), Fr(L)
    n, k = 0, 1
    while k * L < T:
        n += 1
        k += 1
    return n


# ---------------------------------------------------------------- 問題の記録
@dataclass
class Problem:
    id: str
    level: str                     # 初級 / 中級 / 上級
    kind: str                      # 12 種類の問題の型
    title: str
    statement: str                 # 問題文（$…$ の式を含む）
    answer: str                    # 解答（結論）
    steps: list[str] = field(default_factory=list)   # 途中式・使った原理
    principles: list[str] = field(default_factory=list)  # 使う基本原理（P1〜P5）
    sections: list[str] = field(default_factory=list)    # 教材の節（解くのに必要な説明の場所）
    novel: bool = False            # 教材の例題そのままでない（値・条件・問い方を変えた）
    external: str | None = None    # 教材の外の知識が要る場合の説明（範囲外と明示）
    checks: list[tuple[str, bool]] = field(default_factory=list)  # 検算の記録（説明, 結果）
    rubric: list[str] = field(default_factory=list)  # 記述・証明の採点の観点

    @property
    def verified(self) -> bool | None:
        return None if not self.checks else all(ok for _, ok in self.checks)


def check(p: Problem, desc: str, ok: bool) -> bool:
    p.checks.append((desc, bool(ok)))
    return bool(ok)


def fmt(x, digits: int = 6) -> str:
    """有理数の表示（整数ならそのまま、そうでなければ分数と小数）。"""
    x = Fr(x)
    if x.denominator == 1:
        return f"{x.numerator:,}"
    f = float(x)
    return f"{x.numerator}/{x.denominator}（≈ {f:,.{digits}g}）"
