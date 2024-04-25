#!/usr/bin/python3 -tt
#
# Copyright (c) 2022, Adam Simpkins
#

"""Export STL files for all of the parts.
To use, run "blender -b -P generate_stl.py"
"""

from __future__ import annotations

from . import blender_util
import bpy

import argparse
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

# A dictionary mapping names to functions that generate objects to export.
#
# If the function returns a bpy.types.Object, that object will be exported.
# The target name will be used as the output file name.
#
# If the function returns None, all objects that exist after the function
# returns will be exported.  Each object will be exported using it's object
# name to construct the output file name.
TargetDict = Dict[str, Callable[[], Optional[bpy.types.Object]]]


def main(
    targets: TargetDict,
    default: Optional[List[str]] = None,
    out_dir: Union[str, Path, None] = None,
    dflt_out_dir_name: str = "stl_out",
) -> None:
    """A main function to use for exporting STL files from CAD models.

    To use, invoke it through blender:

        blender -P your_export_script.py -b -- [SCRIPT_ARGUMENTS]

    Arguments:
    - targets:
      A dictionary of target functions that can be run to generate models to
      export.  The command line arguments control which function(s) to invoke
      and export.
    - default:
      The default targets to execute if no targets are specified on the command
      line.  If this is None, all targets will be executed by default.  If this
      is an empty list then an error will be generated if no targets are listed
      on the command line.
    - out_dir:
      The output directory to use.  May be overridden by the command-line
      --output-dir flag.  If not specified, defaults to SCRIPT_DIR/stl_out,
      where SCRIPT_DIR is the directory containing the top-level script that
      invoked this function.
    - dflt_out_dir_name
      If neither the out_dir argument nor the --output-dir command line
      argument is specified, dflt_out_dir_name is the name to append to the
      script directory to compute the output directory path.
    """
    dflt_out_dir: Optional[Path] = None
    if out_dir is not None:
        dflt_out_dir = Path(out_dir)

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "targets",
        metavar="TARGET",
        nargs="*",
        help="The targets to export",
    )
    ap.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        help="The output directory.",
        default=dflt_out_dir,
    )
    ap.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List the available targets and then exit.",
    )
    ap.add_argument(
        "--all", action="store_true", help="Export all available targets."
    )
    args = ap.parse_args(blender_util.get_script_args())

    if args.list:
        # Blender prints a couple of its own start-up messages to stdout,
        # so print a header line to help distinguish our model name output
        # from other messages already printed by blender.
        print("\n= Available Targets =\n")
        for name in sorted(targets.keys()):
            print(f"{name}")
        sys.exit(0)

    if args.output_dir is None:
        main_module = sys.modules.get("__main__", None)
        main_path = getattr(main_module, "__file__", None)
        if main_path is None:
            ap.error(
                "no --output-dir specified and unable to determine script path"
            )
        out_dir = Path(main_path).parent / dflt_out_dir_name
    else:
        out_dir = Path(args.output_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    if args.targets:
        if args.all:
            ap.error("cannot specify both --all and specific target names")
        target_names = args.targets
        unknown_names = [name for name in args.targets if name not in targets]
        if unknown_names:
            unknown_names_str = ", ".join(unknown_names)
            ap.error(f"unknown target: {unknown_names_str}")
    elif args.all:
        # Execute all targets
        target_names = sorted(targets.keys())
    elif default is None:
        ap.error(f"no target specified.  Use --list to see available targets.")
    else:
        target_names = default[:]

    blender_util.set_view_distance(350.0)
    for target_name in target_names:
        print(f"Exporting target {target_name}...")
        blender_util.delete_all()

        fn = targets[target_name]
        obj = fn()
        if isinstance(obj, bpy.types.Object):
            # Export the one object that was returned
            out_path = out_dir / f"{target_name}.stl"
            export_object(obj, out_path)
            print(f"Wrote {out_path}...")
        else:
            # Export all defined objects
            # pyre-fixme[16]: the blender type stubs are incomplete
            for obj in bpy.data.objects:
                out_path = out_dir / f"{obj.name}.stl"
                export_object(obj, out_path)
                print(f"Wrote {out_path}...")


def export_object(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)

    bpy.ops.export_mesh.stl(filepath=str(path), use_selection=True)
