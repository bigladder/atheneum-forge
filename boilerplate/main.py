"""
Copyright (C) 2024 Big Ladder Software, LLC. See LICENSE.txt for license information.
"""

import typer

from .core import generate


app = typer.Typer()


@app.command()
def gen(config_path: str, project_type: str):
    """
    (Re-)Generate project from template files.
    """
    typer.echo(f"Generating files for {project_type} at {config_path}")


@app.command()
def config_for(config_path: str, project_type: str):
    """
    Generate an empty config file for the given project type.
    """
    typer.echo(f"Generating config.toml for {project_type} at {config_path}")
