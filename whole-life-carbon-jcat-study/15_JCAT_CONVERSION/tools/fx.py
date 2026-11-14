"""Excel formula tools: tokenizer, shift of shared formulas, R1C1 normal form, skeletons, parser, LaTeX.

Mechanical only. Nothing here evaluates a formula. Formulas are treated as text read from the
workbook XML (without the leading '=').
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------------------------
# tokens
# ---------------------------------------------------------------------------------------------
_SHEET = r"(?:'(?:[^']|'')+'|\[\d+\][^\s!'\"(),;{}]*|[^\s!'\"(),:+\-*/^&=<>{};%#\[\]]+)!"
_CELL = r"\$?[A-Z]{1,3}\$?\d{1,7}"
_REF = re.compile(r"(%s)?(%s(?::%s)?|\$?[A-Z]{1,3}:\$?[A-Z]{1,3}|\$?\d{1,7}:\$?\d{1,7})(?![A-Za-z0-9_.(])" % (_SHEET, _CELL, _CELL))
_ERR = re.compile(r"#(?:REF!|N/A|DIV/0!|VALUE!|NAME\?|NUM!|NULL!|GETTING_DATA)")
_FUNC = re.compile(r"(?:_xlfn\.|_xlws\.)?[A-Za-z][A-Za-z0-9_.]*(?=\()")
_NUM = re.compile(r"(?:\d+\.?\d*|\.\d+)(?:[Ee][+-]?\d+)?")
_NAME = re.compile(r"[A-Za-z_\\\u0080-￿][A-Za-z0-9_.\\\u0080-￿]*")
_OPS = ("<>", "<=", ">=", "+", "-", "*", "/", "^", "&", "=", "<", ">", "%", "(", ")", ",", ";", "{", "}", ":", "@")
_SHEET_ERR = re.compile(r"(%s)#REF!" % _SHEET)


def col_num(s):
    n = 0
    for ch in s:
        n = n * 26 + ord(ch) - 64
    return n


def col_letters(c):
    s = ""
    while c > 0:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def tokenize(f):
    """List of (kind, text, extra). kind: str, err, ref, func, num, bool, name, op, ws, unk."""
    out, i, n = [], 0, len(f)
    while i < n:
        ch = f[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if f[j] == '"':
                    if j + 1 < n and f[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            out.append(("str", f[i:j + 1], None))
            i = j + 1
            continue
        if ch.isspace():
            j = i
            while j < n and f[j].isspace():
                j += 1
            out.append(("ws", f[i:j], None))
            i = j
            continue
        m = _SHEET_ERR.match(f, i)
        if m:
            out.append(("err", m.group(0), None))
            i = m.end()
            continue
        m = _ERR.match(f, i)
        if m:
            out.append(("err", m.group(0), None))
            i = m.end()
            continue
        m = _FUNC.match(f, i)
        if m:
            out.append(("func", m.group(0), None))
            i = m.end()
            continue
        m = _REF.match(f, i)
        if m:
            out.append(("ref", m.group(0), (m.group(1) or "", m.group(2))))
            i = m.end()
            continue
        m = _NUM.match(f, i)
        if m:
            out.append(("num", m.group(0), None))
            i = m.end()
            continue
        if f.startswith(("TRUE", "FALSE"), i) and not (i + 5 <= n and _NAME.match(f, i) and len(_NAME.match(f, i).group(0)) > (4 if f.startswith("TRUE", i) else 5)):
            w = "TRUE" if f.startswith("TRUE", i) else "FALSE"
            out.append(("bool", w, None))
            i += len(w)
            continue
        m = _NAME.match(f, i)
        if m:
            out.append(("name", m.group(0), None))
            i = m.end()
            continue
        for op in _OPS:
            if f.startswith(op, i):
                out.append(("op", op, None))
                i += len(op)
                break
        else:
            out.append(("unk", ch, None))
            i += 1
    return out


_PART = re.compile(r"(\$?)([A-Z]{1,3})?(\$?)(\d{1,7})?")


def _parts(body):
    """[(col_abs, col, row_abs, row)] for each side of a reference body; col/row None when absent."""
    res = []
    for side in body.split(":"):
        m = _PART.fullmatch(side)
        ca, c, ra, r = m.group(1), m.group(2), m.group(3), m.group(4)
        if c is None:                       # row only, e.g. "$5"
            res.append((False, None, bool(ca), int(r)))
        else:
            res.append((bool(ca), col_num(c), bool(ra), int(r) if r else None))
    return res


def shift_ref(body, dr, dc):
    out = []
    for ca, c, ra, r in _parts(body):
        s = ""
        if c is not None:
            s += ("$" if ca else "") + col_letters(c if ca else c + dc)
        if r is not None:
            s += ("$" if ra else "") + str(r if ra else r + dr)
        out.append(s)
    return ":".join(out)


def r1c1(body, row, col):
    out = []
    for ca, c, ra, r in _parts(body):
        s = ""
        if r is not None:
            s += "R%d" % r if ra else ("R[%d]" % (r - row) if r != row else "R")
        if c is not None:
            s += "C%d" % c if ca else ("C[%d]" % (c - col) if c != col else "C")
        out.append(s)
    return ":".join(out)


def ref_cells(body):
    """Absolute A1 text of a reference body without $ (for the list of referenced places)."""
    return body.replace("$", "")


def shifted_text(tokens, dr, dc):
    if dr == 0 and dc == 0:
        return "".join(t[1] for t in tokens)
    out = []
    for kind, text, extra in tokens:
        if kind == "ref":
            out.append(extra[0] + shift_ref(extra[1], dr, dc))
        else:
            out.append(text)
    return "".join(out)


def norm_sheet(prefix):
    return prefix[:-1].strip("'").replace("''", "'") if prefix else ""


def pattern(tokens, row, col):
    """R1C1 normal form (copies of a rule share it), the skeleton (references replaced), the method form
    (references, numbers and strings replaced), and the list of referenced places."""
    p, s, m, refs = [], [], [], []
    for kind, text, extra in tokens:
        if kind == "ws":
            continue
        if kind == "ref":
            sh = norm_sheet(extra[0])
            rr = r1c1(extra[1], row, col)
            p.append((sh + "!" if sh else "") + rr)
            s.append("〈R〉" if ":" in extra[1] else "〈c〉")
            m.append(s[-1])
            refs.append((sh + "!" if sh else "") + ref_cells(extra[1]))
        elif kind == "func":
            name = text.upper().replace("_XLFN.", "").replace("_XLWS.", "")
            p.append(name), s.append(name), m.append(name)
        elif kind == "num":
            p.append(text), s.append(text), m.append("〈n〉")
        elif kind == "str":
            p.append(text), s.append(text), m.append("〈s〉")
        else:
            p.append(text), s.append(text), m.append(text)
    return "".join(p), "".join(s), "".join(m), refs


def hid(text, prefix):
    return prefix + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------------------------
# function families (for the kind of a formula)
# ---------------------------------------------------------------------------------------------
FAMILY = {
    "条件分岐": {"IF", "IFS", "IFERROR", "IFNA", "CHOOSE", "SWITCH", "AND", "OR", "NOT", "XOR", "ISBLANK", "ISERROR", "ISNUMBER",
             "ISTEXT", "ISNA", "ISERR", "ISLOGICAL", "ISEVEN", "ISODD"},
    "条件付き集計": {"SUMIF", "SUMIFS", "COUNTIF", "COUNTIFS", "AVERAGEIF", "AVERAGEIFS", "MAXIFS", "MINIFS", "DSUM", "DCOUNT"},
    "集計": {"SUM", "SUMPRODUCT", "AVERAGE", "MAX", "MIN", "COUNT", "COUNTA", "COUNTBLANK", "PRODUCT", "SUMSQ", "LARGE", "SMALL",
           "MEDIAN", "SUBTOTAL", "AGGREGATE"},
    "検索・参照": {"VLOOKUP", "HLOOKUP", "LOOKUP", "INDEX", "MATCH", "OFFSET", "INDIRECT", "XLOOKUP", "XMATCH", "ROW", "COLUMN",
              "ROWS", "COLUMNS", "ADDRESS", "CELL", "TRANSPOSE"},
    "丸め・整数": {"ROUND", "ROUNDUP", "ROUNDDOWN", "INT", "CEILING", "FLOOR", "MOD", "QUOTIENT", "TRUNC", "CEILING.MATH",
              "FLOOR.MATH", "MROUND", "ODD", "EVEN"},
    "数学関数": {"ABS", "SQRT", "EXP", "LN", "LOG", "LOG10", "POWER", "SIGN", "PI"},
    "文字列": {"CONCATENATE", "CONCAT", "TEXT", "LEFT", "RIGHT", "MID", "LEN", "FIND", "SEARCH", "SUBSTITUTE", "REPLACE", "TRIM",
            "UPPER", "LOWER", "VALUE", "TEXTJOIN", "REPT", "ASC", "JIS", "T", "N", "DBCS"},
    "日付": {"DATE", "YEAR", "MONTH", "DAY", "TODAY", "NOW", "DATEDIF", "EDATE", "EOMONTH", "DATEVALUE"},
}
FUNC_FAMILY = {f: fam for fam, fs in FAMILY.items() for f in fs}


def kind_of(tokens):
    funcs, n_refs, ops = [], 0, set()
    for kind, text, extra in tokens:
        if kind == "func":
            funcs.append(text.upper().replace("_XLFN.", "").replace("_XLWS.", ""))
        elif kind == "ref":
            n_refs += 1
        elif kind == "op" and text in "+-*/^&":
            ops.add(text)
    fams = sorted({FUNC_FAMILY.get(f, "その他の関数") for f in funcs})
    if not funcs:
        if n_refs == 0:
            return "定数式", funcs
        if n_refs == 1 and not ops:
            return "単純な参照（値の写し）", funcs
        return "四則演算", funcs
    return "・".join(fams) + ("＋四則演算" if ops else ""), funcs


# ---------------------------------------------------------------------------------------------
# parser and LaTeX
# ---------------------------------------------------------------------------------------------
class ParseError(Exception):
    pass


class Parser:
    PREC = [("=", "<>", "<", ">", "<=", ">="), ("&",), ("+", "-"), ("*", "/"), ("^",)]

    def __init__(self, tokens):
        self.t = [x for x in tokens if x[0] != "ws"]
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("eof", "", None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, text):
        tok = self.take()
        if tok[1] != text:
            raise ParseError("expected %s got %s" % (text, tok[1]))

    def parse(self):
        if self.peek()[1] == "=":
            self.take()
        e = self.binary(0)
        if self.peek()[0] != "eof":
            raise ParseError("trailing %s" % self.peek()[1])
        return e

    def binary(self, level):
        if level == len(self.PREC):
            return self.unary()
        left = self.binary(level + 1)
        while self.peek()[0] == "op" and self.peek()[1] in self.PREC[level]:
            op = self.take()[1]
            right = self.binary(level + 1)
            left = ("bin", op, left, right)
        return left

    def unary(self):
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("-", "+"):
            self.take()
            return ("neg" if tok[1] == "-" else "pos", self.unary())
        e = self.postfix()
        return e

    def postfix(self):
        e = self.primary()
        while self.peek()[1] == "%":
            self.take()
            e = ("pct", e)
        return e

    def primary(self):
        kind, text, extra = self.take()
        if kind == "op" and text == "(":
            e = self.binary(0)
            self.expect(")")
            return ("paren", e)
        if kind == "op" and text == "{":
            rows, row = [], []
            while True:
                tok = self.take()
                if tok[1] == "}":
                    rows.append(row)
                    break
                if tok[1] == ";":
                    rows.append(row); row = []
                elif tok[1] == ",":
                    continue
                elif tok[1] == "-":
                    row.append("-" + self.take()[1])
                else:
                    row.append(tok[1])
            return ("array", rows)
        if kind == "func":
            self.expect("(")
            args = []
            if self.peek()[1] == ")":
                self.take()
                return ("call", text.upper().replace("_XLFN.", "").replace("_XLWS.", ""), args)
            while True:
                if self.peek()[1] in (",", ")"):
                    args.append(("empty",))
                else:
                    args.append(self.binary(0))
                tok = self.take()
                if tok[1] == ")":
                    break
                if tok[1] != ",":
                    raise ParseError("bad argument separator %s" % tok[1])
            return ("call", text.upper().replace("_XLFN.", "").replace("_XLWS.", ""), args)
        if kind == "ref":
            e = ("ref", extra)
            while self.peek()[1] == ":" and self.i + 1 < len(self.t) and self.t[self.i + 1][0] == "ref":
                self.take()
                e = ("range2", e, ("ref", self.take()[2]))
            return e
        if kind in ("num", "str", "bool", "err", "name"):
            return (kind, text)
        if kind == "op" and text == "@":
            return self.primary()
        raise ParseError("unexpected %s %s" % (kind, text))


_TEX_ESC = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#", "^": r"\^{}", "_": r"\_",
            "%": r"\%", "~": r"\~{}"}


def tex_text(s):
    return "".join(_TEX_ESC.get(ch, ch) for ch in s)


class Tex:
    """LaTeX of a parsed formula at a representative cell (row, col) of a sheet.

    Variables: a cell of the same sheet is X_{<column>}(i + d) with i the row of the formula cell;
    an absolute row is written as a number; another sheet adds its name as superscript.
    """

    def __init__(self, row, col, sheet):
        self.row, self.col, self.sheet = row, col, sheet

    def coord(self, ca, c, ra, r):
        cs = col_letters(c) if c is not None else None
        if r is None:
            rs = None
        elif ra:
            rs = str(r)
        else:
            d = r - self.row
            rs = "i" if d == 0 else ("i%+d" % d)
        return cs, rs

    def var(self, extra):
        prefix, body = extra
        sh = norm_sheet(prefix)
        sup = r"^{\langle\text{%s}\rangle}" % tex_text(sh) if sh else ""
        parts = _parts(body)
        if len(parts) == 1:
            cs, rs = self.coord(*parts[0])
            return r"X%s_{\mathrm{%s}}(%s)" % (sup, cs, rs)
        (c1, r1), (c2, r2) = self.coord(*parts[0]), self.coord(*parts[1])
        if r1 is None:
            return r"\mathbf{X}%s_{\mathrm{%s}..\mathrm{%s}}(\cdot)" % (sup, c1, c2)
        if c1 is None:
            return r"\mathbf{X}%s_{\cdot}(%s..%s)" % (sup, r1, r2)
        cols = c1 if c1 == c2 else r"%s..\mathrm{%s}" % (c1, c2)
        rows = r1 if r1 == r2 else "%s..%s" % (r1, r2)
        return r"\mathbf{X}%s_{\mathrm{%s}}(%s)" % (sup, cols, rows)

    def go(self, e):
        k = e[0]
        if k == "ref":
            return self.var(e[1])
        if k == "range2":
            return r"\left[%s : %s\right]" % (self.go(e[1]), self.go(e[2]))
        if k == "num":
            return e[1]
        if k == "str":
            return r"\text{``%s''}" % tex_text(e[1][1:-1].replace('""', '"'))
        if k == "bool":
            return r"\mathrm{%s}" % e[1]
        if k == "err":
            return r"\mathtt{%s}" % tex_text(e[1])
        if k == "name":
            return r"\mathsf{%s}" % tex_text(e[1])
        if k == "empty":
            return r"\varnothing"
        if k == "array":
            return r"\begin{pmatrix}%s\end{pmatrix}" % r" \\ ".join(" & ".join(tex_text(x) for x in row) for row in e[1])
        if k == "paren":
            return r"\left(%s\right)" % self.go(e[1])
        if k == "neg":
            return "-" + self.go(e[1])
        if k == "pos":
            return self.go(e[1])
        if k == "pct":
            return r"\frac{%s}{100}" % self.go(e[1])
        if k == "bin":
            op, a, b = e[1], self.go(e[2]), self.go(e[3])
            if op == "/":
                return r"\frac{%s}{%s}" % (a, b)
            if op == "^":
                return r"{%s}^{%s}" % (a, b)
            sym = {"*": r"\cdot", "+": "+", "-": "-", "&": r"\mathbin{\Vert}", "=": "=", "<>": r"\neq", "<": "<", ">": ">",
                   "<=": r"\le", ">=": r"\ge"}[op]
            return "%s %s %s" % (a, sym, b)
        if k == "call":
            name, args = e[1], [self.go(a) for a in e[2]]
            if name == "IF" and len(args) in (2, 3):
                other = args[2] if len(args) == 3 else r"\mathrm{FALSE}"
                return r"\begin{cases} %s & \text{if } %s \\ %s & \text{otherwise} \end{cases}" % (args[1], args[0], other)
            if name == "SUM":
                return r"\sum\left(%s\right)" % ", ".join(args)
            if name == "SUMPRODUCT":
                return r"\sum \left(%s\right)" % r" \odot ".join(args)
            if name == "SUMIF" and len(args) in (2, 3):
                summed = args[2] if len(args) == 3 else args[0]
                return r"\sum %s \cdot \left[%s \sim %s\right]" % (summed, args[0], args[1])
            if name == "SUMIFS" and len(args) >= 3:
                conds = r" \wedge ".join(r"%s \sim %s" % (args[j], args[j + 1]) for j in range(1, len(args) - 1, 2))
                return r"\sum %s \cdot \left[%s\right]" % (args[0], conds)
            if name in ("MAX", "MIN"):
                return r"\%s\left(%s\right)" % (name.lower(), ", ".join(args))
            if name == "ABS" and len(args) == 1:
                return r"\left|%s\right|" % args[0]
            if name == "SQRT" and len(args) == 1:
                return r"\sqrt{%s}" % args[0]
            if name == "INT" and len(args) == 1:
                return r"\left\lfloor %s \right\rfloor" % args[0]
            if name == "ROUNDUP" and len(args) == 2 and args[1] == "0":
                return r"\left\lceil %s \right\rceil" % args[0]
            if name == "ROUNDDOWN" and len(args) == 2 and args[1] == "0":
                return r"\operatorname{trunc}\left(%s\right)" % args[0]
            if name == "AND":
                return r"\left(%s\right)" % r" \wedge ".join(args)
            if name == "OR":
                return r"\left(%s\right)" % r" \vee ".join(args)
            if name == "NOT" and len(args) == 1:
                return r"\neg\left(%s\right)" % args[0]
            return r"\operatorname{%s}\left(%s\right)" % (tex_text(name).replace(".", "."), ", ".join(args))
        raise ParseError("cannot render %s" % k)


def to_tex(tokens, row, col, sheet):
    """(LaTeX, error). The LaTeX starts with the variable of the cell itself."""
    try:
        ast = Parser(tokens).parse()
        rhs = Tex(row, col, sheet).go(ast)
    except (ParseError, IndexError, KeyError, ValueError, AttributeError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    return r"X_{\mathrm{%s}}(i) = %s" % (col_letters(col), rhs), None


def depth(tokens):
    d = best = 0
    for kind, text, extra in tokens:
        if kind == "op" and text == "(":
            d += 1
            best = max(best, d)
        elif kind == "op" and text == ")":
            d -= 1
    return best
