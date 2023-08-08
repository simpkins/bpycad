#!/usr/bin/python3 -tt
#
# Copyright (c) 2023, Adam Simpkins
#

import bpy
from . import box
from . import pcb_holder


def main() -> None:
    """This is a very simple helper function to invoke whatever CAD model
    function you want to test during development.

    Its only purpose is to make it easy for you to change what function to
    call.  The top-level example.py script is not monitored for changes (we can
    only reload Python modules, and not the top-level script).  Therefore
    rather it is convenient to have a separate module that we can edit to
    control the real model function we want to invoke.
    """
    # pcb_holder.simple_display_holder()
    box.test()

    # Put blender in edit mode after each render
    bpy.ops.object.mode_set(mode="EDIT")
