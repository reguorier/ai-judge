from __future__ import annotations

import importlib.machinery
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "runtime"
DESKTOP_RUNTIME_NAMESPACE_ROOT = (
    Path.home()
    / "Library"
    / "Application Support"
    / "AI Judge"
    / "runtime"
)
DESKTOP_USER_RUNTIME_NAMESPACE_ROOT = (
    Path.home()
    / "Library"
    / "Application Support"
    / "AI Judge"
    / "user-app-support"
    / "runtime"
)
DESKTOP_RUNTIME_PACKAGE_ROOT = (
    Path.home()
    / "Library"
    / "Application Support"
    / "AI Judge"
    / "runtime"
    / "product"
    / "runtime"
)

root = str(PROJECT_ROOT)
if root in sys.path:
    sys.path.remove(root)
sys.path.insert(0, root)

runtime_paths = [str(RUNTIME_ROOT)]
for path in (
    DESKTOP_RUNTIME_NAMESPACE_ROOT,
    DESKTOP_USER_RUNTIME_NAMESPACE_ROOT,
    DESKTOP_RUNTIME_PACKAGE_ROOT,
):
    if path.exists():
        runtime_paths.append(str(path))

runtime_module = types.ModuleType("runtime")
runtime_module.__path__ = runtime_paths
runtime_module.__package__ = "runtime"
runtime_module.__spec__ = importlib.machinery.ModuleSpec("runtime", loader=None, is_package=True)
runtime_module.__spec__.submodule_search_locations = runtime_paths
sys.modules["runtime"] = runtime_module
