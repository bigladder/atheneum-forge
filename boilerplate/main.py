"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import sys
from pathlib import Path
import tomllib

import typer

from .core import generate, create_config_toml, read_config


app = typer.Typer()


THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = (THIS_DIR / ".." / "data").resolve()


@app.command()
def gen(config_path: str, project_type: str):
    """
    (Re-)Generate project from template files.
    """
    typer.echo(f"Generating files for {project_type} at {config_path}")
    p_config = Path(config_path).resolve()
    if not p_config.exists():
        print(f"ERROR: config file doesn't exist: {p_config}")
        sys.exit(3)
    if not p_config.is_file():
        print(f"ERROR: config is not a file: {p_config}")
    tgt_dir = p_config.parent
    src_dir = DATA_DIR / project_type
    if not src_dir.exists() or not src_dir.is_dir():
        print("ERROR")
        sys.exit(1)
    if not tgt_dir.exists() or not p_config.exists():
        print("ERROR")
        sys.exit(2)
    with open(src_dir / "manifest.toml", "rb") as fid:
        manifest = tomllib.load(fid)
    with open(p_config, "r") as fid:
        config_toml = fid.read()
    config = read_config(config_toml, manifest["parameters"])
    result, is_ok = generate(src_dir, tgt_dir, manifest, config, dry_run=False)
    if not is_ok:
        print("[ERROR]  error while processing... not all tasks completed successfully")
    for r in result:
        print(f"- {r}")


@app.command()
def config_for(config_path: str, project_type: str):
    """
    Generate an empty config file for the given project type.
    """
    typer.echo(f"Generating config.toml for {project_type} at {config_path}")
    p_config = Path(config_path).resolve()
    p_manifest = DATA_DIR / project_type / "manifest.toml"
    with open(p_manifest, "rb") as fid:
        manifest = tomllib.load(fid)
    config_str = create_config_toml(manifest)
    p_config.parent.mkdir(parents=True, exist_ok=True)
    with open(p_config, "w") as fid:
        fid.write(config_str)
