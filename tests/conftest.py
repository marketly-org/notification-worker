"""conftest — puts the repo root on sys.path so `from app...` works."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
