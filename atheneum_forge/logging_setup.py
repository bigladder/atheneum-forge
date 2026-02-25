import logging
import logging.config

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.logging import RichHandler
from rich.theme import Theme
from textual.widget import Widget
from textual.widgets import RichLog


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


config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"defaultFormatter": {"format": "%(asctime)s  [%(levelname)s]   %(message)s", "use_colors": False}},
    "handlers": {
        "defaultFileHandler": {
            "formatter": "defaultFormatter",
            "class": "logging.FileHandler",
            "filename": "atheneum_forge.log",
            "level": "ERROR",
            "delay": True,
        },
        "richHandler-tui": {
            "class": RichHandler,
            "level": "INFO",
            "console": LoggingConsole(),
            "rich_tracebacks": True,
            "formatter": "defaultFormatter",
        },
        "richHandler-cli": {
            "class": RichHandler,
            "level": "INFO",
            "show_time": False,
            "highlighter": FileStatusHighlighter(),
            "console": console,
            "markup": True,
        },
    },
    "loggers": {
        "forge": {
            "handlers": ["defaultFileHandler", "richHandler-tui", "richHandler-cli"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

logging.config.dictConfig(config)
