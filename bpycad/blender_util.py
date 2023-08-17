#!/usr/bin/python3 -tt
#
# Copyright (c) 2022, Adam Simpkins
#

# Note: most of the pyre-fixme comments in this file are due to the fact
# that the type annotations provided by the blender-stubs package do not
# accurately reflect the actual behavior of the blender C API.

from __future__ import annotations

import math
import random
import sys
from typing import Dict, List, Optional, Sequence, Tuple, Type, Union
from types import TracebackType

import bpy
import bmesh
import mathutils

from . import cad


def delete_all() -> None:
    if bpy.context.object is not None:
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def set_view_distance(distance: float) -> None:
    """Update the camera distance in all viewport panels"""
    # pyre-fixme[16]
    layout = bpy.data.screens["Layout"]
    view_areas = [a for a in layout.areas if a.type == "VIEW_3D"]
    for a in view_areas:
        region = a.spaces.active.region_3d
        region.view_distance = distance


def blender_mesh(name: str, mesh: cad.Mesh) -> bpy.types.Mesh:
    points = [(p.x, p.y, p.z) for p in mesh.points]
    faces = [tuple(reversed(f)) for f in mesh.faces]

    # pyre-fixme[16]
    blender_mesh: bpy.types.Mesh = bpy.data.meshes.new(name)
    blender_mesh.from_pydata(points, edges=[], faces=faces)
    blender_mesh.update()
    return blender_mesh


def new_mesh_obj(
    name: str, mesh: Union[cad.Mesh, bpy.types.Mesh]
) -> bpy.types.Object:
    if isinstance(mesh, cad.Mesh):
        mesh = blender_mesh(f"{name}_mesh", mesh)

    # pyre-fixme[16]
    obj: bpy.types.Object = bpy.data.objects.new(name, mesh)
    # pyre-fixme[16]
    collection = bpy.data.collections[0]
    collection.objects.link(obj)

    # Select the newly created object
    obj.select_set(True)
    # pyre-fixme[16]
    bpy.context.view_layer.objects.active = obj

    return obj


def boolean_op(
    obj1: bpy.types.Object,
    obj2: bpy.types.Object,
    op: str,
    apply_mod: bool = True,
    dissolve_angle: Optional[float] = None,
) -> None:
    """
    Modifies obj1 by performing a boolean operation with obj2.

    If apply_mod is True, the modifier is applied and obj2 is deleted before reutrning.
    if apply_mod is False, obj2 cannot be deleted before applying the modifier.

    If dissolve_angle is not None, a dissolve_limited() operator will be
    applied after the operator, with the specified angle limit.  dissolve_angle
    should be specified in degrees (rather than radians).
    """
    bpy.ops.object.select_all(action="DESELECT")
    obj1.select_set(True)
    # pyre-fixme[16]
    bpy.context.view_layer.objects.active = obj1

    randn = random.randint(0, 1000000)
    mod_name = f"bool_op_{randn}"
    # pyre-fixme[16]
    mod = obj1.modifiers.new(name=mod_name, type="BOOLEAN")
    mod.object = obj2
    mod.operation = op
    mod.double_threshold = 1e-12

    if apply_mod:
        bpy.ops.object.modifier_apply(modifier=mod.name)

        bpy.ops.object.select_all(action="DESELECT")
        obj2.select_set(True)
        bpy.ops.object.delete(use_global=False)

        # Enter edit mode
        bpy.ops.object.mode_set(mode="EDIT")

        # Merge vertices that are close together
        # Do this after every boolean operator, otherwise blender ends up
        # leaving slightly bad geometry in some cases where the intersections
        # are close to existing vertices.
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles()
        if dissolve_angle is not None:
            rad = math.radians(dissolve_angle)
            bpy.ops.mesh.dissolve_limited(angle_limit=rad)
        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.object.mode_set(mode="OBJECT")


def difference(
    obj1: bpy.types.Object,
    obj2: bpy.types.Object,
    apply_mod: bool = True,
    dissolve_angle: Optional[float] = None,
) -> None:
    boolean_op(
        obj1,
        obj2,
        "DIFFERENCE",
        apply_mod=apply_mod,
        dissolve_angle=dissolve_angle,
    )


