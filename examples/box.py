#!/usr/bin/python3 -tt
#
# Copyright (c) 2023, Adam Simpkins
#

from bpycad import blender_util
from bpycad.cad import Mesh, MeshPoint, Plane

import bpy
from typing import List


class CustomBox:
    """Just a simple enclosure for example purposes.

    Defines a slightly irregularly shaped, and then applies a cutout to one of
    the diagonal walls.
    """

    def __init__(self) -> None:
        self.wall_thickness = 4.0
        self.height = 50.0

        # Define some points for the outer perimeter
        self.perimeter = [
            (0, 0),
            (0, 120),
            (120, 120),
            (120, 90),
            (60, 30),
            (60, 0),
        ]

        # The face that we will apply the display cutout to
        # This is an index into the self.perimeter points
        self.display_face_idx = 3

        self.mesh = Mesh()
        self.beveler = blender_util.Beveler()
        self.gen_walls()

    def gen_walls(self) -> None:
        # Generate the walls.  We do this purely with a bpycad.cad.Mesh,
        # without creating a Blender object yet.
        self.base_perim = [
            self.mesh.add_xyz(x, y, 0.0) for x, y in self.perimeter
        ]
        self.upper_perim = [
            self.mesh.add_xyz(x, y, self.height) for x, y in self.perimeter
        ]
        self.inner_base_perim: List[MeshPoint] = []
        self.inner_upper_perim: List[MeshPoint] = []
        inner_h = self.height - self.wall_thickness

        # Create the outer wall faces
        for idx in range(len(self.base_perim)):
            # Add the vertical outer wall
            self.mesh.add_quad(
                self.base_perim[idx],
                self.upper_perim[idx],
                self.upper_perim[idx - 1],
                self.base_perim[idx - 1],
            )

            # Define the inner wall points
            # Take the outer wall planes, move each inwards by wall_thickness,
            # then find where the inner walls intersect to determine the
            # inner perimeter points.
            prev_wall_plane = Plane(
                self.base_perim[idx].point,
                self.base_perim[idx - 1].point,
                self.upper_perim[idx].point,
            )
            next_idx = (idx + 1) % len(self.base_perim)
            next_wall_plane = Plane(
                self.base_perim[next_idx].point,
                self.base_perim[idx].point,
                self.upper_perim[idx].point,
            )
            prev_inner_wall_plane = prev_wall_plane.shifted_along_normal(
                self.wall_thickness
            )
            next_inner_wall_plane = next_wall_plane.shifted_along_normal(
                self.wall_thickness
            )
            inner_edge = prev_inner_wall_plane.intersect_plane(
                next_inner_wall_plane
            )
            self.inner_base_perim.append(
                self.mesh.add_xyz(inner_edge[0].x, inner_edge[0].y, 0.0)
            )
            self.inner_upper_perim.append(
                self.mesh.add_xyz(inner_edge[0].x, inner_edge[0].y, inner_h)
            )

            # Mark the outer edges to be beveled
            self.beveler.bevel_edge(
                self.base_perim[idx], self.upper_perim[idx]
            )
            self.beveler.bevel_edge(
                self.upper_perim[idx], self.upper_perim[idx - 1]
            )

        # Create the inner wall faces
        for idx in range(len(self.base_perim)):
            p = self.inner_base_perim[idx].point
            # Inner wall
            self.mesh.add_quad(
                self.inner_base_perim[idx],
                self.inner_base_perim[idx - 1],
                self.inner_upper_perim[idx - 1],
                self.inner_upper_perim[idx],
            )
            # Bottom wall
            self.mesh.add_quad(
                self.inner_base_perim[idx],
                self.base_perim[idx],
                self.base_perim[idx - 1],
                self.inner_base_perim[idx - 1],
            )

        # Inner ceiling
        self.mesh.add_fan(
            self.inner_upper_perim[0], reversed(self.inner_upper_perim[1:])
        )
        # Top faces
        self.mesh.add_fan(self.upper_perim[0], self.upper_perim[1:])

    def apply_display_cutout(self, obj: bpy.types.Object) -> None:
        # The bottom corners of the wall that we will apply the cutout to
        p0 = self.base_perim[self.display_face_idx].point
        p1 = self.base_perim[self.display_face_idx + 1].point

        # Apply the display cutout to the diagonal wall
        cutout1 = blender_util.range_cube((-10, 10), (-10, 10), (25, 35))
        blender_util.apply_to_wall(cutout1, p0, p1)
        blender_util.difference(obj, cutout1)

        cutout2 = blender_util.range_cube(
            (-15, 15), (self.wall_thickness * -0.5, 10), (20, 40)
        )
        blender_util.apply_to_wall(cutout2, p0, p1)
        blender_util.difference(obj, cutout2)

    def gen_obj(self) -> bpy.types.Object:
        # Create the main blender object
        obj = blender_util.new_mesh_obj("Box", self.mesh)
        self.beveler.apply_bevels(obj)

        # Apply the display cutout
        self.apply_display_cutout(obj)

        return obj


def test() -> None:
    CustomBox().gen_obj()
