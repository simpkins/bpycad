#!/usr/bin/python3 -tt
#
# Copyright (c) 2022, Adam Simpkins
#

from __future__ import annotations

import math
import random
import sys
from typing import cast, Dict, List, Optional, Sequence, Tuple, Type, Union
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
    layout = bpy.data.screens["Layout"]
    view_areas = [a for a in layout.areas if a.type == "VIEW_3D"]
    for a in view_areas:
        region = cast(bpy.types.SpaceView3D, a.spaces.active).region_3d
        region.view_distance = distance


def blender_mesh(name: str, mesh: cad.Mesh) -> bpy.types.Mesh:
    points = [(p.x, p.y, p.z) for p in mesh.points]
    faces = [tuple(reversed(f)) for f in mesh.faces]

    blender_mesh: bpy.types.Mesh = bpy.data.meshes.new(name)
    blender_mesh.from_pydata(points, edges=[], faces=faces)
    blender_mesh.update()
    return blender_mesh


def new_mesh_obj(
    name: str, mesh: Union[cad.Mesh, bpy.types.Mesh]
) -> bpy.types.Object:
    if isinstance(mesh, cad.Mesh):
        mesh = blender_mesh(f"{name}_mesh", mesh)

    obj: bpy.types.Object = bpy.data.objects.new(name, mesh)
    collection = bpy.data.collections[0]
    collection.objects.link(obj)

    # Select the newly created object
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    return obj


def dissolve_limited(obj: bpy.types.Object, angle: float) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    rad = math.radians(angle)
    bpy.ops.mesh.dissolve_limited(angle_limit=rad)

    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")


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
    bpy.context.view_layer.objects.active = obj1

    randn = random.randint(0, 1000000)
    mod_name = f"bool_op_{randn}"
    mod = cast(
        bpy.types.BooleanModifier,
        obj1.modifiers.new(name=mod_name, type="BOOLEAN"),
    )
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


def apply_to_wall_transform(
    left: cad.Point, right: cad.Point, x: float = 0.0, z: float = 0.0
) -> cad.Transform:
    wall_len = math.sqrt(((right.y - left.y) ** 2) + ((right.x - left.x) ** 2))
    angle = math.atan2(right.y - left.y, right.x - left.x)

    tf = cad.Transform()

    # Move the object along the x axis so it ends up centered on the wall.
    # This assumes the object starts centered around the origin.
    #
    # Also apply any extra X and Z translation supplied by the caller.
    tf = tf.translate(x + wall_len * 0.5, 0.0, z)

    # Next rotate the object so it is at the same angle to the x axis
    # as the wall.
    tf = tf.rotate_radians(0.0, 0.0, angle)

    # Finally move the object from the origin so it is at the wall location
    tf = tf.translate(left.x, left.y, 0.0)

    return tf


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
    tf = apply_to_wall_transform(left, right, x, z)
    with TransformContext(obj) as ctx:
        ctx.transform(tf)


class TransformContext:
    def __init__(self, obj: bpy.types.Object) -> None:
        self.obj = obj
        self.bmesh: bmesh.types.BMesh = bmesh.new()
        # pyre-fixme[6]: obj.data must be a Mesh
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
            # pyre-fixme[6]: obj.data must be a Mesh
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

        bmesh.ops.rotate(
            self.bmesh,
            verts=self.bmesh.verts,
            cent=center,
            matrix=mathutils.Matrix.Rotation(math.radians(angle), 3, axis),
        )

    def translate(self, x: float, y: float, z: float) -> None:
        bmesh.ops.translate(self.bmesh, verts=self.bmesh.verts, vec=(x, y, z))

    def scale(self, x: float, y: float, z: float) -> None:
        bmesh.ops.scale(self.bmesh, verts=self.bmesh.verts, vec=(x, y, z))

    def transform(self, tf: cad.Transform) -> None:
        matrix = mathutils.Matrix(tf._data)
        bmesh.ops.transform(self.bmesh, verts=self.bmesh.verts, matrix=matrix)

    def triangulate(self) -> None:
        bmesh.ops.triangulate(self.bmesh, faces=self.bmesh.faces[:])

    def mirror_x(self) -> None:
        geom = self.bmesh.faces[:] + self.bmesh.verts[:] + self.bmesh.edges[:]
        # Mirror creates new mirrored geometry
        # Set merge_dist to a negative value to prevent any of the new mirrored
        # geometry from being merged with the original vertices.
        ret = bmesh.ops.mirror(
            self.bmesh, geom=geom, axis="X", merge_dist=-1.0
        )
        # Delete the original geometry
        bmesh.ops.delete(self.bmesh, geom=geom)
        # Reverse the faces to restore the correct normal direction
        bmesh.ops.reverse_faces(self.bmesh, faces=self.bmesh.faces[:])


def set_shading_mode(mode: str) -> None:
    for area in bpy.context.workspace.screens[0].areas:
        for space in area.spaces:
            if space.type == "VIEW_3D":
                space.shading.type = mode


def cube(
    x: float | Tuple[float, float],
    y: float | Tuple[float, float],
    z: float | Tuple[float, float],
    name: str = "cube",
) -> bpy.types.Object:
    mesh = cad.cube(x, y, z)
    return new_mesh_obj(name, mesh)