def union(
    obj1: bpy.types.Object,
    obj2: bpy.types.Object,
    apply_mod: bool = True,
    dissolve_angle: Optional[float] = None,
) -> None:
    boolean_op(
        obj1, obj2, "UNION", apply_mod=apply_mod, dissolve_angle=dissolve_angle
    )


def intersect(
    obj1: bpy.types.Object,
    obj2: bpy.types.Object,
    apply_mod: bool = True,
    dissolve_angle: Optional[float] = None,
) -> None:
    boolean_op(
        obj1,
        obj2,
        "INTERSECT",
        apply_mod=apply_mod,
        dissolve_angle=dissolve_angle,
    )


def apply_to_wall(
    obj: bpy.types.Object,
    left: cad.Point,
    right: cad.Point,
    x: float = 0.0,
    z: float = 0.0,
) -> None:
    """Move the object on the X and Y axes so that it is centered on the
    wall between the left and right wall endpoints.

    The face of the object should be on the Y axis (this face will be aligned
    on the wall), and it should be centered on the X axis in order to end up
    centered on the wall.
    """
    wall_len = math.sqrt(((right.y - left.y) ** 2) + ((right.x - left.x) ** 2))
    angle = math.atan2(right.y - left.y, right.x - left.x)

    with TransformContext(obj) as ctx:
        # Move the object along the x axis so it ends up centered on the wall.
        # This assumes the object starts centered around the origin.
        #
        # Also apply any extra X and Z translation supplied by the caller.
        ctx.translate(x + wall_len * 0.5, 0.0, z)

        # Next rotate the object so it is at the same angle to the x axis
        # as the wall.
        ctx.rotate(math.degrees(angle), "Z")

        # Finally move the object from the origin so it is at the wall location
        ctx.translate(left.x, left.y, 0.0)


