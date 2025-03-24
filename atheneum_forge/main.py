"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import logging
import tomllib
from enum import Enum
from pathlib import Path

import typer
from rich.logging import RichHandler
from typing_extensions import Annotated

# from rich.highlighter import RegexHighlighter
# from rich.theme import Theme
from atheneum_forge import core

logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[RichHandler()])


console_log = logging.getLogger("rich")
# Optional file logger:
# formatter = logging.Formatter('%(asctime)s  [%(levelname)s]   %(message)s')
# file_handler = FileHandler("atheneum_forge_log.txt", mode='w')
# file_handler.setFormatter(formatter)
# console_log.addHandler(file_handler)

app = typer.Typer(pretty_exceptions_enable=False)

THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = (THIS_DIR / ".." / "data").resolve()


# class FileStatusHighlighter(RegexHighlighter):
#     """Apply style to generator and renderer messages."""

#     base_style = "example."
#     highlights = [r"(?P<status>([A-Z]*-?)])*[A-Z]"]


# theme = Theme({"example.status": "bold magenta"})


class ProjectType(Enum):
    CPP = "cpp"
    PY = "python"


def setup_dir(config_path: Path, project_type: str) -> dict:
    """
    Helper function to do common setup.
    """
    p_config = Path(config_path).resolve()
    if not p_config.exists():
        console_log.error(f'Config file "{p_config}" doesn\'t exist.')
        raise typer.Exit(code=3)
    if not p_config.is_file():
        console_log.error(f'Config "{p_config}" is not a file.')
    tgt_dir = p_config.parent
    src_dir = DATA_DIR / project_type
    if not src_dir.exists() or not src_dir.is_dir():
        console_log.error(f'"{src_dir}" does not exist or is not a directory.')
        raise typer.Exit(code=1)
    if not tgt_dir.exists() or not p_config.exists():
        console_log.error("Project directory or config file do not exist.")
        raise typer.Exit(code=2)
    with open(src_dir / "manifest.toml", "rb") as fid:
        manifest = tomllib.load(fid)
    with open(p_config, "r") as fid:
        config_toml = fid.read()
    target_files = core.list_all_files(tgt_dir)
    try:
        config = core.read_config(config_toml, manifest["parameters"], target_files)
    except (TypeError, RuntimeError) as err:
        console_log.error("Error while processing config file.")
        console_log.error(err)
        raise typer.Exit(code=1)
    return {
        "p_config": p_config,
        "config": config,
        "tgt_dir": tgt_dir,
        "src_dir": src_dir,
        "manifest": manifest,
        "all_files": target_files,
    }


@app.command()
def gen(
    config_path: Annotated[Path, typer.Argument(help="Fully qualified path of the forge.toml file.")],
    project_type: Annotated[ProjectType, typer.Argument()] = ProjectType.CPP,
    init_submodules: bool = False,
):
    """
    (Re-)Generate project from template files.
    If initialize submodules is True, the config path must be within a git repo.
    Initializing submodules will set up the vendor directory.
    """
    console_log.info(f"Generating files for {project_type} at {config_path}")
    data = setup_dir(config_path, project_type.value)
    result = core.generate(
        data["src_dir"],
        data["tgt_dir"],
        data["manifest"],
        data["config"],
        dry_run=False,
    )
    # if not is_ok:
    #     console_log.error("Error while processing... not all tasks completed successfully.")
    if init_submodules:  # TODO: check for cpp project
        cmds = core.setup_vendor(data["config"], data["p_config"].parent)
        is_ok = core.run_commands(cmds)
        if not is_ok:
            console_log.error("Error running commands...")
    for r in result:
        console_log.info(f"- {r}", extra={"highlighter": None})


@app.command("init")
def initialize_with_config(
    project_path: Annotated[Path, typer.Argument(help="Directory location of the new project.")],
    project_type: Annotated[str, typer.Argument()] = ProjectType.CPP.value,
    git_init: bool = False,
    force: bool = False,
):
    """
    Generate a directory and empty config file for the given project type. (Existing
    configuation files will not be overwritten without the --force flag.)
    If git-init is true, also initialize a git repository.
    """
    p_config = Path(project_path).resolve()
    p_manifest = DATA_DIR / project_type / "manifest.toml"
    with open(p_manifest, "rb") as fid:
        manifest = tomllib.load(fid)
    config_str = core.create_config_toml(manifest)
    p_config.mkdir(parents=True, exist_ok=True)
    configuration_file = p_config / "forge.toml"
    if configuration_file.exists():
        if not force:
            console_log.info(
                f'{configuration_file}" already exists. Use [red]--force[/red] to overwrite.', extra={"markup": True}
            )
            raise typer.Exit(1)
    with open(configuration_file, "w") as fid:
        fid.write(config_str)
        console_log.info(f"Generated {project_type} config file at {configuration_file}")
    if git_init:
        cmds = core.init_git_repo(p_config.parent)
        core.run_commands(cmds)


@app.command("update")
def update_config(
    project_path: Annotated[Path, typer.Argument(help="Directory location of the new project.")],
    project_type: Annotated[ProjectType, typer.Argument()] = ProjectType.CPP,
): ...


@app.command()
def task_update_copyright(config_path: Path, project_type: str, silent: bool = False):
    """
    Run a task to update copyright headers over all recognized files.
    """
    typer.echo("Updating copyright header in files...")
    data = setup_dir(config_path, project_type)
    copy_data_by_file = core.gen_copyright(
        data["config"], data["manifest"]["task"]["copyright"]["copy"], data["all_files"]
    )
    for file_path, copy_lines in copy_data_by_file.items():
        path = data["tgt_dir"] / file_path
        content = None
        with open(path, "r") as fid:
            content = fid.read()
        add_newline = content[-1] == "\n"
        new_content = core.update_copyright(content, copy_lines)
        if add_newline:
            new_content += "\n"
        if new_content != content:
            with open(path, "w") as fid:
                fid.write(new_content)
            if not silent:
                console_log.info(f"... updated copyright for {file_path}")
        elif not silent:
            console_log.info(f"... copyright up to date for {file_path}")
