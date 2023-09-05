#!/usr/bin/python3 -tt
#
# Copyright (c) 2022, Adam Simpkins
#

from __future__ import annotations

import math
from typing import Iterable, List, Optional, Tuple, Union

# Blender modules
import mathutils


class Transform:
    def __init__(self, data: Optional[mathutils.Matrix] = None) -> None:
        if data is None:
            self._data: mathutils.Matrix = mathutils.Matrix(
                ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
            )
        else:
            self._data: mathutils.Matrix = data

    def __str__(self) -> str:
        row_strs = []
        # pyre-fixme[16]: type stubs for mathutils.Matrix do not include
        #   __iter__
        for row in self._data:
            row_contents = ", ".join(str(elem) for elem in row)
            row_strs.append(f"[{row_contents}]")
        contents = ", ".join(row_strs)
        return f"[{contents}]"

    def point(self) -> Point:
        return Point(self._data[0][3], self._data[1][3], self._data[2][3])

    def apply(self, point: Point) -> Point:
        x = self._data @ mathutils.Matrix((point.x, point.y, point.z, 1))
        # pyre-fixme[6]: pyre doesn't know the multiply result is always a 3x1
        #   vector of floats
        return Point(x[0], x[1], x[2])

    def transform(self, tf: Transform) -> Transform:
        # pyre-fixme[6]: pyre doesn't know that the multiply result will always
        #   be another matrix
        return Transform(tf._data @ self._data)

    def translate(self, x: float, y: float, z: float) -> Transform:
        tl = mathutils.Matrix(
            ((1, 0, 0, x), (0, 1, 0, y), (0, 0, 1, z), (0, 0, 0, 1))
        )
        # pyre-fixme[6]: pyre doesn't know that the multiply result will always
        #   be another matrix
        return Transform(tl @ self._data)

    def rotate(self, x: float, y: float, z: float) -> Transform:
        return self.rotate_degrees(x, y, z)

    def rotate_degrees(self, x: float, y: float, z: float) -> Transform:
        xr = math.radians(x)
        yr = math.radians(y)
        zr = math.radians(z)
        return self.rotate_radians(xr, yr, zr)

    def rotate_radians(self, x: float, y: float, z: float) -> Transform:
        rot = mathutils.Matrix(
            (
                (
                    math.cos(y) * math.cos(z),
                    (math.sin(x) * math.sin(y) * math.cos(z))
                    - (math.cos(x) * math.sin(z)),
                    (math.cos(x) * math.sin(y) * math.cos(z))
                    + (math.sin(x) * math.sin(z)),
                    0,
                ),
                (
                    math.cos(y) * math.sin(z),
                    (math.sin(x) * math.sin(y) * math.sin(z))
                    + (math.cos(x) * math.cos(z)),
                    (math.cos(x) * math.sin(y) * math.sin(z))
                    - (math.sin(x) * math.cos(z)),
                    0,
                ),
                (
                    -math.sin(y),
                    math.sin(x) * math.cos(y),
                    math.cos(x) * math.cos(y),
                    0,
                ),
                (0, 0, 0, 1),
            )
        )
        # pyre-fixme[6]: pyre doesn't know that the multiply result will always
        #   be another matrix
        return Transform(rot @ self._data)

    def mirror_x(self) -> Transform:
        mirror = mathutils.Matrix(
            ((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
        )
        # pyre-fixme[6]: pyre doesn't know that the multiply result will always
        #   be another matrix
        return Transform(mirror @ self._data)

    def mirror_y(self) -> Transform:
        mirror = mathutils.Matrix(
            ((0, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
        )
        # pyre-fixme[6]: pyre doesn't know that the multiply result will always
        #   be another matrix
        return Transform(mirror @ self._data)

    def mirror_z(self) -> Transform:
        mirror = mathutils.Matrix(
            ((0, 0, 0, 0), (0, 1, 0, 0), (0, 0, -1, 0), (0, 0, 0, 1))
        )
        # pyre-fixme[6]: pyre doesn't know that the multiply result will always
        #   be another matrix
        return Transform(mirror @ self._data)


class Point:
    __slots__ = ["x", "y", "z"]
    x: float
    y: float
    z: float

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __str__(self) -> str:
        return f"[{self.x}, {self.y}, {self.z}]"

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y}, {self.z})"

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def copy(self) -> Point:
        return Point(self.x, self.y, self.z)

    def translate(self, x: float, y: float, z: float) -> Point:
        return Point(self.x + x, self.y + y, self.z + z)

    def ptranslate(self, point: Point) -> Point:
        return Point(self.x + point.x, self.y + point.y, self.z + point.z)

    def to_transform(self) -> Transform:
        return Transform().translate(self.x, self.y, self.z)

    def transform(self, tf: Transform) -> Point:
        return self.to_transform().transform(tf).point()

    def mirror_x(self) -> Point:
        return Point(-self.x, self.y, self.z)

    def mirror_y(self) -> Point:
        return Point(self.x, -self.y, self.z)

    def mirror_z(self) -> Point:
        return Point(self.x, self.y, -self.z)

    def unit(self) -> Point:
        """Treating this point as a vector, return a new vector of length 1.0"""
        factor = 1.0 / self.length()
        return Point(self.x * factor, self.y * factor, self.z * factor)

    def length(self) -> float:
        """Return the distance from this point to the origin."""
        return math.sqrt(
            (self.x * self.x) + (self.y * self.y) + (self.z * self.z)
        )

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __add__(self, other: Point) -> Point:
        assert isinstance(other, Point), f"other is {type(other)}"
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Point) -> Point:
        assert isinstance(other, Point), f"other is {type(other)}"
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, n: Union[float, int]) -> Point:
        assert isinstance(n, (float, int))
        return Point(self.x * n, self.y * n, self.z * n)

    def dot(self, p: Point) -> float:
        """Return the dot product"""
        return (self.x * p.x) + (self.y * p.y) + (self.z * p.z)


