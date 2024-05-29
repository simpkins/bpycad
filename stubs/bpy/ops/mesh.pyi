import typing as _typing


def select_all(action: str = "TOGGLE") -> None: ...
def dissolve_limited(
    angle_limit: float = 0.0872665,
    use_dissolve_boundaries: bool = False,
    delimit: _typing.Set[str] = {"NORMAL"},
) -> None: ...
def remove_doubles(
    threshold: float = 0.0001,
    use_unselected: bool = False,
    use_sharp_edge_from_normals: bool = False,
) -> None: ...
def beautify_fill(angle_limit: float = ...) -> None: ...
def extrude_region(
    use_normal_flip: bool = False,
    use_dissolve_ortho_edges: bool = False,
    mirror: bool = False,
) -> None: ...
