"""TeX の部分集合 → 構文木 → (1) MathML（式の画像化用） (2) reportlab の段落マークアップ（文中の式） (3) Word の文字列片。

教材の数式は TeX の部分集合で書き、表示式は Chromium の MathML 組版で画像にし、文中の式は文字の飾り（斜体・上付き・下付き）で
表す。知らない命令はエラーにする（式が黙って崩れることを防ぐ）。

対応：\\frac \\dfrac \\tfrac \\sqrt[n]{} ^ _ \\sum \\prod \\int \\lim \\max \\min（表示式では上下に添字）、\\left \\right、
cases・aligned・array・pmatrix・bmatrix 環境、\\text \\mathrm \\mathbf \\mathcal \\mathbb \\operatorname、\\hat \\bar
\\overline \\tilde \\dot、ギリシャ文字、関係・演算の記号、空白（\\, \\; \\quad など）。
"""
from __future__ import annotations

import re
from html import escape

VERSION = "10"            # 変換の版（式の画像のキャッシュの鍵に入れる）

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "ϕ", "varphi": "φ", "chi": "χ",
    "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω", "ell": "ℓ",
}
UPRIGHT_GREEK = set("ΓΔΘΛΞΠΣΦΨΩ")
SYMBOLS = {
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "sim": "∼",
    "simeq": "≃", "propto": "∝", "ll": "≪", "gg": "≫", "in": "∈", "notin": "∉", "ni": "∋", "subset": "⊂",
    "subseteq": "⊆", "supset": "⊃", "cup": "∪", "cap": "∩", "setminus": "∖", "emptyset": "∅", "varnothing": "∅",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔",
    "iff": "⇔", "mapsto": "↦", "times": "×", "cdot": "⋅", "div": "÷", "pm": "±", "mp": "∓", "infty": "∞",
    "partial": "∂", "nabla": "∇", "forall": "∀", "exists": "∃", "neg": "¬", "land": "∧", "lor": "∨", "mid": "∣",
    "ldots": "…", "cdots": "⋯", "dots": "…", "vdots": "⋮", "lceil": "⌈", "rceil": "⌉", "lfloor": "⌊",
    "rfloor": "⌋", "langle": "⟨", "rangle": "⟩", "circ": "∘", "star": "⋆", "ast": "∗", "prime": "′",
    "parallel": "∥", "perp": "⊥", "angle": "∠", "triangle": "△", "Box": "□", "checkmark": "✓", "dagger": "†",
    "lbrace": "{", "rbrace": "}", "lnot": "¬", "lvert": "|", "rvert": "|", "top": "⊤", "intercal": "⊺", "sharp": "♯", "vert": "|", "Vert": "‖", "bullet": "∙", "oplus": "⊕", "otimes": "⊗",
}
BIGOPS = {"sum": "∑", "prod": "∏", "int": "∫", "oint": "∮", "iint": "∬", "bigcup": "⋃", "bigcap": "⋂"}
LIMOPS = {"lim", "max", "min", "sup", "inf", "argmax", "argmin"}
FUNCS = {"sin", "cos", "tan", "exp", "log", "ln", "det", "dim", "deg", "arg", "sgn", "Re", "Im", "lcm", "gcd"}
ACCENTS = {"hat": "^", "bar": "¯", "overline": "¯", "tilde": "~", "dot": "˙", "ddot": "¨", "vec": "→", "widehat": "^"}
SPACES = {",": 0.17, ";": 0.28, ":": 0.22, " ": 0.25, "quad": 1.0, "qquad": 2.0, "!": -0.17, "enspace": 0.5}
MCAL = {"L": "ℒ", "F": "ℱ", "D": "𝒟", "E": "ℰ", "O": "𝒪", "N": "𝒩", "M": "ℳ", "P": "𝒫", "S": "𝒮", "T": "𝒯",
        "A": "𝒜", "B": "ℬ", "C": "𝒞", "H": "ℋ", "R": "ℛ", "I": "ℐ", "K": "𝒦", "U": "𝒰", "V": "𝒱", "X": "𝒳"}
