"""Smoke test for the built wheel / sdist.

Run by release.yaml against the built artifact in an isolated, no-project
environment, e.g.::

    uv run --isolated --no-project --with dist/*.whl tests/smoke_test.py

It must therefore inspect the *installed* package (resolved via import,
importlib.resources, and importlib.metadata), never the source checkout on
disk -- otherwise it would pass even when the artifact is broken or missing its
bundled data files.
"""

import importlib.metadata
import importlib.resources
import subprocess

import atheneum_forge
from atheneum_forge._version import __version__

# 1. The package imports and reports a real version.
assert __version__, "version is empty"
assert atheneum_forge.logging_setup is not None

# 2. The bundled template trees are present in the installed package.
langs = importlib.resources.files("atheneum_forge") / "languages"
for lang in ("cpp", "python"):
    assert (langs / lang).is_dir(), f"missing language tree: {lang}"

# 3. Representative data files actually shipped (catches "only .py got packaged").
for data_file in (
    langs / "cpp" / "manifest.toml",
    langs / "cpp" / "main_CMakeLists.txt.j2",
    langs / "python" / "manifest.toml",
    langs / "python" / "pyproject.toml",
):
    assert data_file.is_file(), f"missing bundled data file: {data_file}"

# 4. The declared console entry points are registered and their targets resolve.
#    ep.load() imports the module and attribute WITHOUT calling it -- important
#    because `forge` launches an interactive TUI that would hang CI.
entry_points = {ep.name: ep for ep in importlib.metadata.entry_points(group="console_scripts")}
for name in ("forge", "forge-cli"):
    assert name in entry_points, f"missing console_scripts entry point: {name}"
    entry_points[name].load()

# 5. The non-interactive CLI runs end-to-end.
subprocess.run(["forge-cli", "--help"], check=True)

print(f"smoke test OK: atheneum-forge {__version__}")
