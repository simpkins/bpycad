import bpy
import mathutils
import typing as _typing

T = _typing.TypeVar("T")


class BMesh:
    faces: BMFaceSeq = ...
    edges: BMEdgeSeq = ...
    verts: BMVertSeq = ...

    def from_mesh(
        self,
        mesh: bpy.types.Mesh,
        face_normals: _typing.Any = True,  # pyre-fixme[2]: shouldn't use Any
        vertex_normals: _typing.Any = True,  # pyre-fixme[2]: shouldn't use Any
        use_shape_key: bool = False,
        shape_key_index: int = 0,
    ) -> None: ...
    def to_mesh(self, mesh: bpy.types.Mesh) -> None: ...
    def free(self) -> None: ...


class BMFace:
    edges: BMElemSeq[BMEdge]
    verts: BMElemSeq[BMVert]
    index: int


class BMEdge:
    link_faces: BMElemSeq[BMFace]
    verts: BMElemSeq[BMVert]
    index: int


class BMVert:
    co: mathutils.Vector
    index: int


class BMEdgeSeq(_typing.List[BMEdge]): ...


class BMFaceSeq(_typing.List[BMFace]): ...


class BMVertSeq(_typing.List[BMVert]): ...


class BMElemSeq(_typing.Sequence[T]):
    def index_update(self) -> None: ...
