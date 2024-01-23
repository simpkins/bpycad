"""
Automatically re-run blender.py within Blender whenever it changes.

This is a blender operator that monitors an external script and its
dependencies for any changes, and automatically re-runs the script any time a
change is made to any of these files.

This makes it easy to work on the CAD code in an external editor, and have the
changes automatically reflected in Blender whenever you save the files.

This automatically starts monitoring when you first run the script.
It adds entries to the main Edit menu to allow stopping and re-starting
monitoring.
"""

from __future__ import annotations

import bpy
import importlib
import sys
import time
import traceback
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Dict, List, Optional, Sequence, Set, Tuple, Type


_instance: Optional[MonitorOperatorBase] = None


class ImportTracker(MetaPathFinder):
    """
    A helper class to monitor imports that happen, so we can keep track
    of which modules we need to monitor.

    This hooks into the import system so we can record modules we attempt to
    import even if an error occurs while importing them.
    """

    def __init__(self) -> None:
        self.real_meta_path: Optional[List[MetaPathFinder]] = None
        self.imported_modules: Dict[str, List[Path]] = {}

    def __enter__(self) -> ImportTracker:
        self.install()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.uninstall()

    def install(self) -> None:
        assert not self.real_meta_path
        # pyre-ignore[8]: typeshed defines sys.meta_path using a protocol
        #   rather than MetaPathFinder, and has annoying inconsistencies
        #   between its protocol and the real type.
        self.real_meta_path = sys.meta_path
        sys.meta_path = [self]

    def uninstall(self) -> None:
        meta_path = self.real_meta_path
        assert meta_path is not None
        # pyre-ignore[9]: same typeshed sys.meta_path problems as above.
        sys.meta_path = meta_path
        self.real_meta_path = None

    # pyre-fixme[14]: pyre reports an inconsistent override here when using
    #  slightly out-of-date typeshed hints from before
    #  https://github.com/python/typeshed/pull/9070
    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[str]],
        target: Optional[ModuleType] = None,
    ) -> Optional[ModuleSpec]:
        meta_path = self.real_meta_path
        assert meta_path is not None
        for mpf in meta_path:
            spec = mpf.find_spec(fullname, path, target=target)
            if spec is not None:
                paths: List[Path] = []
                if spec.origin is not None:
                    paths.append(Path(spec.origin))
                self.imported_modules[fullname] = paths
                return spec

        # If we reach here we failed to find this module.
        # Even though we could not find it, monitor the path were it is likely
        # to be.  We want to immediately reload if this file does get created
        # in the future.
        if path:
            search_path = path
        else:
            # If this is a top-level, walk through sys.path and add possible
            # locations where it might not be found.  This might not be 100%
            # accurate with what the real MetaPathFinders would do, but is good
            # enough for most cases.
            search_path = sys.path
        module_base = fullname.rsplit(".", 1)[-1]
        paths: List[Path] = []
        for p in search_path:
            paths.append(Path(p) / f"{module_base}.py")
            paths.append(Path(p) / module_base / "__init__.py")
        print(f"unable to find import: {fullname} ; will search {paths}")
        self.imported_modules[fullname] = paths

        return None

    def invalidate_caches(self) -> None:
        meta_path = self.real_meta_path
        assert meta_path is not None
        for mpf in meta_path:
            mpf.invalidate_caches()


