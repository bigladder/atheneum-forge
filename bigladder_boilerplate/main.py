"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import sys
from pathlib import Path
import tomllib

import typer

import bigladder_boilerplate.core as core


app = typer.Typer()


THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = (THIS_DIR / ".." / "data").resolve()


@app.command()
def gen(config_path: str, project_type: str, init_submodules: bool = False):
    """
    (Re-)Generate project from template files.
    If initialize submodules is True, the config path must be within a git repo.
    Initializing submodules will set up the vendor directory.
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
    all_files = core.list_all_files(tgt_dir)
    config, is_ok = core.read_config(config_toml, manifest["parameters"], all_files)
    if not is_ok:
        print("[ERROR] error while processing config file")
        sys.exit(1)
    result, is_ok = core.generate(src_dir, tgt_dir, manifest, config, dry_run=False)
    if not is_ok:
        print("[ERROR] error while processing... not all tasks completed successfully")
    if init_submodules:
        cmds = core.setup_vendor(config, p_config.parent)
        is_ok = core.run_commands(cmds)
        if not is_ok:
            print("[ERROR] error running commands...")
    for r in result:
        print(f"- {r}")


@app.command()
def init_with_config(config_path: str, project_type: str, git_init: bool = False):
    """
    Generate a directory and empty config file for the given project type.
    If git-init is true, also initialize a git repository.
    """
    typer.echo(f"Generating config.toml for {project_type} at {config_path}")
    p_config = Path(config_path).resolve()
    p_manifest = DATA_DIR / project_type / "manifest.toml"
    with open(p_manifest, "rb") as fid:
        manifest = tomllib.load(fid)
    config_str = core.create_config_toml(manifest)
    p_config.parent.mkdir(parents=True, exist_ok=True)
    with open(p_config, "w") as fid:
        fid.write(config_str)
    if git_init:
        cmds = core.init_git_repo(p_config.parent)
        core.run_commands(cmds)
