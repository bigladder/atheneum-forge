import tomllib

from jinja2 import Template


def render(template: str, config: dict) -> str:
    """
    Render a template using the given data
    - template: Jinja2 template to render
    - config: dict(string, stringable), values to insert into template
    RESULT: string, the rendered template
    """
    t = Template(template)
    return t.render(config)


def read_manifest(toml_str: str) -> dict:
    """
    Read a TOML manifest from a string.
    - toml_str: the TOML string
    RESULT: dict(str, any)
    """
    return tomllib.loads(toml_str)