class MonitorOperatorBase(bpy.types.Operator):
    """Monitor an external script for changes and re-run on change"""

    # pyre-fixme[31]: bpy property types aren't really types
    poll_interval: bpy.props.FloatProperty(name="poll_interval", default=0.1)

    # pyre-fixme[31]: bpy property types aren't really types
    delete_all: bpy.props.BoolProperty(name="delete_all", default=True)

    # This is really a list, but blender does not appear to support passing
    # CollectionProperty values to operators when invoking them, so we pass it
    # as a comma-separated string.
    # pyre-fixme[31]: bpy property types aren't really types
    monitored_packages: bpy.props.StringProperty(name="monitored_packages")
    _monitored_packages: List[str] = []

    # The REGISTER option allows our messages to be logged to the info console
    bl_options = {"REGISTER"}

    _timer: Optional[bpy.types.Timer] = None
    stop: bool = False

    _monitored_modules: Dict[str, List[Path]] = {}
    _timestamps: Dict[Path, Optional[float]] = {}
    _name: str = ""

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        global _instance
        return _instance is None

    def modal(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> Set[str]:
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        if self.stop:
            global _instance
            _instance = None
            self.cancel(context)
            self.report({"INFO"}, f"cancelling monitoring of {self._name}")
            return {"CANCELLED"}

        self.check_for_updates()
        return {"PASS_THROUGH"}

    def execute(self, context: bpy.types.Context) -> Set[str]:
        global _instance
        if _instance is not None:
            self.report({"Error"}, f"Script monitor is already running")
            return {"CANCELLED"}
        _instance = self

        self._monitored_packages = self.monitored_packages.split(",")

        self._init()
        self.report({"INFO"}, f"monitoring modules for {self._name}")
        self._init_monitored_modules()
        self.on_change()

        wm = context.window_manager
        self._timer = wm.event_timer_add(
            self.poll_interval, window=context.window
        )
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _refresh_monitored_modules(
        self, import_tracker: ImportTracker
    ) -> None:
        monitored_modules: Dict[str, List[Path]] = {}
        for mod_name, paths in import_tracker.imported_modules.items():
            paths_to_monitor = self._get_monitor_paths(mod_name, paths)
            if paths_to_monitor:
                monitored_modules[mod_name] = paths_to_monitor

        self._monitored_modules = monitored_modules
        self._timestamps = self._get_timestamps()

    def _init_monitored_modules(self) -> None:
        for mod_name, module in sys.modules.items():
            mod_path_str = getattr(module, "__file__", None)
            mod_paths: List[Path] = []
            if mod_path_str is not None:
                mod_paths.append(Path(mod_path_str))
            paths_to_monitor = self._get_monitor_paths(mod_name, mod_paths)
            if paths_to_monitor:
                self._monitored_modules[mod_name] = paths_to_monitor

    def _get_monitor_paths(
        self, mod_name: str, mod_paths: List[Path]
    ) -> List[Path]:
        for pkg in self._monitored_packages:
            if mod_name == pkg or mod_name.startswith(pkg + "."):
                return mod_paths

        return []

    def cancel(self, context: bpy.types.Context) -> None:
        wm = context.window_manager
        timer = self._timer
        assert timer is not None
        wm.event_timer_remove(timer)

    def check_for_updates(self) -> None:
        current = self._get_timestamps()
        if current == self._timestamps:
            return

        self._timestamps = current
        self.on_change()

    def _purge_loaded_modules(self) -> None:
        # We simply delete all currently monitored modules from sys.modules
        # Calling self._run() should then re-import any modules that are needed
        #
        # Note that this behavior is different than using importlib.reload():
        # importlib.reload() keeps the old module objects and replaces their
        # contents with the newer info.  We are replacing the module objects
        # wholesale.  It is possible that the old modules remain around if they
        # are still referenced, but in general we don't really care about this.
        #
        # Replacing the modules wholesale and letting them be re-imported as
        # they are used is simpler, since we don't need to worry about
        # re-importing modules in the correct order to ensure that some
        # dependent modules always get reloaded before other modules that
        # depend on them.
        importlib.invalidate_caches()
        for mod_name in self._monitored_modules:
            sys.modules.pop(mod_name, None)

    def _get_timestamps(self) -> Dict[Path, Optional[float]]:
        result: Dict[Path, Optional[float]] = {}
        for path_list in self._monitored_modules.values():
            for path in path_list:
                result[path] = self._get_timestamp(path)
        return result

    def _get_timestamp(self, path: Path) -> Optional[float]:
        try:
            s = path.stat()
        except IOError:
            return None
        return s.st_mtime

    def on_change(self) -> None:
        if self.delete_all:
            if bpy.context.object is not None:
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete(use_global=False)

        print("=" * 60, file=sys.stderr)
        print(f"Running {self._name}...", file=sys.stderr)
        self.report({"INFO"}, f"running {self._name}")

        # Unload all currently loaded modules.
        # This ensures that any necessary modules will be re-imported when we
        # run the functions, so they can be discovered by our ImportTracker.
        # This is also required for correctness: even modules that have not
        # changed need to be re-imported, since their existing incarnations may
        # use and refer to other modules that were changed.  They need to be
        # reloaded to see up-to-date versions of modules that were changed.
        self._purge_loaded_modules()

        error = False
        import_tracker = ImportTracker()
        import_tracker.install()
        try:
            start = time.time()
            self._run()
            end = time.time()
            duration = end - start
            print(f"Finished {self._name} in {duration:.02f}s")
        except Exception as ex:
            # If your editor replaces files by removing the old one before
            # writing out the new file, we can attempt to reload the module
            # before it has been written out completely, which will result in
            # an error here.  This is okay, we will keep monitoring and
            # will reload again once the editor has finished writing out the
            # full new file.
            self._report_error(f"error running {self._name}")
            error = True
        finally:
            import_tracker.uninstall()

        self._refresh_monitored_modules(import_tracker)

    def _init(self) -> None:
        pass

    def _run(self) -> None:
        raise NotImplementedError("must be implemented by a subclass")

    def _report_error(self, msg: str) -> None:
        err_str = traceback.format_exc()
        # I haven't quite tracked down why, but Blender doesn't always write
        # self.report() messages to the console after operator runs.  Sometimes
        # it does, sometimes it doesn't.  Therefore we also include our own
        # explicit print() statement.
        self.report({"WARNING"}, f"{msg}: {err_str}")
        print(f"{msg}: {err_str}")


class CancelMonitorOperator(bpy.types.Operator):
    """Cancel an existing ScriptMonitor operator"""

    bl_idname = "script.cancel_external_script_monitor"
    bl_label = "Cancel External Script Monitor"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        global _instance
        return _instance is not None

    def execute(self, context: bpy.types.Context) -> Set[str]:
        global _instance
        if _instance is not None:
            _instance.stop = True

        return {"FINISHED"}


class ScriptMonitorOperator(MonitorOperatorBase):
    bl_idname = "script.external_script_monitor"
    bl_label = "Monitor External Script"

    _local_dir: Path = Path()
    _abs_path: Path = Path()
    # pyre-fixme[31]: bpy property types aren't really types
    path: bpy.props.StringProperty(name="path", default="main.py")

    def _init(self) -> None:
        self._local_dir = Path(bpy.data.filepath).parent.resolve()
        self._abs_path = self._local_dir / self.path
        self._name = str(self._abs_path)

    def _get_monitor_paths(
        self, mod_name: str, mod_paths: List[Path]
    ) -> List[Path]:
        if self.monitored_packages is not None:
            # If an explicit set of packages to monitor was specified,
            # just use that.
            return super()._get_monitor_paths(mod_name, mod_paths)

        return [path for path in mod_paths if self._local_dir in path.parents]

    def _run(self) -> None:
        global_namespace = {
            "__file__": str(self._abs_path),
            "__name__": "__main__",
        }
        src_code = self._abs_path.read_text()
        exec(compile(src_code, str(self._abs_path), "exec"), global_namespace)


class FunctionMonitorOperator(MonitorOperatorBase):
    bl_idname = "script.external_function_monitor"
    bl_label = "Monitor External Function"

    # pyre-fixme[31]: bpy property types aren't really types
    function: bpy.props.StringProperty(name="function")

    _local_dir: Path = Path()
    _mod_name: str = ""
    _fn_name: str = ""

    def _init(self) -> None:
        self._name = self.function
        parts = self.function.rsplit(".", 1)
        if len(parts) != 2:
            raise Exception(
                "invalid function name: must be of the form <module>.<name>"
            )
        self._mod_name, self._fn_name = parts

        # If monitored_packages was not specified, default to monitoring the
        # entire package that contains the module we are running.
        if not self.monitored_packages:
            parts = self._mod_name.rsplit(".", 1)
            if len(parts) == 2:
                pkg_name = parts[0]
                self.monitored_packages = pkg_name
            else:
                # If this module is not in a package, just monitor the module
                self.monitored_packages = self._mod_name

    def _run(self) -> None:
        module = importlib.import_module(self._mod_name)
        fn = getattr(module, self._fn_name)
        fn()


def menu_func(self: bpy.types.Menu, context: bpy.types.Context) -> None:
    self.layout.operator(
        ScriptMonitorOperator.bl_idname, text=ScriptMonitorOperator.bl_label
    )
    self.layout.operator(
        CancelMonitorOperator.bl_idname, text=CancelMonitorOperator.bl_label
    )


def register() -> None:
    bpy.utils.register_class(ScriptMonitorOperator)
    bpy.utils.register_class(FunctionMonitorOperator)
    bpy.utils.register_class(CancelMonitorOperator)
    # pyre-fixme[16]: incomplete bpy type annotations
    bpy.types.TOPBAR_MT_edit.append(menu_func)


# Register and add to the "view" menu (required to also use F3 search
# "Modal Timer Operator" for quick access)
def unregister() -> None:
    bpy.utils.unregister_class(ScriptMonitorOperator)
    bpy.utils.unregister_class(FunctionMonitorOperator)
    bpy.utils.unregister_class(CancelMonitorOperator)
    # pyre-fixme[16]: incomplete bpy type annotations
    bpy.types.TOPBAR_MT_edit.remove(menu_func)


def main(fn_name: str, monitored_packages: Optional[List[str]] = None) -> None:
    try:
        monitored_packages = monitored_packages or []
        monitored_packages_str = ",".join(monitored_packages)

        register()
        # pyre-fixme[16]: external_function_monitor is dynamically registered
        bpy.ops.script.external_function_monitor(
            function=fn_name, monitored_packages=monitored_packages_str
        )
    except Exception as ex:
        import logging

        logging.exception(f"unhandled exception: {ex}")
        sys.exit(1)