class Point2D:
    __slots__ = ["x", "y"]
    x: float
    y: float

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"[{self.x}, {self.y}]"

    def __repr__(self) -> str:
        return f"Point2D({self.x}, {self.y})"

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def copy(self) -> Point2D:
        return Point2D(self.x, self.y)

    def translate(self, x: float, y: float) -> Point2D:
        return Point2D(self.x + x, self.y + y)

    def ptranslate(self, point: Point2D) -> Point2D:
        return Point2D(self.x + point.x, self.y + point.y)

    def unit(self) -> Point2D:
        """Treating this point as a vector, return a new vector of length 1.0"""
        factor = 1.0 / self.length()
        return Point2D(self.x * factor, self.y * factor)

    def length(self) -> float:
        """Return the distance from this point to the origin."""
        return math.sqrt((self.x * self.x) + (self.y * self.y))

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point2D):
            return False
        return self.x == other.x and self.y == other.y

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __add__(self, other: Point2D) -> Point2D:
        assert isinstance(other, Point2D), f"other is {type(other)}"
        return Point2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point2D) -> Point2D:
        assert isinstance(other, Point2D), f"other is {type(other)}"
        return Point2D(self.x - other.x, self.y - other.y)

    def __mul__(self, n: Union[float, int]) -> Point2D:
        assert isinstance(n, (float, int))
        return Point2D(self.x * n, self.y * n)

    def dot(self, p: Point2D) -> float:
        """Return the dot product"""
        return (self.x * p.x) + (self.y * p.y)


