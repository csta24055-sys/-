"""A Store whose cells are overlaid by the changed values of one case (for the reference evaluator)."""
import collections
from store import KEY_SHIFT


class OverlaySheet:
    def __init__(self, sheet, changes):
        self.base = sheet
        self.book, self.name, self.sid = sheet.book, sheet.name, sheet.sid
        self.values = collections.ChainMap(changes, sheet.values) if changes else sheet.values
        self.formula = sheet.formula
        mr, mc = sheet.max_row, sheet.max_col
        for k in (changes or {}):
            if changes[k] is not None:
                mr, mc = max(mr, k // KEY_SHIFT), max(mc, k % KEY_SHIFT)
        self.max_row, self.max_col = mr, mc

    def get(self, r, c):
        return self.values.get(r * KEY_SHIFT + c)


class OverlayStore:
    def __init__(self, store, changes):
        """changes: {sheet sid: {key: value}}"""
        self.store = store
        self.changes = changes
        self._sheets = {}
        self.names, self.local_names = store.names, store.local_names

    def sheet(self, book, name):
        sh = self.store.sheet(book, name)
        if sh is None:
            return None
        o = self._sheets.get(sh.sid)
        if o is None:
            o = self._sheets[sh.sid] = OverlaySheet(sh, self.changes.get(sh.sid))
        return o

    def resolve_name(self, book, sheet, name):
        return self.store.resolve_name(book, sheet, name)
