"""Make the project root importable so tests can `import text_format`, etc.,
regardless of the working directory pytest is invoked from."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
