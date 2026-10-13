#!/usr/bin/env python3
"""Same path as the monorepo (`scripts/verify_clock.py`); runs demo/verify_clock.py.

  python scripts/verify_clock.py --digest <64 hex> --base https://api.metrecept.co.uk
  python scripts/verify_clock.py --receipt <jws> --base https://api.metrecept.co.uk
"""
import os
import runpy
import sys

_target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo", "verify_clock.py")
sys.argv[0] = _target
runpy.run_path(_target, run_name="__main__")
