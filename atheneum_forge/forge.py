# SPDX-FileCopyrightText: © 2025 Big Ladder Software <info@bigladdersoftware.com>
# SPDX-License-Identifier: BSD-3-Clause

import logging
import re
from pathlib import Path
from subprocess import CalledProcessError

from jinja2 import Environment, FileSystemLoader

from atheneum_forge import core, project_factory

logger = logging.getLogger("forge")


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


class AtheneumForge:
    def __init__(self):
        self.generator: project_factory.GeneratedProject | None = None

    def initialize_configuration(  # noqa: PLR0913, PLR0917
        self,
        project_path: Path,
        project_name: str,
        type: project_factory.ProjectType = project_factory.ProjectType.none,
        generate: bool = True,
        git_init: bool = True,
        submodule_init: bool = True,
        force: bool = False,
    ) -> None:
        """
        Generate a directory and empty config file for the given project type. (Existing
        configuation files will not be overwritten without the --force flag.)
        """
        ProjType = project_factory.ProjectType

        if not project_name:
            project_name = Path(project_path).resolve().name  # normalized or raw?

        # Deliberate control flow: invalid type is a usage error, raised directly (not wrapped).
        if type == ProjType.none:
            # We'd like 'type' to be specified as an optional argument, but a "valid" default could have
            # unintended consequences.
            logger.error("Please specify a valid type (use [red]--help[/red] for options).")
            raise RuntimeError("No project type specified.")

        # Step 1: construct the generator (creates/validates the config file).
        try:
            if type == ProjType.cpp:
                self.generator = project_factory.GeneratedCPP(project_path, project_name, force)
            else:  # ProjType.python
                self.generator = project_factory.GeneratedPython(project_path, project_name, force)
        except FileNotFoundError as err:  # missing sources, or no name and no existing config
            logger.error(f"Could not locate project sources or configuration: {err}")
            raise
        except RuntimeError as err:  # config exists without force, or config processing failed
            logger.error(err)
            raise

        if (git_init or submodule_init) and not generate:
            # In a python project the pre-commit tool is only installed once pyproject.toml is read,
            # so it can't be called without file generation.
            logger.info(
                "Git repository not initialized ([red]--no-git-init[/] applied). Please generate project files first."
            )

        if not generate:
            return

        # Step 2: generate project files (and optionally init git/submodules).
        try:
            self.generate_project_files(project_path, git_init=git_init, submodule_init=submodule_init)
        except (FileNotFoundError, RuntimeError) as err:  # _check_directories / collect_source_files / manifest
            logger.error(f"Project files could not be generated: {err}")
            raise
        except CalledProcessError as err:  # bubbled up from _git_init / _submodule_init
            logger.error(f"Git/submodule initialization failed: {err}")
            # files are already generated; the repo is usable, so don't abort

    def generate_project_files(  # type: ignore
        self, project_path: Path, git_init: bool = True, submodule_init: bool = True
    ) -> None:
        """
        (Re-)Generate project from template files.
        If initialize submodules is True, the config path must be within a git repo.
        Initializing submodules will set up the vendor directory.
        """
        if not self.generator:
            type = project_factory.GeneratedProject.get_project_type(project_path)
            if type == project_factory.ProjectType.cpp:
                self.generator = project_factory.GeneratedCPP(project_path)
            elif type == project_factory.ProjectType.python:
                self.generator = project_factory.GeneratedPython(project_path)
            else:
                logger.error("Project type was not found.")

        result = self.generator.generate(project_path)  # type: ignore
        for r in result:
            logger.info(
                f"- {r}",
            )

        if submodule_init:
            self._git_init()
            self._submodule_init()
        elif git_init:
            self._git_init()

    def _submodule_init(self):
        try:
            core.run_commands(self.generator.init_submodules())  # type: ignore
        except CalledProcessError as err:
            logger.error(err)
            raise err

    def _git_init(self):
        try:
            core.run_commands(self.generator.init_git_repo() + self.generator.init_pre_commit())  # type: ignore
        except CalledProcessError as err:
            logger.error(err)
            raise err

    def update_project_files(
        self,
        project_path: Path,
    ) -> None:
        """Shorthand command that calls generate under the hood.

        Args:
            project_path
        """
        return self.generate_project_files(project_path, False, False)

    def add_owner_copyright(self, source_path: Path) -> None:
        env = Environment(loader=FileSystemLoader(Path(__file__).parent, encoding="utf-8"), keep_trailing_newline=True)
        for file in source_path.iterdir():
            if self.generator:
                core.prepend_copyright_to_copy(
                    file, core.render_copyright_string(env, self.generator.configuration, file)
                )
            else:
                logger.info("Select a project type before adding copyright to files.")

    def edit_config(self, edits: dict[str, str]) -> None:
        if self.generator:
            self.generator.edit_forge_config(edits)