MBB = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ"}
JP = re.compile(r"[　-鿿＀-￯]")


class TexError(ValueError):
    pass


# ---------------------------------------------------------------- tokenizer
def tokenize(s: str) -> list[str]:
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            if m:
                out.append("\\" + m.group(1))
                i += len(m.group(0))
            else:
                out.append(s[i:i + 2])
                i += 2
        elif c.isspace():
            out.append(" ")
            i += 1
            while i < len(s) and s[i].isspace():
                i += 1
        elif c.isdigit() or (c == "." and i + 1 < len(s) and s[i + 1].isdigit()):
            m = re.match(r"\d*\.?\d+", s[i:])
            out.append(m.group(0))
            i += len(m.group(0))
        else:
            out.append(c)
            i += 1
    return out


# ---------------------------------------------------------------- parser → tree
class Parser:
    def __init__(self, s: str):
        self.t = tokenize(s)
        self.i = 0
        self.src = s

    def peek(self, skip_space=True):
        j = self.i
        while skip_space and j < len(self.t) and self.t[j] == " ":
            j += 1
        return self.t[j] if j < len(self.t) else None

    def next(self, skip_space=True):
        while skip_space and self.i < len(self.t) and self.t[self.i] == " ":
            self.i += 1
        if self.i >= len(self.t):
            raise TexError(f"式が途中で終わる: {self.src}")
        tok = self.t[self.i]
        self.i += 1
        return tok

    def parse(self):
        row = self.expr(stop=set())
        if self.i < len(self.t) and self.peek() is not None:
            raise TexError(f"余分な記号 {self.peek()!r}: {self.src}")
        return row

    def expr(self, stop):
        items = []
        while True:
            p = self.peek()
            if p is None or p in stop:
                break
            if p == "}":
                if "}" in stop:
                    break
                raise TexError(f"対応しない }}: {self.src}")
            items.append(self.scripted())
        return ("row", items)

    def group_or_atom(self):
        p = self.peek()
        if p == "{":
            self.next()
            r = self.expr(stop={"}"})
            if self.next() != "}":
                raise TexError(f"}} が無い: {self.src}")
            return r
        return self.atom()

    def raw_group(self) -> str:
        """{…} の中身を文字列のまま（\\text など）。"""
        if self.next() != "{":
            raise TexError(f"{{ が必要: {self.src}")
        depth, buf = 1, []
        while True:
            if self.i >= len(self.t):
                raise TexError(f"}} が無い: {self.src}")
            tok = self.t[self.i]
            self.i += 1
            if tok == "{":
                depth += 1
            elif tok == "}":
                depth -= 1
                if depth == 0:
                    break
            buf.append(tok)
        return "".join(buf)

    def scripted(self):
        base = self.atom()
        sub = sup = None
        primes = 0
        while self.peek() in ("^", "_", "'"):
            tok = self.next()
            if tok == "'":
                primes += 1
                continue
            arg = self.group_or_atom()
            if tok == "^":
                if sup is not None:
                    raise TexError(f"上付きが二重: {self.src}")
                sup = arg
            else:
                if sub is not None:
                    raise TexError(f"下付きが二重: {self.src}")
                sub = arg
        if primes:   # f' は上付きにせず、文字の後ろに置く（重なりを避ける）
            pr = ("mo", "′" * primes, {"prime": True})
            if sup is not None:
                sup = ("row", [pr, sup])
            else:
                core = ("sub", base, sub) if sub is not None else base
                return ("row", [core, pr])
        if sub is None and sup is None:
            return base
        if base[0] == "bigop":
            return ("bigop", base[1], base[2], sub, sup)
        if base[0] == "limop":
            return ("limop", base[1], sub)
        if sub is not None and sup is not None:
            return ("subsup", base, sub, sup)
        return ("sub", base, sub) if sub is not None else ("sup", base, sup)

    def atom(self):
        tok = self.next()
        if tok == "{":
            r = self.expr(stop={"}"})
            self.next()
            return r
        if tok.startswith("\\"):
            return self.command(tok[1:])
        if re.fullmatch(r"\d*\.?\d+", tok):
            return ("mn", tok)
        if tok.isalpha() and not JP.search(tok):
            return ("mi", tok, "italic")
        if JP.search(tok):
            raise TexError(f"日本語は \\text{{}} に入れる: {self.src}")
        if tok in "+-=<>()[]|,;:!/*.?":
            return ("mo", {"-": "−", "*": "∗"}.get(tok, tok), {})
        if tok == "&":
            raise TexError(f"& は表の環境の中だけ: {self.src}")
        return ("mo", tok, {})

    def command(self, name: str):
        if name in GREEK:
            ch = GREEK[name]
            return ("mi", ch, "normal" if ch in UPRIGHT_GREEK else "italic")
        if name in SYMBOLS:
            return ("mo", SYMBOLS[name], {})
        if name in SPACES:
            return ("space", SPACES[name])
        if name in ("{", "}", "#", "%", "&", "$"):
            return ("mo", name, {})
        if name == "|":
            return ("mo", "‖", {})
        if name == "\\":
            raise TexError(f"\\\\ は表の環境の中だけ: {self.src}")
        if name in BIGOPS:
            return ("bigop", BIGOPS[name], name == "int" or name.startswith("i") or name == "oint")
        if name in LIMOPS:
            return ("limop", name)
        if name in FUNCS:
            return ("mi", name, "normal")
        if name in ("frac", "dfrac", "tfrac"):
            a = self.group_or_atom()
            b = self.group_or_atom()
            return ("frac", a, b)
        if name == "sqrt":
            n = None
            if self.peek() == "[":
                self.next()
                n = self.expr(stop={"]"})
                self.next()
            return ("sqrt", self.group_or_atom(), n)
        if name in ("text", "textrm", "mbox"):
            return ("mtext", self.raw_group())
        if name in ("mathrm", "operatorname", "rm", "mathbf", "boldsymbol", "bm"):
            raw = self.raw_group()
            variant = "bold" if name in ("mathbf", "boldsymbol", "bm") else "normal"
            if re.fullmatch(r"[A-Za-z0-9 .\-]+", raw) and "_" not in raw and "^" not in raw:
                return ("mi", raw.replace(" ", ""), variant)
            return _restyle(Parser(raw).parse(), variant)
        if name == "mathit":
            return ("mi", self.raw_group().replace(" ", ""), "italic")
        if name == "mathcal":
            g = self.raw_group().strip()
            return ("mi", "".join(MCAL.get(c, c) for c in g), "normal")
        if name == "mathbb":
            g = self.raw_group().strip()
            return ("mi", "".join(MBB.get(c, c) for c in g), "normal")
        if name in ACCENTS:
            return ("accent", self.group_or_atom(), ACCENTS[name], name in ("overline", "widehat"))
        SIZES = {"big": 1.2, "Big": 1.6, "bigg": 2.0, "Bigg": 2.5}
        base = name[:-1] if name.endswith(("l", "r")) and name[:-1] in SIZES else name
        if base in SIZES:
            return ("mo", self.delim(), {"size": SIZES[base]})
        if name in ("left", "right"):
            if name != "left":
                raise TexError(f"\\{name} の対応する \\left が無い: {self.src}")
            open_ = self.delim()
            body = self.expr(stop={"\\right"})
            if self.next() != "\\right":
                raise TexError(f"\\right が無い: {self.src}")
            close = self.delim()
            return ("fenced", open_, body, close)
        if name == "begin":
            env = self.raw_group()
            if env == "array":
                self.raw_group()
            return self.environment(env)
        if name == "underbrace":
            body = self.group_or_atom()
            lab = None
            if self.peek() == "_":
                self.next()
                lab = self.group_or_atom()
            return ("underbrace", body, lab)
        raise TexError(f"知らない命令 \\{name}: {self.src}")

    def delim(self) -> str:
        tok = self.next()
        if tok == ".":
            return ""
        if tok.startswith("\\"):
            n = tok[1:]
            if n in SYMBOLS:
                return SYMBOLS[n]
            if n in ("{", "}"):
                return n
            if n == "|":
                return "‖"
            raise TexError(f"区切りに使えない {tok}: {self.src}")
        return tok

    def environment(self, env: str):
        rows, row, cell = [], [], []
        while True:
            p = self.peek()
            if p is None:
                raise TexError(f"\\end{{{env}}} が無い: {self.src}")
            if p == "\\end":
                self.next()
                e = self.raw_group()
                if e != env:
                    raise TexError(f"環境の対応が違う {env}/{e}: {self.src}")
                break
            if p == "&":
                self.next()
                row.append(("row", cell))
                cell = []
                continue
            if p == "\\\\":
                self.next()
                row.append(("row", cell))
                rows.append(row)
                row, cell = [], []
                continue
            cell.append(self.scripted())
        if cell or row:
            row.append(("row", cell))
            rows.append(row)
        if env not in ("cases", "aligned", "align", "array", "pmatrix", "bmatrix", "matrix", "gathered"):
            raise TexError(f"知らない環境 {env}: {self.src}")
        return ("table", env, rows)


