#!/usr/bin/env python3
import os
import sys
import subprocess

ROOT_SCRIPTS = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'verify_full_import.py'))

if __name__ == '__main__':
    cmd = [sys.executable, ROOT_SCRIPTS]
    print(f"Running wrapper: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    proc.wait()
    sys.exit(proc.returncode)
