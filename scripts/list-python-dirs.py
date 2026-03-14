#!/usr/bin/env python3
"""Extract unique top-level directories from file paths on stdin."""

import os
import sys

cwd = os.getcwd() + "/"
dirs = set()
for line in sys.stdin:
    path = line.strip()
    if path.startswith(cwd):
        top = path[len(cwd) :].split("/")[0]
        if top and "." not in top:
            dirs.add(top)
print(", ".join(sorted(dirs)))
