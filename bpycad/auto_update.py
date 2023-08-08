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
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


_instance: Optional[MonitorOperatorBase] = None


class MonitorOperatorBase(bpy.types.Operator):
    """Monitor an external script for changes and re-run on change."""

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

    _monitored_paths: List[Path] = []
    _monitored_modules: List[str] = []
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
        self.on_change(force_refresh_module_list=True)

        wm = context.window_manager
        self._timer = wm.event_timer_add(
            self.poll_interval, window=context.window
        )
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _refresh_monitored_modules(self) -> None:
        self._monitored_modules, self._monitored_paths = (
            self._init_monitor_modules()
        )

        self.report({"INFO"}, f"monitoring modules for {self._name}")
        self._timestamps = self._get_timestamps()

    def _init_monitor_modules(self) -> Tuple[List[str], List[Path]]:
        monitored_modules: List[str] = []
        monitored_paths: List[Path] = []

        for mod_name, module in sys.modules.items():
            mod_path = getattr(module, "__file__", None)
            if mod_path is None:
                continue

            for pkg in self._monitored_packages:
                if mod_name == pkg or mod_name.startswith(pkg + "."):
                    monitored_modules.append(mod_name)
                    monitored_paths.append(Path(mod_path))
                    break

        return monitored_modules, monitored_paths

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
        self._purge_loaded_modules()
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
        for path in self._monitored_paths:
            result[path] = self._get_timestamp(path)
        return result

    def _get_timestamp(self, path: Path) -> Optional[float]:
        try:
            s = path.stat()
        except IOError:
            return None
        return s.st_mtime

    def on_change(self, force_refresh_module_list: bool = False) -> None:
        if self.delete_all:
            if bpy.context.object is not None:
                bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete(use_global=False)

        print("=" * 60, file=sys.stderr)
        print(f"Running {self._name}...", file=sys.stderr)
        self.report({"INFO"}, f"running {self._name}")

        error = False
        try:
            self._run()
            print(f"Finished {self._name}")
        except Exception as ex:
            # If your editor replaces files by removing the old one before
            # writing out the new file, we can attempt to reload the module
            # before it has been written out completely, which will result in
            # an error here.  This is okay, we will keep monitoring and
            # will reload again once the editor has finished writing out the
            # full new file.
            self._report_error(f"error running {self._name}")
            error = True

        if force_refresh_module_list or not error:
            # Only refresh the list of monitored modules after a successful run.
            self._refresh_monitored_modules()

    def _init(self) -> None:
        pass

    def _run(self) -> None:
        raise NotImplementedError("must be implemented by a subclass")

    def _report_error(self, msg: str) -> None:
        err_str = traceback.format_exc()
        self.report({"INFO"}, f"{msg}: {err_str}")
        print(f"{msg}: {err_str}")


class CancelMonitorOperator(bpy.types.Operator):
    """Monitor an external script for changes and re-run on change."""

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

    def _init_monitor_modules(self) -> Tuple[List[str], List[Path]]:
        if self.monitored_packages is not None:
            # If an explicit set of packages to monitor was specified,
            # just use that.
            return super()._init_monitor_modules()

        monitored_modules: List[str] = []
        monitored_paths: List[Path] = [self._abs_path]

        for mod_name, module in sys.modules.items():
            mod_path_str = getattr(module, "__file__", None)
            if mod_path_str is None:
                continue
            mod_path = Path(mod_path_str)

            if self._local_dir in mod_path.parents:
                monitored_modules.append(mod_name)
                monitored_paths.append(Path(mod_path))

        return monitored_modules, monitored_paths

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


# Register and add to the "view" menu (required to also use F3 search "Modal Timer Operator" for quick access)
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
