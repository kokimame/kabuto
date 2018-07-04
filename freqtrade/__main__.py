#!/usr/bin/env python3
"""
__main__.py for Freqtrade
To launch Freqtrade as a module

> python -m freqtrade (with Python >= 3.6)
"""

import sys

from freqtrade import main

if __name__ == '__main__':
    main.set_loggers()
    main.main(sys.argv[1:])
