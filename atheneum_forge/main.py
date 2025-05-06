"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import logging
from pathlib import Path
from subprocess import CalledProcessError

import typer
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme
from typing_extensions import Annotated

from atheneum_forge import core, project_factory


class FileStatusHighlighter(RegexHighlighter):
    """Apply style to generator and renderer messages."""

    base_style = "example."
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
    handlers=[RichHandler(show_time=False, highlighter=FileStatusHighlighter(), console=console, markup=True)],
)

console_log = logging.getLogger("rich")

# Optional file logger:
# formatter = logging.Formatter('%(asctime)s  [%(levelname)s]   %(message)s')
# file_handler = FileHandler("atheneum_forge_log.txt", mode='w')
# file_handler.setFormatter(formatter)
# console_log.addHandler(file_handler)

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


# def setup_dir(config_path: Path) -> dict:
#     """
#     Helper function to do common setup.
#     """
#     p_config = Path(config_path).resolve()
#     if not p_config.exists():
#         console_log.error(f'Config file "{p_config}" doesn\'t exist.')
#         raise typer.Exit(code=3)
#     if not p_config.is_file():
#         console_log.error(f'Config "{p_config}" is not a file.')

#     tgt_dir = p_config.parent
#     if not tgt_dir.exists() or not p_config.exists():
#         console_log.error("Project directory or config file do not exist.")
#         raise typer.Exit(code=2)
#     config_toml = core.read_toml(p_config)
#     project_type = config_toml["project_type"]

#     src_dir = DATA_DIR / project_type
#     if not src_dir.exists() or not src_dir.is_dir():
#         console_log.error(f'"{src_dir}" does not exist or is not a directory.')
#         raise typer.Exit(code=1)
#     manifest = core.read_toml(src_dir / "manifest.toml")
#     target_files = core.list_files_in(tgt_dir)
#     try:
#         config = core.merge_defaults_into_config(config_toml, manifest["parameters"], target_files)
#     except (TypeError, RuntimeError) as err:
#         console_log.error("Error while processing config file.")
#         console_log.error(err)
#         raise typer.Exit(code=1)
#     return {
#         "p_config": p_config,
#         "config": config,
#         "tgt_dir": tgt_dir,
#         "src_dir": src_dir,
#         "manifest": manifest,
#         "all_files": target_files,
#     }


@app.command("generate")
def generate_project_files(  # type: ignore
    project_path: Annotated[Path, typer.Argument(help="Directory location of the project.")],
    git_init: Annotated[bool, typer.Option(help="Initialize git repository in project directory.")] = True,
    submodule_init: Annotated[
        bool, typer.Option(help="Initialize git submodules in project vendor directory, if applicable.")
    ] = True,
    generator=None,  # Can't type with the abc class
) -> None:
    """
    (Re-)Generate project from template files.
    If initialize submodules is True, the config path must be within a git repo.
    Initializing submodules will set up the vendor directory.
    """
    if not generator:
        type = project_factory.GeneratedProject.get_project_type(project_path)
        if type == project_factory.ProjectType.cpp:
            generator = project_factory.GeneratedCPP(project_path)
        elif type == project_factory.ProjectType.python:
            generator = project_factory.GeneratedPython(project_path)
        else:
            console_log.error("Project type was not found.")
            raise typer.Exit(1)

    result = generator.generate(project_path)  # type: ignore
    for r in result:
        console_log.info(
            f"- {r}",
        )

    if git_init:
        try:
            core.run_commands(generator.init_git_repo() + generator.init_pre_commit())  # type: ignore
        except CalledProcessError as err:
            console_log.error(err)

    if submodule_init:
        try:
            core.run_commands(generator.init_submodules())  # type: ignore
        except CalledProcessError as err:
            console_log.error(err)


ProjType = project_factory.ProjectType


@app.command("init")
def initialize_configuration(  # noqa: PLR0913
    project_path: Annotated[Path, typer.Argument(help="Directory location of the new project.")],
    project_name: Annotated[str, typer.Argument(help="Name of the project.")],
    type: ProjType = ProjType.none,
    generate: Annotated[
        bool, typer.Option(help="Automatically generate project files alongside configuration.")
    ] = True,
    git_init: Annotated[bool, typer.Option(help="Initialize git repository in project directory.")] = True,
    submodule_init: Annotated[
        bool, typer.Option(help="Initialize git submodules in project vendor directory, if applicable.")
    ] = True,
    force: Annotated[bool, typer.Option(help="Overwrite project configuration file.")] = False,
) -> None:
    """
    Generate a directory and empty config file for the given project type. (Existing
    configuation files will not be overwritten without the --force flag.)
    """
    try:
        generator: project_factory.GeneratedProject | None
        if type == ProjType.none:
            # We'd like 'type' to be specified as an optional argument, but a "valid" default could have
            # unintended consequences.
            console_log.info("Please specify a valid type (use [red]--help[/red] for options).")
            raise typer.Exit(code=1)
        elif type == ProjType.cpp:
            generator = project_factory.GeneratedCPP(project_path, project_name, force)
        elif type == ProjType.python:
            generator = project_factory.GeneratedPython(project_path, project_name, force)
        if git_init or submodule_init:
            if not generate:
                # In a python project the pre-commit tool is only installed once pyproject.toml is read,
                # so it can't be called without file generation
                console_log.info(
                    "Git repository not initialized ([red]--no-git-init[/] applied). Please generate "
                    "project files first."
                )
        if generate:
            generate_project_files(project_path, git_init=git_init, submodule_init=submodule_init, generator=generator)
    except RuntimeError:
        raise typer.Exit(code=1)


# @app.command()
# def update_copyright(config_path: Path, project_type: str, silent: bool = False) -> None:
#     """
#     Run a task to update copyright headers over all recognized files.
#     """
#     typer.echo("Updating copyright header in files...")
#     data = setup_dir(config_path)
#     copy_data_by_file = core.gen_copyright(
#         data["config"], data["manifest"]["task"]["copyright"]["copy"], data["all_files"]
#     )
#     for file_path, copy_lines in copy_data_by_file.items():
#         path = data["tgt_dir"] / file_path
#         content = None
#         with open(path, "r") as fid:
#             content = fid.read()
#         add_newline = content[-1] == "\n"
#         new_content = core.update_copyright(content, copy_lines)
#         if add_newline:
#             new_content += "\n"
#         if new_content != content:
#             with open(path, "w") as fid:
#                 fid.write(new_content)
#             if not silent:
#                 console_log.info(f"... updated copyright for {file_path}")
#         elif not silent:
#             console_log.info(f"... copyright up to date for {file_path}")