def _restyle(node, variant: str):
    """\\mathrm{…}・\\mathbf{…} の中の文字（mi）を立体・太字にする。隣り合う 1 文字の mi はまとめて 1 語にする。"""
    k = node[0]
    if k == "mi":
        return ("mi", node[1], variant)
    if k == "row":
        items, buf = [], ""
        for x in node[1]:
            x = _restyle(x, variant)
            if x[0] == "mi":
                buf += x[1]
                continue
            if buf:
                items.append(("mi", buf, variant))
                buf = ""
            items.append(x)
        if buf:
            items.append(("mi", buf, variant))
        return ("row", items)
    if k in ("sub", "sup"):
        return (k, _restyle(node[1], variant), _restyle(node[2], variant))
    if k == "subsup":
        return (k, _restyle(node[1], variant), _restyle(node[2], variant), _restyle(node[3], variant))
    return node


def parse(tex: str):
    return Parser(tex).parse()


# ---------------------------------------------------------------- MathML
def _mo(s, stretchy=False, extra=""):
    st = "" if stretchy else ' stretchy="false"'
    if s in "()[]|⌈⌉⌊⌋⟨⟩{}‖":
        return f"<mo{st}{extra}>{escape(s)}</mo>"
    return f"<mo{extra}>{escape(s)}</mo>"


