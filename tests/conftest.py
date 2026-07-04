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
product_paths = []
for path in runtime_paths:
    product_root = Path(path) / "product"
    if product_root.exists():
        product_paths.append(str(product_root))

for path in reversed(product_paths):
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(1, path)

for module_name in list(sys.modules):
    if module_name == "runtime" or module_name.startswith("runtime."):
        sys.modules.pop(module_name, None)

runtime_module = types.ModuleType("runtime")
runtime_module.__path__ = runtime_paths
runtime_module.__package__ = "runtime"
runtime_module.__spec__ = importlib.machinery.ModuleSpec("runtime", loader=None, is_package=True)
runtime_module.__spec__.submodule_search_locations = runtime_paths
sys.modules["runtime"] = runtime_module

if product_paths:
    product_module = types.ModuleType("runtime.product")
    product_module.__path__ = product_paths
    product_module.__package__ = "runtime.product"
    product_module.__spec__ = importlib.machinery.ModuleSpec("runtime.product", loader=None, is_package=True)
    product_module.__spec__.submodule_search_locations = product_paths
    runtime_module.product = product_module
    sys.modules["runtime.product"] = product_module