def range_cube(
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    z_range: Tuple[float, float],
    name: str = "cube",
) -> bpy.types.Object:
    """Deprecated.  Use cube() instead."""
    return cube(x_range, y_range, z_range, name)


def wedge(
    p0: cad.Point2D | Tuple[float, float],
    p1: cad.Point2D | Tuple[float, float],
    p2: cad.Point2D | Tuple[float, float],
    length: float,
    name: str = "wedge",
) -> bpy.types.Object:
    mesh = cad.wedge(p0, p1, p2, length)
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


def text(
    text: str,
    size: float = 10.0,
    h: float = 1.0,
    align_x: str = "LEFT",
    align_y: str = "TOP_BASELINE",
    font_path: Optional[str] = None,
    resolution: int = 12,
    name: str = "text",
) -> bpy.types.Object:

    # Blender's curve-to-mesh logic unfortunately generates a lot of
    # non-manifold geometry.  Therefore we have to be pretty careful about how
    # we use it in order to produce a sane mesh.
    # https://projects.blender.org/blender/blender/issues/117468
    #
    # - We avoid using the TextCurve.extrude parameter, and instead just use
    #   TextCurve to generate a flat 2D mesh which we extrude separately.
    #   TextCurve.extrude unfortunately produces a mesh where the side walls
    #   are not connected to the top and bottom.
    # - Even when generating just a flat mesh, TextCurve to mesh conversion
    #   will still produce non-manifold edges where two adjacent faces do not
    #   share the same edge.  We have to call beautify_fill() before extruding.

    font_curve = text_curve(
        text,
        size=size,
        align_x=align_x,
        align_y=align_y,
        font_path=font_path,
        resolution=resolution,
        name=name,
    )
    return text_curve_to_mesh_object(font_curve, extrude=h, name=name)


def text_curve(
    text: str,
    size: float = 10.0,
    align_x: str = "LEFT",
    align_y: str = "TOP_BASELINE",
    font_path: Optional[str] = None,
    resolution: int = 12,
    name: str = "text",
) -> bpy.types.TextCurve:
    font_curve = cast(
        bpy.types.TextCurve,
        bpy.data.curves.new(type="FONT", name=f"{name}_curve"),
    )
    font_curve.body = text
    font_curve.size = size
    font_curve.align_x = align_x
    font_curve.align_y = align_y
    font_curve.resolution_u = resolution

    if font_path is not None:
        font = bpy.data.fonts.load(font_path)
        font_curve.font = font

    return font_curve


def text_curve_to_mesh_object(
    font_curve: bpy.types.TextCurve, extrude: float = 0.0, name: str = "text"
) -> bpy.types.Object:
    curve_obj = bpy.data.objects.new(
        name=f"{name}_curve_obj", object_data=font_curve
    )

    mesh = bpy.data.meshes.new_from_object(curve_obj)
    mesh_obj = bpy.data.objects.new(name, mesh)
    collection = bpy.data.collections[0]
    collection.objects.link(mesh_obj)
    bpy.data.objects.remove(curve_obj, do_unlink=True)

    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj

    # Converting a TextCurve to a mesh unfortunately produces non-manifold
    # geometry.  Run beautify_fill() to attempt to clean up non-manifold faces.
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    bpy.ops.mesh.beautify_fill()

    # If extrude was requested, apply the extrusion now.
    # Don't use the TextCurve.extrude property, since this produces
    # non-manifold geometry.
    if extrude:
        bpy.ops.mesh.extrude_region()
        bpy.ops.transform.translate(value=(0, 0, extrude))

    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")

    return mesh_obj


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
        edge_weights = self.get_bevel_weights(mesh.edges)

        edge_weights_attr = mesh.attributes.get("bevel_weight_edge")
        if edge_weights_attr is None:
            edge_weights_attr = mesh.attributes.new(
                "bevel_weight_edge", "FLOAT", "EDGE"
            )

        for edge_idx, weight in edge_weights.items():
            edge_weights_attr.data[edge_idx].value = weight

            e = mesh.edges[edge_idx]

            # Blender 4.x+ uses the "bevel_weight_edge" mesh attribute for
            # edge weights.  Older versions of blender had this as a property
            # on the MeshEdge object.
            # (https://projects.blender.org/blender/blender/issues/95966)
            # If the edge has the old property, we are on an older version of
            # blender, so set it.
            if hasattr(e, "bevel_weight"):
                # pyre-fixme[16]: we have explicitly confirmed the bevel_weight
                #   attribute exists.
                e.bevel_weight = weight

        # Create the bevel modifier
        bevel = cast(
            bpy.types.BevelModifier,
            obj.modifiers.new(name="BevelCorners", type="BEVEL"),
        )
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


def duplicate(
    obj: bpy.types.Object, name: str, linked: bool = False
) -> bpy.types.Object:
    if linked:
        new_data = obj.data
    else:
        new_data = obj.data.copy()
    new_obj = bpy.data.objects.new(name, new_data)
    bpy.context.collection.objects.link(new_obj)

    return new_obj
