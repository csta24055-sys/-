"""Every value in WLC Studio carries where it came from and how sure we are.

The seven states are required by the implementation directive and are kept distinct everywhere
(storage, calculation, display). A missing value is never turned into 0.

| state            | 表示            | meaning                                                     | passed to the engine as |
|------------------|-----------------|-------------------------------------------------------------|-------------------------|
| confirmed        | 取得・確認済み  | from a source or the user, and confirmed by the user        | the value               |
| from_drawing     | 図面から計算    | computed from drawings / BIM / quantity tables (traceable)  | the value               |
| statistical      | 統計推定        | statistical estimate with a cited dataset and an interval   | the value (flagged)     |
| assumption       | 仮定            | explicit assumption (scenario value), no measured basis     | the value (flagged)     |
| not_obtained     | 未取得          | not available yet                                           | missing (None)          |
| not_applicable   | 適用外          | does not exist for this building                            | absent                  |
| not_computable   | 計算不能        | cannot be determined from available information             | missing (None)          |

Candidates proposed by an automatic lookup are stored separately and become a value only when
the user accepts one ("採用"). A candidate is never silently used in a calculation.
"""
from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any

STATES = ("confirmed", "from_drawing", "statistical", "assumption", "not_obtained", "not_applicable", "not_computable")
LABEL = {"confirmed": "取得・確認済み", "from_drawing": "図面から計算", "statistical": "統計推定", "assumption": "仮定",
         "not_obtained": "未取得", "not_applicable": "適用外", "not_computable": "計算不能"}
HAS_VALUE = {"confirmed", "from_drawing", "statistical", "assumption"}
ESTIMATED = {"statistical", "assumption"}
# Which value wins when several exist for one field (higher first). Ties: the newest.
PRIORITY = {"confirmed": 5, "from_drawing": 4, "statistical": 2, "assumption": 1,
            "not_applicable": 3, "not_computable": 0, "not_obtained": -1}
UNCERTAINTY_KINDS = ("none", "interval", "scenario")


class ProvenanceError(ValueError):
    pass


@dataclass
class Uncertainty:
    """low/high bound the value; kind says what they mean.

    interval: a prediction interval at `level` (e.g. 0.8). `calibrated` is True only when its
              empirical coverage was measured on independent data (validate.py); otherwise the UI
              shows 「仮の範囲」.
    scenario: low/high are alternative scenarios (e.g. 直接基礎 / 杭基礎), not a probability.
    """
    kind: str = "none"
    low: float | None = None
    high: float | None = None
    level: float | None = None
    calibrated: bool = False
    basis: str = ""

    def check(self) -> None:
        if self.kind not in UNCERTAINTY_KINDS:
            raise ProvenanceError("不確かさの種類 %r は使えない" % self.kind)
        if self.kind == "none":
            return
        for v in (self.low, self.high):
            if not (isinstance(v, (int, float)) and math.isfinite(v)):
                raise ProvenanceError("不確かさの範囲は有限の数値で指定する")
        if self.low > self.high:
            raise ProvenanceError("不確かさの下限が上限より大きい")
        if self.kind == "interval" and not (isinstance(self.level, (int, float)) and 0 < self.level < 1):
            raise ProvenanceError("予測区間には信頼水準（0〜1）を付ける")


@dataclass
class Value:
    """One stored value of one field."""
    field_id: str
    state: str
    value: Any = None
    unit: str = ""
    method: str = ""                 # e.g. user_entered, plateau_attribute, gsi_geocoder, ifc_quantity, mi_floor_area
    source_id: str = ""              # key of the data source registry (sources/registry.json) or a document id
    source_detail: str = ""          # page, table, cell, IFC entity id, building id ...
    retrieved_at: str = ""           # ISO date of retrieval
    factor_version: str = ""         # version of the dataset / factor set used
    permission: str = ""             # licence id or consent record
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    note: str = ""
    updated_at: float = field(default_factory=time.time)
    updated_by: str = "user"

    def check(self) -> "Value":
        if self.state not in STATES:
            raise ProvenanceError("状態 %r は使えない（%s のどれか）" % (self.state, "、".join(STATES)))
        if self.state in HAS_VALUE:
            if self.value is None or (isinstance(self.value, str) and not self.value.strip()):
                raise ProvenanceError("状態「%s」には値が要る（%s）" % (LABEL[self.state], self.field_id))
            if isinstance(self.value, float) and not math.isfinite(self.value):
                raise ProvenanceError("値が有限の数値でない（%s）" % self.field_id)
            if not self.method:
                raise ProvenanceError("値の取り方（method）を書く（%s）" % self.field_id)
        else:
            if self.value not in (None, ""):
                raise ProvenanceError("状態「%s」には値を持たせない（%s）。0 として扱うことはしない" % (LABEL[self.state], self.field_id))
        if self.state in ("statistical",) and self.uncertainty.kind == "none":
            raise ProvenanceError("統計推定には不確かさ（区間）を付ける（%s）" % self.field_id)
        if self.state in ("statistical", "from_drawing") and not self.source_id:
            raise ProvenanceError("統計推定・図面からの計算には出典（source_id）を付ける（%s）" % self.field_id)
        self.uncertainty.check()
        return self

    def to_json(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_json(d: dict) -> "Value":
        d = dict(d)
        u = d.pop("uncertainty", None) or {}
        v = Value(**{k: d[k] for k in d if k in Value.__dataclass_fields__})
        v.uncertainty = Uncertainty(**{k: u[k] for k in u if k in Uncertainty.__dataclass_fields__})
        return v

    @property
    def label(self) -> str:
        return LABEL[self.state]


def best(values: list[Value]) -> Value | None:
    """The value that is used for a field: highest state priority, then newest."""
    if not values:
        return None
    return max(values, key=lambda v: (PRIORITY[v.state], v.updated_at))


def conflicts(values: list[Value], rel_tol: float = 0.05) -> list[tuple[Value, Value]]:
    """Pairs of values with a value whose numbers differ by more than rel_tol (or differ as text)."""
    out = []
    vals = [v for v in values if v.state in HAS_VALUE]
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i].value, vals[j].value
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
                scale = max(abs(a), abs(b))
                if scale > 0 and abs(a - b) / scale > rel_tol:
                    out.append((vals[i], vals[j]))
            elif a != b:
                out.append((vals[i], vals[j]))
    return out