class TransformContext:
    def __init__(self, obj: bpy.types.Object) -> None:
        self.obj = obj
        # pyre-fixme: 20
        self.bmesh = bmesh.new()
        self.bmesh.from_mesh(obj.data)

    def __enter__(self) -> TransformContext:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if exc_value is None:
            self.bmesh.to_mesh(self.obj.data)
        self.bmesh.free()

    def rotate(
        self,
        angle: float,
        axis: str,
        center: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        if center is None:
            center = (0.0, 0.0, 0.0)

        # pyre-fixme[20]
        bmesh.ops.rotate(
            self.bmesh,
            verts=self.bmesh.verts,
            cent=center,
            matrix=mathutils.Matrix.Rotation(math.radians(angle), 3, axis),
        )

    def translate(self, x: float, y: float, z: float) -> None:
        # pyre-fixme[20]
        bmesh.ops.translate(self.bmesh, verts=self.bmesh.verts, vec=(x, y, z))

    def scale(self, x: float, y: float, z: float) -> None:
        # pyre-fixme[20]
        bmesh.ops.scale(self.bmesh, vec=(x, y, z))

    def transform(self, tf: cad.Transform) -> None:
        matrix = mathutils.Matrix(tf._data)
        # pyre-fixme[20]
        bmesh.ops.transform(self.bmesh, verts=self.bmesh.verts, matrix=matrix)

    def triangulate(self) -> None:
        # pyre-fixme[20]
        bmesh.ops.triangulate(self.bmesh, faces=self.bmesh.faces[:])

    def mirror_x(self) -> None:
        geom = self.bmesh.faces[:] + self.bmesh.verts[:] + self.bmesh.edges[:]
        # Mirror creates new mirrored geometry
        # Set merge_dist to a negative value to prevent any of the new mirrored
        # geometry from being merged with the original vertices.
        # pyre-fixme[20]
        ret = bmesh.ops.mirror(
            self.bmesh, geom=geom, axis="X", merge_dist=-1.0
        )
        # Delete the original geometry
        # pyre-fixme[20]
        bmesh.ops.delete(self.bmesh, geom=geom)
        # Reverse the faces to restore the correct normal direction
        # pyre-fixme[20]
        bmesh.ops.reverse_faces(self.bmesh, faces=self.bmesh.faces[:])


def set_shading_mode(mode: str) -> None:
    # pyre-fixme[16]
    for area in bpy.context.workspace.screens[0].areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = mode


def cube(x: float, y: float, z: float, name: str = "cube") -> bpy.types.Object:
    mesh = cad.cube(x, y, z)
    return new_mesh_obj(name, mesh)


def range_cube(
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    z_range: Tuple[float, float],
    name: str = "cube",
) -> bpy.types.Object:
    mesh = cad.range_cube(x_range, y_range, z_range)
    return new_mesh_obj(name, mesh)


def cylinder(
    r: float,
    h: Union[float, Tuple[float, float]],
    fn: int = 24,
    rotation: float = 360.0,
    name: str = "cylinder",
    r2: Optional[float] = None,
) -> bpy.types.Object:
    mesh = cad.cylinder(r, h, fn=fn, rotation=rotation, r2=r2)
    return new_mesh_obj(name, mesh)


def cone(
    r: float,
    h: float,
    fn: int = 24,
    rotation: float = 360.0,
    name: str = "cylinder",
) -> bpy.types.Object:
    mesh = cad.cone(r, h, fn=fn, rotation=rotation)
    return new_mesh_obj(name, mesh)


class Beveler:
    """
    A helper class for applying bevels to the edges of a Mesh.
    """

    _bevel_edges: Dict[Tuple[int, int], float]

    def __init__(self) -> None:
        self._bevel_edges = {}

    def bevel_edge(
        self, p0: cad.MeshPoint, p1: cad.MeshPoint, weight: float = 1.0
    ) -> None:
        """Set the bevel weight for an edge"""
        if p0.index < p1.index:
            key = p0.index, p1.index
        else:
            key = p1.index, p0.index
        self._bevel_edges[key] = weight

    def get_bevel_weights(
        self, edges: Sequence[bpy.types.MeshEdge]
    ) -> Dict[int, float]:
        results: Dict[int, float] = {}
        for idx, e in enumerate(edges):
            v0 = e.vertices[0]
            v1 = e.vertices[1]
            if v0 < v1:
                key = v0, v1
            else:
                key = v1, v0

            weight = self._bevel_edges.get(key, 0.0)
            if weight > 0.0:
                results[idx] = weight

        return results

    def apply_bevels(
        self, obj: bpy.types.Object, width: float = 2.0, segments: int = 8
    ) -> None:
        mesh = obj.data
        assert isinstance(
            mesh, bpy.types.Mesh
        ), "bevels can only be applied to mesh objects"
        # pyre-fixme[6]: blender type stubs don't make it clear that mesh.edges
        #   always behaves as a sequence of MeshEdges
        edge_weights = self.get_bevel_weights(mesh.edges)
        for edge_idx, weight in edge_weights.items():
            # pyre-fixme[16]: incomplete bpy type annotations
            e = mesh.edges[edge_idx]
            e.bevel_weight = weight

        # Create the bevel modifier
        # pyre-fixme[16]: incomplete bpy type annotations
        bevel = obj.modifiers.new(name="BevelCorners", type="BEVEL")
        bevel.width = width
        bevel.limit_method = "WEIGHT"
        bevel.segments = segments

        # Apply the modifier
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.ops.object.modifier_apply(modifier=bevel.name)

        # Enter edit mode
        bpy.ops.object.mode_set(mode="EDIT")

        # Merge vertices that are close together
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.object.mode_set(mode="OBJECT")


def get_script_args() -> List[str]:
    """
    Get the additional command line arguments that were passed to the
    script when invoking blender.  This returns all arguments after "--".

    The return value can be passed to argparse.ArgumentParser.parse_args()
    """
    for idx, arg in enumerate(sys.argv):
        if arg == "--":
            return sys.argv[idx + 1 :]
    return []
