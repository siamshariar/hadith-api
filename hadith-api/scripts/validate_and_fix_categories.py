#!/usr/bin/env python3
import os
import sys
import subprocess
ROOT_SCRIPT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'validate_and_fix_categories.py'))
if __name__ == '__main__':
    cmd = [sys.executable, ROOT_SCRIPT]
    print(f"Running wrapper: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    proc.wait()
    sys.exit(proc.returncode)
