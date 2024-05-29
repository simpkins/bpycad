import bmesh
import mathutils
import typing as _typing


def rotate(
    bm: bmesh.types.BMesh,
    cent: mathutils.Vector | _typing.Tuple[float, float, float] = ...,
    matrix: mathutils.Matrix = ...,
    verts: _typing.List[bmesh.types.BMVert] | bmesh.types.BMVertSeq = ...,
    space: mathutils.Matrix = ...,
    use_shapekey: bool = False,
) -> None: ...


def translate(
    bm: bmesh.types.BMesh,
    vec: mathutils.Vector | _typing.Tuple[float, float, float],
    space: mathutils.Matrix = ...,
    verts: _typing.List[bmesh.types.BMVert] | bmesh.types.BMVertSeq = ...,
    use_shapekey: bool = False,
) -> None: ...


def scale(
    bm: bmesh.types.BMesh,
    vec: mathutils.Vector | _typing.Tuple[float, float, float],
    space: mathutils.Matrix = ...,
    verts: _typing.List[bmesh.types.BMVert] | bmesh.types.BMVertSeq = ...,
    use_shapekey: bool = False,
) -> None: ...


def transform(
    bm: bmesh.types.BMesh,
    matrix: mathutils.Matrix,
    space: mathutils.Matrix = ...,
    verts: _typing.List[bmesh.types.BMVert] | bmesh.types.BMVertSeq = ...,
    use_shapekey: bool = False,
) -> None: ...


def triangulate(
    bm: bmesh.types.BMesh,
    faces: _typing.List[bmesh.types.BMFace] = ...,
    quad_method: str = ...,
    ngon_method: str = ...,
) -> _typing.Dict[str, _typing.Any]: ...


def mirror(
    bm: bmesh.types.BMesh,
    geom: _typing.List[
        bmesh.types.BMVert | bmesh.types.BMEdge | bmesh.types.BMFace
    ] = ...,
    matrix: mathutils.Matrix = ...,
    merge_dist: float = ...,
    axis: str = ...,
    mirror_u: bool = ...,
    mirror_v: bool = ...,
    mirror_udim: bool = ...,
    use_shapekey: bool = ...,
) -> _typing.Dict[str, _typing.Any]: ...


def delete(
    bm: bmesh.types.BMesh,
    geom: _typing.List[
        bmesh.types.BMVert | bmesh.types.BMEdge | bmesh.types.BMFace
    ] = ...,
    context: str = ...,
) -> None: ...


def reverse_faces(
    bm: bmesh.types.BMesh,
    faces: _typing.List[bmesh.types.BMFace] = ...,
    flip_multires: bool = False,
) -> None: ...


def beautify_fill(
    bm: bmesh.types.BMesh,
    faces: _typing.List[bmesh.types.BMFace] = ...,
    edges: _typing.List[bmesh.types.BMEdge] = ...,
    use_restrict_tag: bool = ...,
    method: str = ...,
) -> _typing.Dict[str, _typing.Any]: ...