class Plane:
    __slots__ = ["p0", "p1", "p2"]

    def __init__(self, p0: Point, p1: Point, p2: Point) -> None:
        self.p0: Point = p0
        self.p1: Point = p1
        self.p2: Point = p2

    def normal(self) -> Point:
        """Compute the unit normal vector of the plane."""
        try:
            return self._normal_impl().unit() * -1.0
        except ZeroDivisionError:
            # All 3 points lie along the same line
            raise ValueError("cannot compute the normal of a degenerate plane")

    def _normal_impl(self) -> Point:
        da = self.p1 - self.p0
        db = self.p2 - self.p0
        return Point(
            da.y * db.z - da.z * db.y,
            da.z * db.x - da.x * db.z,
            da.x * db.y - da.y * db.x,
        )

    def intersect_line(self, line0: Point, line1: Point) -> Optional[Point]:
        """Return the point where the line connecting line0 and line1 intersects
        with this plane.

        Returns None if the line is parallel to this plane, or if the plane is
        degenerate (all 3 points in the plane are on the same line).
        """
        # Compute the plane's normal vector
        normal = self._normal_impl()

        line_vector = line1 - line0
        dot = normal.dot(line_vector)
        if dot == 0.0:
            return None

        w = line0 - self.p0
        fraction = -normal.dot(w) / dot
        return line0 + (line_vector * fraction)

    def z_intersect(self, x: float, y: float) -> float:
        """Given an X, Y position, return the Z coordinates of the plane at
        this X, y position.

        Throws an exception if the plane is vertical or degenerate.
        """
        intersect = self.intersect_line(Point(x, y, 0.0), Point(x, y, 1.0))
        if intersect is None:
            raise ValueError("cannot find Z intersect on a vertical plane")
        return intersect.z

    def shifted_along_normal(self, offset: float) -> Plane:
        """Return a new plane that is parallel to this plane,
        but shifted along the normal by the specified amount.
        """
        v = self.normal() * offset
        return Plane(self.p0 + v, self.p1 + v, self.p2 + v)

    def intersect_plane(self, plane: Plane) -> Optional[Tuple[Point, Point]]:
        """Return the line created by the intersection of this plane with
        another plane.

        Returns None if the two planes are parallel.
        """
        p0 = self.intersect_line(plane.p0, plane.p1)
        if p0 is None:
            p0 = self.intersect_line(plane.p0, plane.p2)
            if p0 is None:
                return None
            p1 = self.intersect_line(plane.p1, plane.p2)
        else:
            p1 = self.intersect_line(plane.p0, plane.p2)
            if p1 is None:
                p1 = self.intersect_line(plane.p1, plane.p2)

        if p1 is None:
            return None

        return (p0, p1)

    def rotation_off_z(self) -> Point:
        """
        Return the X and Y rotation required to rotate another object
        so that it is in alignment with this plane.

        This can be used to tilt an object so it will sit flat on this plane.
        If this plane is completely level with the ground (it's normal vector
        is the Z axis) then no rotation is required and (0, 0, 0) is returned.
        If the plane is tilted away from the Z axis this returns the X and Y
        rotation required to match the tilt.

        The Z component of the returned point is always 0.0.
        """
        norm = self.normal()
        x_angle = math.acos(norm.z / math.sqrt((norm.y ** 2) + (norm.z ** 2)))
        y_angle = math.acos(norm.z / math.sqrt((norm.x ** 2) + (norm.z ** 2)))
        return Point(x_angle, y_angle, 0.0)


