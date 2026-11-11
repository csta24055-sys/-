"""Research code of the transformation study (chapter 10).

Independent concept model, fictional data only. The reference calculation of the earlier
study is used read-only as the baseline (``tstudy.baseline``); nothing in this package
writes into ``09_APPROX_STUDY``.
"""
import sys

sys.dont_write_bytecode = True  # never create __pycache__ inside the frozen baseline folders
