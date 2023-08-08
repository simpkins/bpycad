#!/usr/bin/python3 -tt
#
# Copyright (c) 2023, Adam Simpkins
#

"""Example showing the usage of bpycad.dev_main

To use, run "blender -P export_stl.py -b"

If you want to export just specific models, pass in the model names you want
after a "--" argument.  e.g.,

  blender -P export_stl.py -b -- simple_display_holder
"""

import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from bpycad import export_stl

from examples import pcb_holder

export_stl.main({"simple_display_holder": pcb_holder.simple_display_holder})
