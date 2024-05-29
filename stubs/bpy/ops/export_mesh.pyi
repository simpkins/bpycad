def stl(
    filepath: str = "",
    check_existing: bool = True,
    filter_glob: str = "*args.stl",
    use_selection: bool = False,
    global_scale: float = 1.0,
    use_scene_unit: bool = False,
    ascii: bool = False,
    use_mesh_modifiers: bool = True,
    batch_mode: str = "OFF",
    axis_forward: str = "Y",
    axis_up: str = "Z",
) -> None: ...
