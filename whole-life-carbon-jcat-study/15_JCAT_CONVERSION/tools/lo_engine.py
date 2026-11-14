"""LibreOffice (headless, UNO) as an independent spreadsheet engine: load a workbook copy, set input
cells, recalculate everything, read the values of the formula cells. Never saves the document."""
import os, subprocess, time
import uno
from com.sun.star.beans import PropertyValue
from store import Err, ERR_CODES

LO_ERR = {"#NULL!": 1, "#DIV/0!": 2, "#VALUE!": 3, "#REF!": 4, "#NAME?": 5, "#NUM!": 6, "#N/A": 7}


def prop(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p


class LO:
    def __init__(self, port, profile):
        self.port = port
        self.proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--nologo", "--norestore", "--nodefault",
                                      "-env:UserInstallation=file://" + profile,
                                      "--accept=socket,host=localhost,port=%d;urp;" % port],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        for _ in range(240):
            try:
                self.ctx = resolver.resolve("uno:socket,host=localhost,port=%d;urp;StarOffice.ComponentContext" % port)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("LibreOffice did not start")
        self.desktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
        self.doc = None

    def load(self, path):
        self.doc = self.desktop.loadComponentFromURL(uno.systemPathToFileUrl(path), "_blank", 0,
                                                     (prop("Hidden", True), prop("MacroExecutionMode", 0)))
        self.sheets = {self.doc.Sheets.getByIndex(i).Name: self.doc.Sheets.getByIndex(i) for i in range(self.doc.Sheets.Count)}
        return self

    def set_value(self, sheet, row, col, value):
        """row/col 1-based; value None (clear), float, or str."""
        cell = self.sheets[sheet].getCellByPosition(col - 1, row - 1)
        if value is None:
            # VALUE 1 | DATETIME 2 | STRING 4 | FORMULA 16 (setString("") does not remove a number)
            cell.clearContents(1 | 2 | 4 | 16)
        elif isinstance(value, str):
            cell.setString(value)
        else:
            cell.setValue(float(value))

    def recalc(self):
        self.doc.calculateAll()

    def read_sheet(self, sheet, positions):
        """Values at the given (row, col) positions (1-based) of formula cells: float, str or Err."""
        sh = self.sheets[sheet]
        if not positions:
            return {}
        maxr = max(r for r, c in positions)
        maxc = max(c for r, c in positions)
        data = sh.getCellRangeByPosition(0, 0, maxc - 1, maxr - 1).getDataArray()
        out = {}
        for r, c in positions:
            v = data[r - 1][c - 1]
            out[(r, c)] = v if isinstance(v, str) else (None if v is None else float(v))
        # error results (FormulaResult.ERROR = 4)
        ranges = sh.getCellRangeByPosition(0, 0, maxc - 1, maxr - 1).queryFormulaCells(4)
        for addr in ranges.getRangeAddresses():
            for rr in range(addr.StartRow, addr.EndRow + 1):
                for cc in range(addr.StartColumn, addr.EndColumn + 1):
                    if (rr + 1, cc + 1) in out:
                        s = sh.getCellByPosition(cc, rr).getString()
                        out[(rr + 1, cc + 1)] = Err(LO_ERR.get(s, 100 + (int(s[4:]) if s.startswith("Err:") and s[4:].isdigit() else 99)))
        return out

    def close(self):
        try:
            if self.doc is not None:
                self.doc.close(True)
        except Exception:
            pass
        try:
            self.desktop.terminate()
        except Exception:
            pass
        self.proc.terminate()