def mml(n, display=True) -> str:
    k = n[0]
    if k == "row":
        return "<mrow>" + "".join(mml(x, display) for x in n[1]) + "</mrow>"
    if k == "mi":
        v = n[2]
        attr = "" if (v == "italic" and len(n[1]) == 1) else (' mathvariant="normal" style="font-weight:bold"' if v == "bold" else
                                                              (' mathvariant="normal"' if len(n[1]) == 1 else ""))
        return f"<mi{attr}>{escape(n[1])}</mi>"
    if k == "mn":
        return f"<mn>{escape(n[1])}</mn>"
    if k == "mo":
        if n[2].get("prime"):
            return f'<mo lspace="0" rspace="0">{escape(n[1])}</mo>'
        if n[2].get("size"):
            sz = n[2]["size"]
            return f'<mo stretchy="true" symmetric="true" minsize="{sz}em" maxsize="{sz}em">{escape(n[1])}</mo>'
        return _mo(n[1])
    if k == "mtext":
        style = ' style="font-family:IPAGothic,IPAexGothic,sans-serif"' if JP.search(n[1]) else ""
        return f"<mtext{style}>{escape(n[1])}</mtext>"
    if k == "space":
        return f'<mspace width="{n[1]}em"/>'
    if k == "sub":
        return f"<msub>{mml(n[1], display)}{mml(n[2], display)}</msub>"
    if k == "sup":
        return f"<msup>{mml(n[1], display)}{mml(n[2], display)}</msup>"
    if k == "subsup":
        return f"<msubsup>{mml(n[1], display)}{mml(n[2], display)}{mml(n[3], display)}</msubsup>"
    if k == "frac":
        return f"<mfrac>{mml(n[1], display)}{mml(n[2], display)}</mfrac>"
    if k == "sqrt":
        if n[2] is None:
            return f"<msqrt>{mml(n[1], display)}</msqrt>"
        return f"<mroot>{mml(n[1], display)}{mml(n[2], display)}</mroot>"
    if k == "bigop":
        _, sym, integral, sub, sup = (n + (None, None))[:5] if len(n) == 3 else n
        op = f'<mo largeop="true"{" movablelimits=\"false\"" if display else ""}>{sym}</mo>'
        if sub is None and sup is None:
            return op
        if integral or not display:
            if sub is not None and sup is not None:
                return f"<msubsup>{op}{mml(sub, display)}{mml(sup, display)}</msubsup>"
            return f"<msub>{op}{mml(sub, display)}</msub>" if sub is not None else f"<msup>{op}{mml(sup, display)}</msup>"
        if sub is not None and sup is not None:
            return f"<munderover>{op}{mml(sub, display)}{mml(sup, display)}</munderover>"
        return f"<munder>{op}{mml(sub, display)}</munder>" if sub is not None else f"<mover>{op}{mml(sup, display)}</mover>"
    if k == "limop":
        name = n[1]
        base = f"<mi>{name}</mi>"
        sub = n[2] if len(n) > 2 else None
        if sub is None:
            return base
        return f"<munder>{base}{mml(sub, display)}</munder>" if display else f"<msub>{base}{mml(sub, display)}</msub>"
    if k == "accent":
        acc = n[2]
        return f'<mover accent="true">{mml(n[1], display)}<mo stretchy="{"true" if n[3] else "false"}">{escape(acc)}</mo></mover>'
    if k == "fenced":
        o = _mo(n[1], True, ' fence="true"') if n[1] else ""
        c = _mo(n[3], True, ' fence="true"') if n[3] else ""
        return f"<mrow>{o}{mml(n[2], display)}{c}</mrow>"
    if k == "underbrace":
        inner = f'<munder>{mml(n[1], display)}<mo stretchy="true">⏟</mo></munder>'
        if n[2] is not None:
            return f"<munder>{inner}{mml(n[2], display)}</munder>"
        return inner
    if k == "table":
        env, rows = n[1], n[2]
        align = {"cases": "left left", "aligned": "right left", "align": "right left"}.get(env, "center")
        ds = env in ("aligned", "align", "gathered")
        cell = (lambda c: f'<mstyle displaystyle="true">{mml(c, display)}</mstyle>') if ds else (lambda c: mml(c, display))
        pad = "0.2em 0" if env in ("aligned", "align") else "0.2em 0.5em"
        def ta(j: int) -> str:  # Chromium の MathML は columnalign を見ないので CSS で揃える
            if env == "cases":
                return "left"
            if env in ("aligned", "align"):
                return "right" if j % 2 == 0 else "left"
            return "center"
        body = "".join("<mtr>" + "".join(f'<mtd style="padding:{pad};text-align:{ta(j)}">{cell(c)}</mtd>'
                                         for j, c in enumerate(r)) + "</mtr>" for r in rows)
        gap = "0em" if env in ("aligned", "align") else "0.8em"
        tab = f'<mtable columnalign="{align}" rowspacing="0.45em" columnspacing="{gap}">{body}</mtable>'
        if env == "cases":
            return f'<mrow><mo stretchy="true" fence="true">{{</mo>{tab}</mrow>'
        if env == "pmatrix":
            return f'<mrow><mo stretchy="true">(</mo>{tab}<mo stretchy="true">)</mo></mrow>'
        if env == "bmatrix":
            return f'<mrow><mo stretchy="true">[</mo>{tab}<mo stretchy="true">]</mo></mrow>'
        return tab
    raise TexError(f"内部: 未対応の節 {k}")


