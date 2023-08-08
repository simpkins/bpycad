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

ModuleDict = Dict[str, Callable[[], bpy.types.Object]]


def export_stl(
    name: str, out_dir: Path, obj_fn: Callable[[], bpy.types.Object]
) -> None:
    print(f"Exporting {name}...")
    blender_util.delete_all()
    obj = obj_fn()

    out_path = out_dir / f"{name}.stl"
    bpy.ops.export_mesh.stl(filepath=str(out_path))


def main(models: ModuleDict, out_dir: Union[str, Path, None] = None) -> None:
    """A main function to use for exporting STL files from CAD models.

    To use, invoke it through blender:

        blender -P dev.py -b -- [SCRIPT_ARGUMENTS]
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
        help="The output directory",
        default=dflt_out_dir,
    )
    args = ap.parse_args(blender_util.get_script_args())

    if args.output_dir is None:
        main_module = sys.modules.get("__main__", None)
        main_path = getattr(main_module, "__file__", None)
        if main_path is None:
            ap.error(
                "no --output-dir specified and unable to determine script path"
            )
        out_dir = Path(main_path).parent / "_out"
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
