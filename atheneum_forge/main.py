"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import logging
from enum import Enum
from pathlib import Path
from subprocess import CalledProcessError

import tomllib
import typer
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme
from typing_extensions import Annotated

from atheneum_forge import core


class FileStatusHighlighter(RegexHighlighter):
    """Apply style to generator and renderer messages."""

    base_style = "example."
    # highlights = [r"(?P<status>([A-Z]*)(-?[A-Z]*)*)"]
    highlights = [r"(?P<status_copy>COPY)", r"(?P<status_render>RENDER)", r"(?P<status_skipped>SKIPPED)"]


console = Console(
    theme=Theme(
        {
            "example.status_copy": "spring_green3",
            "example.status_render": "dark_magenta",
            "example.status_skipped": "grey53",
        }
    )
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, highlighter=FileStatusHighlighter(), console=console)],
)

console_log = logging.getLogger("rich")

# Optional file logger:
# formatter = logging.Formatter('%(asctime)s  [%(levelname)s]   %(message)s')
# file_handler = FileHandler("atheneum_forge_log.txt", mode='w')
# file_handler.setFormatter(formatter)
# console_log.addHandler(file_handler)

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)

THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = (THIS_DIR / ".." / "data").resolve()
FORGE_CONFIG = "forge.toml"


class ProjectType(str, Enum):
    cpp = "cpp"
    python = "python"


def setup_dir(config_path: Path) -> dict:
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
    if not tgt_dir.exists() or not p_config.exists():
        console_log.error("Project directory or config file do not exist.")
        raise typer.Exit(code=2)
    config_toml = core.read_toml(p_config)
    project_type = config_toml["project_type"]

    src_dir = DATA_DIR / project_type
    if not src_dir.exists() or not src_dir.is_dir():
        console_log.error(f'"{src_dir}" does not exist or is not a directory.')
        raise typer.Exit(code=1)
    manifest = core.read_toml(src_dir / "manifest.toml")
    target_files = core.list_all_files(tgt_dir)
    try:
        config = core.merge_defaults_into_config(config_toml, manifest["parameters"], target_files)
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


@app.command("gen")
def generate(
    config_path: Annotated[Path, typer.Argument(help="Directory location of the project.")],
    init_submodules: bool = False,
) -> None:
    """
    (Re-)Generate project from template files.
    If initialize submodules is True, the config path must be within a git repo.
    Initializing submodules will set up the vendor directory.
    """
    data = setup_dir(config_path / FORGE_CONFIG)
    console_log.info(f"Generating files for {data['config']['project_type']} at {config_path}")
    result = core.generate(
        data["config"]["project_name"],
        data["src_dir"],
        data["tgt_dir"],
        data["manifest"],
        data["config"],
        dry_run=False,
    )
    if init_submodules:  # TODO: check for cpp project
        cmds = core.setup_vendor(data["config"], data["p_config"].parent)
        try:
            core.run_commands(cmds)
        except CalledProcessError as err:
            console_log.error(err)
    for r in result:
        console_log.info(
            f"- {r}",
        )


@app.command("init")
def initialize_with_config(
    project_path: Annotated[Path, typer.Argument(help="Directory location of the new project.")],
    project_name: Annotated[str, typer.Argument(help="Name of the project.")],
    type: ProjectType = ProjectType.cpp,
    git_init: bool = True,
    force: bool = False,
    autogen: bool = True,
) -> None:
    """
    Generate a directory and empty config file for the given project type. (Existing
    configuation files will not be overwritten without the --force flag.)
    If git-init is true, also initialize a git repository.
    """
    p_config = Path(project_path).resolve()
    p_manifest = DATA_DIR / type.value / "manifest.toml"
    with open(p_manifest, "rb") as fid:
        manifest = tomllib.load(fid)
    config_str = core.create_config_toml(manifest, project_name)
    p_config.mkdir(parents=True, exist_ok=True)
    configuration_file = p_config / FORGE_CONFIG
    if configuration_file.exists():
        if not force:
            console_log.info(
                f'{configuration_file}" already exists. Use [red]--force[/red] to overwrite.', extra={"markup": True}
            )
            raise typer.Exit(1)
    with open(configuration_file, "w") as fid:
        fid.write(config_str)
        console_log.info(f"Generated {type.value} config file at {configuration_file}")
    if autogen:
        generate(p_config)
    if git_init:
        if not autogen:
            # In a python project the pre-commit tool is only installed once pyproject.toml is read,
            # so it can't be called without file generation
            console_log.info("Git repository not initialized ([red]--no-git-init[/] applied).", extra={"markup": True})
        else:
            cmds = core.init_git_repo(p_config) + core.init_pre_commit(p_config, type.value)
            core.run_commands(cmds)


@app.command()
def update_copyright(config_path: Path, project_type: str, silent: bool = False) -> None:
    """
    Run a task to update copyright headers over all recognized files.
    """
    typer.echo("Updating copyright header in files...")
    data = setup_dir(config_path)
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
