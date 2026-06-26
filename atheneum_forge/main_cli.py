# SPDX-FileCopyrightText: © 2025 Big Ladder Software <info@bigladdersoftware.com>
# SPDX-License-Identifier: BSD-3-Clause

import logging
from pathlib import Path
from subprocess import CalledProcessError

import typer
from typing_extensions import Annotated

from atheneum_forge import core, project_factory

console_log = logging.getLogger("forge")

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


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
    If submodule_init is True, a git repo will be created.
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
def initialize_configuration(  # noqa: PLR0913, PLR0917
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
    # Deliberate control flow: keep OUT of any try so it can't be swallowed.
    if type == ProjType.none:
        # We'd like 'type' to be specified as an optional argument, but a "valid" default could have
        # unintended consequences.
        console_log.info("Please specify a valid type (use [red]--help[/red] for options).")
        raise typer.Exit(code=1)

    # Step 1: construct the generator (creates/validates the config file).
    try:
        if type == ProjType.cpp:
            generator: project_factory.GeneratedProject = project_factory.GeneratedCPP(
                project_path, project_name, force
            )
        else:  # ProjType.python
            generator = project_factory.GeneratedPython(project_path, project_name, force)
    except FileNotFoundError as err:  # missing source dir, or no name and no existing config
        console_log.error(f"Could not locate project sources or configuration: {err}")
        raise typer.Exit(code=1) from err
    except RuntimeError as err:  # config exists without --force, or config processing failed
        console_log.error(err)
        raise typer.Exit(code=1) from err

    if (git_init or submodule_init) and not generate:
        # In a python project the pre-commit tool is only installed once pyproject.toml is read,
        # so it can't be called without file generation.
        console_log.info(
            "Git repository not initialized ([red]--no-git-init[/] applied). Please generate project files first."
        )

    if not generate:
        return

    # Step 2: generate project files from the now-valid configuration.
    try:
        generate_project_files(project_path, git_init=git_init, submodule_init=submodule_init, generator=generator)
    except FileNotFoundError as err:  # _check_directories / collect_source_files
        console_log.error(f"Project files could not be generated: {err}")
        raise typer.Exit(code=1) from err
    except RuntimeError as err:
        console_log.error(err)
        raise typer.Exit(code=1) from err
