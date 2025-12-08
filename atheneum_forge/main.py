# SPDX-FileCopyrightText: © 2025 Big Ladder Software <info@bigladdersoftware.com>
# SPDX-License-Identifier: BSD-3-Clause

import logging
from pathlib import Path
from typing import Iterable

from rich.logging import RichHandler
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, VerticalGroup
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Header,
    Input,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from .forge import AtheneumForge, project_factory

# TODO: Explore this idea for a Textual logging handler
# class RichLogHandler(logging.Handler):
#     def __init__(self, rich_log_widget: RichLog):
#         super().__init__()
#         self.rich_log_widget = rich_log_widget

#     def emit(self, record):
#         msg = self.format(record)
#         self.rich_log_widget.write(msg)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forge")

formatter = logging.Formatter("%(asctime)s  [%(levelname)s]   %(message)s")
file_handler = logging.FileHandler("atheneum_forge_log.txt", mode="w")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Lovely little hack from https://github.com/Textualize/textual/discussions/3568
# Derive a console from RichLog, but pretend it has the members of Console so they
# can be manipulated for the RichHandler
class LoggingConsole(RichLog):
    """A RichLog widget that acts as a RichHandler console."""

    file = False
    console: Widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file = False  # Essential for RichHandler to treat it as a console

    def print(self, content):
        """Overrides RichHandler's print method to write to the RichLog."""
        self.write(content)


rich_log_handler = RichHandler(
    console=LoggingConsole(),  # type: ignore
    rich_tracebacks=True,
)
rich_log_handler.setFormatter(formatter)
logger.addHandler(rich_log_handler)


class FolderTree(DirectoryTree):
    """Tree that shows only the entries that are folders."""

    def __init__(
        self,
        path: str | Path,
        title: str,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(path, name=name, id=id, classes=classes, disabled=disabled)
        self.border_title = title

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.is_dir()]


class ForgeUI(App):
    BINDINGS = [("escape", "quit", "Quit application")]

    CSS_PATH = "main.tcss"

    PROJECT_TYPES = ["python", "cpp"]

    def __init__(self):
        super().__init__()
        self.project_dir: Path | None = None
        self.project_subdirectory: Path | None = None
        self.project_name: str = ""
        self.project_type: str = ""
        self.init_submodules: bool = False
        self.init_repo: bool = False
        self.forge = AtheneumForge()

    def compose(self) -> ComposeResult:
        self.theme = "nord"
        yield Header(show_clock=True)
        with Horizontal(id="footer-outer"):
            with Horizontal(id="footer-inner"):
                yield Footer()  # see tcss file for details
            yield Static("", id="status_text")
        with TabbedContent():
            with TabPane("Initial", id="initial_tab"):
                yield Grid(
                    FolderTree(Path.cwd().parent, "Parent_directory", classes="forge-elements", id="parent_directory"),
                    VerticalGroup(
                        Input(id="project_parent", placeholder="Parent directory", classes="forge-elements"),
                        Input(
                            id="project_subdirectory", placeholder="New project subdirectory", classes="forge-elements"
                        ),
                        Input(
                            id="project_name",
                            placeholder="Project name (optional)",
                            classes="forge-elements",
                            tooltip="If a different name than the project subdirectory is desired",
                        ),
                        Select.from_values(
                            ForgeUI.PROJECT_TYPES, prompt="Project type", classes="forge-elements", id="project_type"
                        ),
                    ),
                    VerticalGroup(
                        Checkbox("Initialize git repo", self.init_repo, id="init_repo"),
                        Checkbox("Initialize submodules", self.init_submodules, id="init_submodules"),
                        Button("Configure only", id="configure_only", classes="forge-buttons"),
                        Button("Generate only", id="generate_only", classes="forge-buttons"),
                        Button("Configure and generate", id="configure_and_generate", classes="forge-buttons"),
                    ),
                    id="layout",
                )
            with TabPane("Update", id="update_pane"):
                pass
            with TabPane("Log", id="log_pane"):
                yield rich_log_handler.console  # type: ignore #(actual type "Console", expected type "Widget")

    # def on_mount(self) -> None: #TODO: Alternative to rich_log_handler that might be more canonical
    #     log_widget = self.query_one("#log_window", RichLog)
    #     rich_log_handler = RichLogHandler(log_widget)
    #     formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    #     rich_log_handler.setFormatter(formatter)
    #     logger.addHandler(rich_log_handler)

    @on(DirectoryTree.DirectorySelected)
    def get_project_directory(self, message: DirectoryTree.DirectorySelected) -> None:
        self.project_dir = message.path
        self.query_one("#project_parent", Input).value = str(self.project_dir.resolve())
        self.app.action_focus_next()

    # @on(Input.Blurred)  #TODO: What if you Tab away from the Input
    @on(Input.Submitted)
    def save_project_directories(self):
        self.project_dir = Path(self.query_one("#project_parent", Input).value)
        self.project_subdirectory = Path(self.query_one("#project_subdirectory", Input).value)
        self.project_name = self.query_one("#project_name", Input).value
        self.app.action_focus_next()

    @on(Select.Changed)
    def choose_project_type(self):
        self.project_type = self.query_one("#project_type", Select).value  # type: ignore
        checkbox = self.query_one("#init_submodules", Checkbox)
        checkbox.disabled = True if (self.project_type == "python") else False

    @on(Checkbox.Changed)
    def get_git_options(self, event=Checkbox.Changed):
        if event.control.id == "init_repo":
            self.init_repo = self.query_one("#init_repo", Checkbox).value
        if event.control.id == "init_submodules":
            self.init_submodules = self.query_one("#init_submodules", Checkbox).value

    @on(Button.Pressed)
    def generate_forge_data(self, event=Button.Pressed):
        self.save_project_directories()
        assert self.project_dir
        assert self.project_subdirectory
        project_path: Path = self.project_dir / self.project_subdirectory
        project_name = "" if not self.project_name else self.project_name
        project_type = (
            project_factory.ProjectType.cpp if self.project_type == "cpp" else project_factory.ProjectType.python
        )
        match event.button.id:
            case "configure_only":  # TODO: modal screen to issue force command
                self.forge.initialize_configuration(
                    project_path, project_name, project_type, False, self.init_repo, self.init_submodules, True
                )
            case "generate_only":
                self.forge.generate_project_files(
                    project_path,
                    self.init_repo,
                    self.init_submodules,
                )
            case "configure_and_generate":
                self.forge.initialize_configuration(
                    project_path, project_name, project_type, True, self.init_repo, self.init_submodules, True
                )
                self.query_one("#status_text", Static).update(
                    f"Project successfully generated at {project_path}. See Log for details."
                )

    async def action_quit(self):
        self.exit()


def main():
    instance = ForgeUI()
    instance.run()


if __name__ == "__main__":
    main()