class Line2D:
    """A 2 dimensional line."""

    __slots__ = ["p0", "p1"]

    def __init__(self, p0: Point2D, p1: Point2D) -> None:
        self.p0: Point2D = p0
        self.p1: Point2D = p1

    def __str__(self) -> str:
        return f"[{self.p0} -> {self.p1}]"

    def __repr__(self) -> str:
        return f"Line2D({self.p0:!r}, {self.p1!r})"

    def vector(self) -> Point2D:
        """Return the vector between the origin and end of this line."""
        return Point2D(self.p1.x - self.p0.x, self.p1.y - self.p0.y)

    def length(self) -> float:
        return self.vector().length

    def normal(self) -> Point2D:
        """Compute the normal vector of this line."""
        v = self.vector()
        return Point2D(v.y, -v.x).unit()

    def shifted_along_normal(self, offset: float) -> Line2D:
        """Return a new line that is parallel to this line,
        but shifted along the normal by the specified amount.
        """
        v = self.normal() * offset
        return Line2D(self.p0 + v, self.p1 + v)

    def as_slope_intercept(self) -> Tuple[float, float]:
        """Return the slope and intercept of this line,
        if written as a linear equation.

        Returns the values a and b from the equation y = a*x + b
        """
        if self.p1.x == self.p0.x:
            # This line is completely vertical
            raise Exception(
                "line is vertical, and cannot be written as a linear equation."
            )

        slope = (self.p1.y - self.p0.y) / (self.p1.x - self.p0.x)
        intercept = self.p0.y - slope * self.p0.x
        return (slope, intercept)

    def intersect(self, other: Line2D) -> Point2D:
        """Return the point where this line intersects with the specified
        line.
        """
        # Compute this line's normal vector
        v = self.vector()
        normal = Point2D(v.y, -v.x)

        otherv = other.vector()
        dot = normal.dot(otherv)
        if dot == 0.0:
            # These lines are parallel
            return None

        w = other.p0 - self.p0
        fraction = -normal.dot(w) / dot
        return other.p0 + (otherv * fraction)

    def angle(self, other: Line2D) -> float:
        """Compute the angle between this line and another line.

        Returns the value between 0 and pi radians.
        """
        selfv = self.vector()
        otherv = other.vector()
        num = selfv.x * otherv.x + selfv.y * otherv.y
        denom = self.length() * other.length()
        return math.acos(num / denom)

    def angle_full(self, other: Line2D) -> float:
        """Compute the angle between this line and another line.

        Returns the value between -pi and pi radians.
        """
        selfv = self.vector()
        otherv = other.vector()
        dot = selfv.x * otherv.x + selfv.y * otherv.y
        det = selfv.x * otherv.y - selfv.y * otherv.x
        return math.atan2(det, dot)


class MeshPoint:
    __slots__ = ["mesh", "_index", "point"]
    mesh: Mesh
    _index: Optional[int]
    point: Point

    def __init__(self, mesh: Mesh, point: Point) -> None:
        self.mesh = mesh
        self._index = None
        self.point = point

    def __repr__(self) -> str:
        return (
            f"MeshPoint(mesh={self.mesh!r}, point={self.point!r}, "
            f"index={self.index!r})"
        )

    @property
    def index(self) -> int:
        index = self._index
        if index is None:
            index = len(self.mesh.points)
            self._index = index
            self.mesh.points.append(self)
        return index

    @property
    def x(self) -> float:
        return self.point.x

    @property
    def y(self) -> float:
        return self.point.y

    @property
    def z(self) -> float:
        return self.point.z


class Mesh:
    def __init__(self) -> None:
        self.points: List[MeshPoint] = []
        self.all_points: List[MeshPoint] = []
        self.faces: List[
            Union[Tuple[int, int, int], Tuple[int, int, int, int]]
        ] = []

    def add_point(self, point: Union[Point, MeshPoint]) -> MeshPoint:
        if isinstance(point, MeshPoint):
            assert (
                point.mesh is not self
            ), "no need for duplicate points in the same mesh"
            point = point.point
        assert isinstance(point, Point)
        mp = MeshPoint(self, point=point)
        self.all_points.append(mp)
        return mp

    def add_xyz(self, x: float, y: float, z: float) -> MeshPoint:
        return self.add_point(Point(x, y, z))

    def add_tri(self, p0: MeshPoint, p1: MeshPoint, p2: MeshPoint) -> int:
        index = len(self.faces)
        self.faces.append((p0.index, p1.index, p2.index))
        return index

    def add_quad(
        self, p0: MeshPoint, p1: MeshPoint, p2: MeshPoint, p3: MeshPoint
    ) -> int:
        index = len(self.faces)
        self.faces.append((p0.index, p1.index, p2.index, p3.index))
        return index

    def add_fan(self, p0: MeshPoint, points: Iterable[MeshPoint]) -> None:
        """
        Add a sequence of triangular faces, fanned out from p0 to each of the
        other points.
        """
        prev: Optional[MeshPoint] = None
        for p in points:
            if prev is not None:
                self.add_tri(p0, prev, p)
            prev = p

    def transform(self, tf: Transform) -> None:
        for mp in self.all_points:
            mp.point = mp.point.transform(tf)

    def rotate(self, x: float, y: float, z: float) -> None:
        tf = Transform().rotate(x, y, z)
        self.transform(tf)

    def rotate_degrees(self, x: float, y: float, z: float) -> None:
        tf = Transform().rotate_degrees(x, y, z)
        self.transform(tf)

    def rotate_radians(self, x: float, y: float, z: float) -> None:
        tf = Transform().rotate_radians(x, y, z)
        self.transform(tf)

    def translate(self, x: float, y: float, z: float) -> None:
        tf = Transform().translate(x, y, z)
        self.transform(tf)

    def mirror_x(self) -> None:
        for mp in self.all_points:
            mp.point.x = -1.0 * mp.x
        self.faces = [tuple(reversed(face)) for face in self.faces]


