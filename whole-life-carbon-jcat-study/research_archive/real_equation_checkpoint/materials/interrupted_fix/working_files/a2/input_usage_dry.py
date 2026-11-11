"""bench.input_usage with its output redirected (argument 1)."""
import sys
from pathlib import Path

from bench import input_usage

input_usage.OUT = Path(sys.argv[1])
sys.exit(input_usage.main())
