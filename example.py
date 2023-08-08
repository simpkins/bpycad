#!/usr/bin/python3 -tt
#
# Copyright (c) 2023, Adam Simpkins
#

"""Example showing the usage of bpycad.dev_main

To use, run "blender -P example.py"

This script will execute the CAD code and render the resulting object(s) in
blender.  Whenever you make changes to any of the CAD source files the models
will automatically be re-generated in Blender, letting you see an up-to-date
view whenever you save your code.
"""

import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from bpycad import dev_main

dev_main.main(["bpycad", "examples"], "examples.dev.main")