def compute_angle(v0: cad.Point, v1: cad.Point) -> float:
    """Compute the angle between two vectors.

    Returns the value in radians.
    """
    num = v0.x * v1.x + v0.y * v1.y + v0.z * v1.z
    denom = v0.length() * v1.length()
    return math.acos(num / denom)


def cube(x: float, y: float, z: float) -> Mesh:
    hx = x * 0.5
    hy = y * 0.5
    hz = z * 0.5

    mesh = Mesh()
    b_tl = mesh.add_xyz(-hx, hy, -hz)
    b_tr = mesh.add_xyz(hx, hy, -hz)
    b_br = mesh.add_xyz(hx, -hy, -hz)
    b_bl = mesh.add_xyz(-hx, -hy, -hz)

    t_tl = mesh.add_xyz(-hx, hy, hz)
    t_tr = mesh.add_xyz(hx, hy, hz)
    t_br = mesh.add_xyz(hx, -hy, hz)
    t_bl = mesh.add_xyz(-hx, -hy, hz)

    mesh.add_quad(b_tl, b_bl, b_br, b_tr)
    mesh.add_quad(t_tl, t_tr, t_br, t_bl)
    mesh.add_quad(t_br, t_tr, b_tr, b_br)
    mesh.add_quad(t_bl, t_br, b_br, b_bl)
    mesh.add_quad(t_tl, t_bl, b_bl, b_tl)
    mesh.add_quad(t_tr, t_tl, b_tl, b_tr)

    return mesh


def range_cube(
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    z_range: Tuple[float, float],
) -> Mesh:
    mesh = Mesh()
    b_tl = mesh.add_xyz(x_range[0], y_range[1], z_range[0])
    b_tr = mesh.add_xyz(x_range[1], y_range[1], z_range[0])
    b_br = mesh.add_xyz(x_range[1], y_range[0], z_range[0])
    b_bl = mesh.add_xyz(x_range[0], y_range[0], z_range[0])

    t_tl = mesh.add_xyz(x_range[0], y_range[1], z_range[1])
    t_tr = mesh.add_xyz(x_range[1], y_range[1], z_range[1])
    t_br = mesh.add_xyz(x_range[1], y_range[0], z_range[1])
    t_bl = mesh.add_xyz(x_range[0], y_range[0], z_range[1])

    mesh.add_quad(b_tl, b_bl, b_br, b_tr)
    mesh.add_quad(t_tl, t_tr, t_br, t_bl)
    mesh.add_quad(t_br, t_tr, b_tr, b_br)
    mesh.add_quad(t_bl, t_br, b_br, b_bl)
    mesh.add_quad(t_tl, t_bl, b_bl, b_tl)
    mesh.add_quad(t_tr, t_tl, b_tl, b_tr)

    return mesh


