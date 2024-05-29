from __future__ import annotations

import typing as _typing


T = _typing.TypeVar("T")
IdT = _typing.TypeVar("IdT", bound=ID)


class bpy_struct:
    # pyre-fixme[2,3]: shouldn't use Any
    def get(self, key: str, default: _typing.Any = None) -> _typing.Any: ...


class ID(bpy_struct):
    name: str = ...

    def copy(self: IdT) -> IdT: ...


class bpy_prop_collection(bpy_struct, _typing.Sequence[T]):
    def __getitem__(self, key: int | str) -> T: ...


class ViewLayer(bpy_struct): ...


class Object(ID):
    data: ID = ...
    modifiers: ObjectModifiers = ...

    def select_set(
        self, state: bool, view_layer: _typing.Optional[ViewLayer] = None
    ) -> None: ...


class Mesh(ID):
    edges: MeshEdges = ...
    attributes: AttributeGroup = ...

    def update(
        self, calc_edges: bool = False, calc_edges_loose: bool = False
    ) -> None: ...
    def from_pydata(
        self,
        vertices: _typing.Any,  # pyre-fixme[2]: shouldn't use Any
        edges: _typing.Any,  # pyre-fixme[2]: shouldn't use Any
        faces: _typing.Any,  # pyre-fixme[2]: shouldn't use Any
    ) -> None: ...


class Operator(bpy_struct):
    def report(self, type: _typing.Set[str], message: str) -> None: ...


class OperatorProperties(bpy_struct): ...


class Context(bpy_struct):
    window: Window = ...
    window_manager: WindowManager = ...


class WorkSpace(ID):
    screens: bpy_prop_collection[Screen] = ...


class WindowManager(ID):
    def event_timer_add(
        self, time_step: float, window: _typing.Optional[Window] = None
    ) -> Timer: ...

    def event_timer_remove(self, timer: Timer) -> None: ...

    @classmethod
    def modal_handler_add(cls, operator: Operator) -> bool: ...


class Window(bpy_struct): ...


class Event(bpy_struct):
    type: str = ...


class Timer(bpy_struct): ...


class Menu(bpy_struct):
    layout: UILayout = ...


class UILayout(bpy_struct):
    def operator(
        self,
        operator: str,
        text: str = "",
        text_ctxt: str = "",
        translate: bool = True,
        icon: str = "NONE",
        emboss: bool = True,
        depress: bool = False,
        icon_value: int = 0,
    ) -> OperatorProperties: ...


class BlendData(bpy_struct):
    filepath: str = ...
    screens: BlendDataScreens = ...
    meshes: BlendDataMeshes = ...
    objects: BlendDataObjects = ...
    collections: BlendDataCollections = ...
    curves: BlendDataCurves = ...
    fonts: BlendDataFonts = ...


class Collection(ID):
    objects: CollectionObjects = ...


class Screen(ID):
    areas: bpy_prop_collection[Area] = ...


class Area(bpy_struct):
    spaces: AreaSpaces = ...
    type: str = ...


class Space(bpy_struct):
    type: str = ...


class SpaceView3D(Space):
    region_3d: RegionView3D = ...


class RegionView3D(bpy_struct):
    view_distance: float = ...


class AreaSpaces(bpy_prop_collection[Space]):
    active: Space = ...


class BlendDataScreens(bpy_prop_collection[Screen]): ...


class BlendDataMeshes(bpy_prop_collection[Mesh]):
    def new(self, name: str) -> Mesh: ...
    def new_from_object(
        self,
        object: Object,
        preserve_all_data_layers: bool = False,
        depsgraph: _typing.Optional[Depsgraph] = None,
    ) -> Mesh: ...


class Depsgraph(bpy_struct): ...


class BlendDataObjects(bpy_prop_collection[Object]):
    def new(self, name: str, object_data: ID) -> Object: ...
    def remove(
        self,
        object: Object,
        do_unlink: bool = True,
        do_id_user: bool = True,
        do_ui_user: bool = True,
    ) -> None: ...


class BlendDataCollections(bpy_prop_collection[Collection]): ...


class BlendDataCurves(bpy_prop_collection[Curve]):
    def new(self, name: str, type: str) -> Curve: ...


class BlendDataFonts(bpy_prop_collection[VectorFont]):
    def load(
        self, filepath: str, check_existing: bool = ...
    ) -> VectorFont: ...


class AttributeGroup(bpy_prop_collection[Attribute]):
    def new(self, name: str, type: str, domain: str) -> Attribute: ...


class Attribute(bpy_struct): ...


class MeshEdges(bpy_prop_collection[MeshEdge]): ...


class MeshEdge(bpy_struct):
    vertices: _typing.Tuple[int, int] = ...


class Curve(ID):
    resolution_u: int
    resolution_v: int


class TextCurve(Curve):
    body: str = ...
    size: float = ...
    align_x: str = ...
    align_y: str = ...
    font: VectorFont = ...


class VectorFont(ID): ...


class ObjectModifiers(bpy_prop_collection[Modifier]):
    def new(self, name: str, type: str) -> Modifier: ...


class Modifier(bpy_struct):
    name: str = ...


class BooleanModifier(Modifier):
    object: Object = ...
    operation: str = ...
    double_threshold: float = ...


class BevelModifier(Modifier):
    width: float = ...
    limit_method: str = ...
    segments: int = ...


class CollectionObjects(bpy_prop_collection[Object]):
    def link(self, object: Object) -> None: ...
    def unlink(self, object: Object) -> None: ...