def to_mathml(tex: str, display: bool = True) -> str:
    tree = parse(tex)
    return f'<math display="{"block" if display else "inline"}">{mml(tree, display)}</math>'


# ---------------------------------------------------------------- reportlab inline markup
def to_plain_node(n) -> str:
    """節の中身を飾り無しの文字列に（上線を付ける文字を取り出す）。"""
    k = n[0]
    if k == "row":
        return "".join(to_plain_node(x) for x in n[1])
    if k in ("mi", "mn", "mo", "mtext"):
        return n[1]
    return ""


def _rl(n) -> str:
    k = n[0]
    if k == "row":
        return "".join(_rl(x) for x in n[1])
    if k == "mi":
        s = escape(n[1])
        if n[2] == "bold":
            return f'<font name="MSerifB">{s}</font>'
        if n[2] == "italic" and len(n[1]) == 1 and n[1] not in UPRIGHT_GREEK:
            return f'<font name="MSerifI">{s}</font>'
        return f'<font name="MSerif">{s}</font>'
    if k == "mn":
        return f'<font name="MSerif">{escape(n[1])}</font>'
    if k == "mo":
        s = n[1]
        pad = " " if s in "=<>≤≥≠≈∈→⇒⇔+−×≡∼∝" else ""
        return f'<font name="MSerif">{pad}{escape(s)}{pad}</font>'
    if k == "mtext":
        return escape(n[1])
    if k == "space":
        return " " if n[1] > 0 else ""
    if k == "sub":
        return _rl(n[1]) + f"<sub>{_rl(n[2])}</sub>"
    if k == "sup":
        return _rl(n[1]) + f"<super>{_rl(n[2])}</super>"
    if k == "subsup":
        return _rl(n[1]) + f"<sub>{_rl(n[2])}</sub><super>{_rl(n[3])}</super>"
    if k == "frac":
        a, b = _rl(n[1]), _rl(n[2])
        wrap = lambda x, node: f"({x})" if _complex(node) else x  # noqa: E731
        return f'{wrap(a, n[1])}<font name="MSerif">/</font>{wrap(b, n[2])}'
    if k == "sqrt":
        return f'<font name="MSerif">√</font>({_rl(n[1])})'
    if k == "bigop":
        _, sym, integral, sub, sup = n if len(n) == 5 else (*n, None, None)
        s = f'<font name="MSerif">{sym}</font>'
        if sub is not None:
            s += f"<sub>{_rl(sub)}</sub>"
        if sup is not None:
            s += f"<super>{_rl(sup)}</super>"
        return s
    if k == "limop":
        s = f'<font name="MSerif">{n[1]}</font>'
        return s + (f"<sub>{_rl(n[2])}</sub>" if len(n) > 2 and n[2] is not None else "")
    if k == "accent":
        if n[2] == "¯":   # 上線（循環小数など）は文字ごとの結合用の上線で
            return "".join(f'<font name="MSerif">{escape(ch)}\u0305</font>' for ch in to_plain_node(n[1]))
        return _rl(n[1]) + f'<font name="MSerif">{escape(n[2] if n[2] != "^" else "̂")}</font>'
    if k == "fenced":
        return f'<font name="MSerif">{escape(n[1])}</font>{_rl(n[2])}<font name="MSerif">{escape(n[3])}</font>'
    if k == "underbrace":
        return _rl(n[1])
    if k == "table":
        raise TexError("文中の式に表（cases など）は使えない。表示式にする")
    raise TexError(f"内部: 未対応の節 {k}")


