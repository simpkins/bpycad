#!/usr/bin/python3 -tt
#
# Copyright (c) 2023, Adam Simpkins
#

from bpycad import blender_util
import bpy

from typing import Optional


def simple_display_holder() -> bpy.types.Object:
    """Create a simple model for holding several PCB modules while prototyping.
    """
    pad = PcbHolder(100, 155)

    # 3.2" TFT display (https://adafru.it/1743)
    pad.add_screw_rect(x=50.0, y=38.0, w=83.312, h=57.15)

    # .91" OLED display (https://adafru.it/4440)
    pad.add_screw_rect(x=20, y=135, w=28, h=16.5, thread=2.0)

    # 4-channel 5V relay module
    pad.add_screw_rect(x=68, y=113, w=45, h=68)

    return pad.obj


class PcbHolder:
    def __init__(self, w: float, h: float, thickness: float = 8) -> None:
        self.w = w
        self.h = h
        self.base_thickness = thickness

        self.connector_r: float = 2.2 * 0.5
        self.connector_h = 4.75

        self.obj: bpy.types.Object = blender_util.range_cube(
            (0.0, self.w), (0.0, self.h), (0, self.base_thickness)
        )
        self.add_board_connectors()

    def add_board_connectors(self) -> None:
        # Add protrusions on the left and right that match the protrusions on
        # mini-breadboards allowing them to be hooked together.
        y_offsets = (54, 28)
        off_idx = 0

        y = 14
        while y < self.h:
            self._add_connector(0, y)
            self._add_connector_hole(self.w, y)
            y += y_offsets[off_idx]
            off_idx = (off_idx + 1) % len(y_offsets)

    def _add_connector(self, x: float, y: float) -> None:
        cyl = blender_util.cylinder(
            self.connector_r - 0.05, (0, self.connector_h - 0.4)
        )
        with blender_util.TransformContext(cyl) as ctx:
            ctx.translate(x - (2.00 * 0.5), y, 0)
        blender_util.union(self.obj, cyl)

    def _add_connector_hole(self, x: float, y: float) -> None:
        cyl = blender_util.cylinder(
            self.connector_r + 0.07, (-0.5, self.connector_h + 0.4)
        )
        with blender_util.TransformContext(cyl) as ctx:
            ctx.translate(x - 0.95, y, 0)
        blender_util.difference(self.obj, cyl)

    def add_standoff(
        self,
        x: float,
        y: float,
        # Thread diameter.  Defaults to M2.5 screws
        thread: float = 2.5,
        # Overall standoff diameter.  We use diameter rather than radius
        # here just since the thread argument above is also a diameter, to
        # match common metric screw size measurements.
        d: Optional[float] = None,
        # Height of the standoff
        h: float = 6,
        screw_depth: Optional[float] = None,
    ) -> None:
        thread_r = thread * 0.5
        if d is None:
            d = thread + 2.5
        standoff_r = d * 0.5

        if screw_depth is None:
            screw_depth = min(max(h, 8.0), h + self.base_thickness - 1.0)

        intersect_depth = 1
        standoff = blender_util.cylinder(
            r=standoff_r,
            h=(self.base_thickness - intersect_depth, self.base_thickness + h),
        )
        hole = blender_util.cylinder(
            r=thread_r,
            h=(
                self.base_thickness + h - screw_depth,
                self.base_thickness + h + intersect_depth,
            ),
        )
        with blender_util.TransformContext(standoff) as ctx:
            ctx.translate(x, y, 0)
        with blender_util.TransformContext(hole) as ctx:
            ctx.translate(x, y, 0)
        blender_util.union(self.obj, standoff)
        blender_util.difference(self.obj, hole)

    def add_screw_rect(
        self, x: float, y: float, w: float, h: float, thread: float = 2.5
    ) -> None:
        self.add_standoff(x - (w * 0.5), y + (h * 0.5), thread=thread)
        self.add_standoff(x + (w * 0.5), y + (h * 0.5), thread=thread)
        self.add_standoff(x + (w * 0.5), y - (h * 0.5), thread=thread)
        self.add_standoff(x - (w * 0.5), y - (h * 0.5), thread=thread)
