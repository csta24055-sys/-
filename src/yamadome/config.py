"""設定の読み込みと未確定項目の洗い出し。"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Site:
    raw: dict
    path: Path
    unresolved: list[str] = field(default_factory=list)

    @property
    def grid_x(self) -> dict[str, float]:
        return self.raw["grid"]["x"]

    @property
    def grid_y(self) -> dict[str, float]:
        return self.raw["grid"]["y"]

    def depth(self, cls: str) -> float:
        return float(self.raw["depth_classes"][cls]["depth"])

    @property
    def base_depth(self) -> float:
        return self.depth("base")

    @property
    def is_complete(self) -> bool:
        return not self.unresolved


def _scan_nulls(node, prefix, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("note", "source", "sources", "at"):
                continue
            _scan_nulls(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            name = v.get("name", i) if isinstance(v, dict) else i
            _scan_nulls(v, f"{prefix}[{name}]", out)
    elif node is None:
        out.append(prefix)


def load(path: str | Path) -> Site:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    site = Site(raw=raw, path=path)
    _scan_nulls(raw, "", site.unresolved)
    return site
