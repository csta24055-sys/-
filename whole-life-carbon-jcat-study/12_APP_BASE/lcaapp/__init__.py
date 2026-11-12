"""Base system of the building LCA app: common input data (2), result display (4), storage (5).

The calculation itself is done by the existing two-structure engine
(``10_TRANSFORM_STUDY/research_code/tstudy/unified.py``), which this package calls and never
modifies. The engine is an independent concept model verified on fictional data only; it is
not a re-implementation of any other tool.
"""
import sys

sys.dont_write_bytecode = True          # never leave __pycache__ in the frozen research folders

APP_VERSION = "0.1.0"
INPUT_FORMAT = "lca-input/1"            # input document (classification item space)
COMMON_FORMAT = "lca-common/1"          # common internal format (engine model space, with states)
REFSET_FORMAT = "lca-refset/1"          # reference data set (factors and standard values)

DATA_KINDS = ("fictional", "real", "unknown")
