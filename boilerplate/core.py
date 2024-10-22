import tomllib

from jinja2 import Template


def render(template: str, config: dict) -> str:
    """
    Render a template using the given data
    - template: string, Jinja2 template to render
    - config: dict(string, stringable), values to insert into template
    RESULT: string, the rendered template
    """
    t = Template(template)
    return t.render(config)


def read_manifest(toml_str: str) -> dict:
    return tomllib.loads(toml_str)
