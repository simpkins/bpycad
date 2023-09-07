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

import abc
import argparse
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Union

ModelDict = Dict[str, Callable[[], bpy.types.Object]]


class ObjectGenerator(abc.ABC):
    """
    An interface class for code that generates multiple objects.

    In some cases you may have multiple objects that get generated together by
    the same code (for instance, because the parameters of one object affect
    the others).  When exporting them a STL files you want to export them as
    separate files, or you may only want to export specific objects from the
    group.

    This class makes allows you to define a function to generate a group of
    objects and define the names of the objects that will be generated.
    """

    _objects: Optional[Dict[str, bpy.types.Object]] = None

    # Subclasses should set object_names
    object_names: List[str]

    def get_objects(self) -> Dict[str, bpy.types.Object]:
        objects = self._objects
        if objects is None:
            objects = self.generate_objects()
            generated_names = list(sorted(objects.keys()))
            expected_names = sorted(self.object_names)
            if generated_names != expected_names:
                raise Exception(
                    f"object generator {type(self)} did not generate the "
                    f"expected objects: {generated_names} != {expected_names}"
                )
            self._objects = objects

        return objects

    def get_object(self, name: str) -> bpy.types.Object:
        return self.get_objects()[name]

    @abc.abstractmethod
    def generate_objects(self) -> Dict[str, bpy.types.Object]:
        raise NotImplementedError()


class SimpleGenerator(ObjectGenerator):
    def __init__(self, name: str, fn: Callable[[], bpy.types.Object]) -> None:
        self.name = name
        self.object_names: List[str] = [name]
        self.fn = fn

    def generate_objects(self) -> Dict[str, bpy.types.Object]:
        obj = self.fn()
        return {self.name: obj}


def _get_models(
    models: Optional[ModelDict],
    generators: Optional[Sequence[ObjectGenerator]],
) -> Dict[str, ObjectGenerator]:
    model_dict: Dict[str, ObjectGenerator] = {}
    if generators is not None:
        for gen in generators:
            for name in gen.object_names:
                if name in model_dict:
                    raise Exception(
                        f"multiple generators specified for object {name}"
                    )
                model_dict[name] = gen

    if models is not None:
        for name, fn in models.items():
            if name in model_dict:
                raise Exception(
                    f"multiple generators specified for object {name}"
                )
            model_dict[name] = SimpleGenerator(name, fn)

    return model_dict


def main(
    models: ModelDict,
    generators: Optional[Sequence[ObjectGenerator]] = None,
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

    model_dict = _get_models(models, generators)
    if args.list:
        # Blender prints a couple of its own start-up messages to stdout,
        # so print a header line to help distinguish our model name output
        # from other messages already printed by blender.
        print("\n= Model Names =\n")
        for name in sorted(model_dict.keys()):
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
        unknown_names = [
            name for name in args.models if name not in model_dict
        ]
        if unknown_names:
            unknown_names_str = ", ".join(unknown_names)
            ap.error(f"unknown model: {unknown_names_str}")
    else:
        model_names = list(sorted(model_dict.keys()))

    for name in model_names:
        print(f"Exporting {name}...")
        out_path = out_dir / f"{name}.stl"

        gen = model_dict[name]
        obj = gen.get_object(name)
        export_object(obj, out_path)

    sys.exit(0)


def export_object(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)

    bpy.ops.export_mesh.stl(filepath=str(path), use_selection=True)
