"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import logging
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import DirectoryTree, Footer, Header, Input, Label, Select


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


class FolderTree(DirectoryTree):
    """Tree that shows only the entries that are folders."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if path.is_dir()]


class ForgeUI(App):
    BINDINGS = [("escape", "quit", "Quit application")]

    CSS = """
    .forge-elements {
        background: purple;
        border: solid white;
        margin: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="New project directory", classes="forge-elements")
        yield FolderTree(".", classes="forge-elements")
        yield Select([("python", 1), ("cpp", 2)], prompt="Project type", classes="forge-elements")
        yield Footer()

    @on(DirectoryTree.DirectorySelected)
    def get_project_directory(self, message: DirectoryTree.DirectorySelected) -> None:
        self.project_dir = message.path
        self.mount(Label(str(self.project_dir)))
        console_log.info(self.project_dir)

    @on(Input.Submitted)
    def save_project_directory(self):
        self.project_dir = Path(self.query_one(Input).value)
        self.mount(Label(str(self.project_dir)))

    async def action_quit(self):
        self.exit()


def main():
    instance = ForgeUI()
    instance.run()


if __name__ == "__main__":
    main()