def cylinder(
    r: float,
    h: Union[float, Tuple[float, float]],
    fn: int = 24,
    rotation: float = 360.0,
    r2: Optional[float] = None,
) -> Mesh:
    if isinstance(h, tuple):
        bottom_z, top_z = h
    else:
        top_z = h * 0.5
        bottom_z = -h * 0.5
    if r2 is None:
        r2 = r

    if rotation >= 360.0:
        rotation = 360.0
        end = fn
    else:
        end = fn + 1

    mesh = Mesh()
    top_center = mesh.add_xyz(0.0, 0.0, top_z)
    bottom_center = mesh.add_xyz(0.0, 0.0, bottom_z)
    top_points: List[MeshPoint] = []
    bottom_points: List[MeshPoint] = []

    rotation_rads = math.radians(rotation)
    for n in range(end):
        angle = (rotation_rads / fn) * n

        top_x = math.sin(angle) * r
        top_y = math.cos(angle) * r
        bottom_x = math.sin(angle) * r2
        bottom_y = math.cos(angle) * r2

        top_points.append(mesh.add_xyz(top_x, top_y, top_z))
        bottom_points.append(mesh.add_xyz(bottom_x, bottom_y, bottom_z))

    for idx in range(1, len(top_points)):
        # Note: this intentionally wraps around to -1 when idx == 0
        prev_f = top_points[idx - 1]
        prev_b = bottom_points[idx - 1]

        mesh.add_tri(top_center, prev_f, top_points[idx])
        mesh.add_tri(bottom_center, bottom_points[idx], prev_b)
        mesh.add_quad(prev_f, prev_b, bottom_points[idx], top_points[idx])

    if rotation >= 360.0:
        mesh.add_tri(top_center, top_points[-1], top_points[0])
        mesh.add_tri(bottom_center, bottom_points[0], bottom_points[-1])
        mesh.add_quad(
            top_points[-1], bottom_points[-1], bottom_points[0], top_points[0]
        )
    else:
        mesh.add_quad(
            top_center, bottom_center, bottom_points[0], top_points[0]
        )
        mesh.add_quad(
            top_center, top_points[-1], bottom_points[-1], bottom_center
        )

    return mesh


def cone(r: float, h: float, fn: int = 24, rotation: float = 360.0) -> Mesh:
    top_z = h * 0.5
    bottom_z = -h * 0.5

    if rotation >= 360.0:
        rotation = 360.0
        end = fn
    else:
        end = fn + 1

    mesh = Mesh()
    top_center = mesh.add_xyz(0.0, 0.0, top_z)
    bottom_center = mesh.add_xyz(0.0, 0.0, bottom_z)
    bottom_points: List[MeshPoint] = []

    rotation_rads = math.radians(rotation)
    for n in range(end):
        angle = (rotation_rads / fn) * n
        circle_x = math.sin(angle) * r
        circle_y = math.cos(angle) * r

        bottom_points.append(mesh.add_xyz(circle_x, circle_y, bottom_z))

    for idx in range(1, len(bottom_points)):
        # Note: this intentionally wraps around to -1 when idx == 0
        prev_b = bottom_points[idx - 1]

        mesh.add_tri(bottom_center, bottom_points[idx], prev_b)
        mesh.add_tri(prev_b, bottom_points[idx], top_center)

    if rotation >= 360.0:
        mesh.add_tri(bottom_center, bottom_points[0], bottom_points[-1])
        mesh.add_tri(bottom_points[-1], bottom_points[0], top_center)
    else:
        mesh.add_tri(bottom_center, bottom_points[0], top_center)
        mesh.add_tri(top_center, bottom_points[-1], bottom_center)

    return mesh


def bezier(
    npoints: int, start: Point, ctrl0: Point, ctrl1: Point, end: Point
) -> List[Point]:
    """
    Generates a cubic bezier curve from the start to the end point,
    with the control points defined by ctrl0 and ctrl1.

    The curve will go from the start to the end, leaving the start point
    heading towards ctrl0, and approaching the end point from the direction of
    ctrl1.
    """
    results: List[Point] = []
    tscale = 1.0 / (npoints - 1)
    for idx in range(npoints):
        t = idx * tscale
        nt = 1.0 - t
        b = (
            (start * (nt ** 3))
            + (ctrl0 * (3 * nt * nt * t))
            + (ctrl1 * (3 * nt * t * t))
            + (end * (t ** 3))
        )
        results.append(b)

    return results