def _complex(node) -> bool:
    return node[0] == "row" and len([x for x in node[1] if x[0] != "space"]) > 1


def to_rl(tex: str) -> str:
    return _rl(parse(tex))


# ---------------------------------------------------------------- Word runs: [(text, italic, vertical)] vertical: 0/sub/sup
def _runs(n, v=0, out=None, flat=False):
    out = [] if out is None else out
    k = n[0]
    if k == "row":
        for x in n[1]:
            _runs(x, v, out, flat)
    elif k == "mi":
        out.append((n[1], n[2] == "italic" and len(n[1]) == 1 and n[1] not in UPRIGHT_GREEK, v, n[2] == "bold"))
    elif k in ("mn",):
        out.append((n[1], False, v, False))
    elif k == "mo":
        s = n[1]
        pad = " " if s in "=<>≤≥≠≈∈→⇒⇔+−×≡∼∝" else ""
        out.append((pad + s + pad, False, v, False))
    elif k == "mtext":
        out.append((n[1], False, v, False))
    elif k == "space":
        if n[1] > 0:
            out.append((" ", False, v, False))
    elif k in ("sub", "sup", "subsup"):
        _runs(n[1], v, out, flat)
        if k in ("sub", "subsup"):
            _runs(n[2], "sub", out, flat)
        if k == "sup":
            _runs(n[2], "sup", out, flat)
        if k == "subsup":
            _runs(n[3], "sup", out, flat)
    elif k == "frac":
        c1, c2 = _complex(n[1]), _complex(n[2])
        if c1:
            out.append(("(", False, v, False))
        _runs(n[1], v, out, flat)
        if c1:
            out.append((")", False, v, False))
        out.append(("/", False, v, False))
        if c2:
            out.append(("(", False, v, False))
        _runs(n[2], v, out, flat)
        if c2:
            out.append((")", False, v, False))
    elif k == "sqrt":
        out.append(("√(", False, v, False))
        _runs(n[1], v, out, flat)
        out.append((")", False, v, False))
    elif k == "bigop":
        _, sym, integral, sub, sup = n if len(n) == 5 else (*n, None, None)
        out.append((sym, False, v, False))
        if sub is not None:
            _runs(sub, "sub", out, flat)
        if sup is not None:
            _runs(sup, "sup", out, flat)
    elif k == "limop":
        out.append((n[1], False, v, False))
        if len(n) > 2 and n[2] is not None:
            _runs(n[2], "sub", out, flat)
    elif k == "accent":
        _runs(n[1], v, out, flat)
        out.append(({"^": "̂", "¯": "̄", "~": "̃", "˙": "̇"}.get(n[2], n[2]), False, v, False))
    elif k == "fenced":
        out.append((n[1], False, v, False))
        _runs(n[2], v, out, flat)
        out.append((n[3], False, v, False))
    elif k == "underbrace":
        _runs(n[1], v, out, flat)
    elif k == "table":
        if not flat:
            raise TexError("文中の式に表（cases など）は使えない")
        for i, r in enumerate(n[2]):
            if i:
                out.append(("; ", False, v, False))
            for c in r:
                _runs(c, v, out, flat)
                out.append((" ", False, v, False))
    return out


def to_runs(tex: str):
    return _runs(parse(tex))


def to_plain(tex: str) -> str:
    """検索・照合用の平文（下付きは _ 、上付きは ^ で表す）。"""
    s = ""
    for text, _it, v, _b in _runs(parse(tex), flat=True):
        s += ("_" + text if v == "sub" else "^" + text if v == "sup" else text)
    return s
