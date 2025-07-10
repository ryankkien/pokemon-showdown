#!/usr/bin/env python3
"""
Wrapper script to run bot tests from the root directory.
"""
import subprocess
import sys

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "tests.test_bot"]))