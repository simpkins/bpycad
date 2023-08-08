#!/usr/bin/python3 -tt
#
# Copyright (c) 2023, Adam Simpkins
#

from __future__ import annotations

from . import auto_update, blender_util

import argparse
from typing import List, Optional


def main(
    monitored_pkgs: List[str],
    default_fn: Optional[str] = None,
    view_distance: float = 350.0,
) -> None:
    """A main function for use when editing and developing of CAD functions.

    This function will execute the CAD code and render the resulting objects in
    blender, and then continue to monitor all of the CAD python files for
    changes.  Any time a python file is changed the CAD code will be
    automatically re-executed to update the view in blender.

    To use, write your own small module that invokes this function with your
    desired set of packages to monitor and (optionally) a default function to
    run. Then run your script with blender.  e.g., if your script is named
    dev.py, then run:

        blender -P dev.py

    Note that if you need to pass in arguments to this script, you must
    specify them on the command line after a "--" argument, to separate blender
    arguments from your script arguments.
    """

    if default_fn:
        fn_nargs = "?"
    else:
        fn_nargs = 1

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "function",
        metavar="FUNCTION",
        nargs=fn_nargs,
        help="The function to execute",
        default=default_fn,
    )
    args = ap.parse_args(blender_util.get_script_args())

    blender_util.set_view_distance(view_distance)

    auto_update.main(args.function, monitored_pkgs)
