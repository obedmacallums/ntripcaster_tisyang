#!/usr/bin/env python3
"""
NTRIP Caster launcher script
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pycaster.main import main

if __name__ == '__main__':
    main()
