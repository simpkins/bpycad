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
from typing import Callable, Dict, Optional, Union

ModelDict = Dict[str, Callable[[], bpy.types.Object]]


def main(
    models: ModelDict,
    out_dir: Union[str, Path, None] = None,
    dflt_out_dir_name: str = "stl_out",
) -> None:
    """A main function to use for exporting STL files from CAD models.

    To use, invoke it through blender:

        blender -P your_export_script.py -b -- [SCRIPT_ARGUMENTS]

    Arguments:
    - models:
      A dictionary of all model functions.  The command line arguments control
      whether all models will be exported or just some selection of them.
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
        "models", metavar="MODEL", nargs="*", help="The models to export"
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
        help="List the available models and then exit.",
    )
    args = ap.parse_args(blender_util.get_script_args())

    if args.list:
        # Blender prints a couple of its own start-up messages to stdout,
        # so print a header line to help distinguish our model name output
        # from other messages already printed by blender.
        print("\n= Model Names =\n")
        for name in sorted(models.keys()):
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

    if args.models:
        model_names = args.models
        unknown_names = [name for name in args.models if name not in models]
        if unknown_names:
            unknown_names_str = ", ".join(unknown_names)
            ap.error(f"unknown model: {unknown_names_str}")
    else:
        model_names = list(sorted(models.keys()))

    for name in model_names:
        export_stl(name, out_dir, models[name])

    sys.exit(0)


def export_stl(
    name: str, out_dir: Path, obj_fn: Callable[[], bpy.types.Object]
) -> None:
    print(f"Exporting {name}...")
    blender_util.delete_all()
    obj = obj_fn()

    out_path = out_dir / f"{name}.stl"
    bpy.ops.export_mesh.stl(filepath=str(out_path))
