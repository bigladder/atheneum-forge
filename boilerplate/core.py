from jinja2 import Template

def render(template, config):
    """
    Render a template using the given data
    - template: string, Jinja2 template to render    
    - config: dict(string, stringable), values to insert into template
    RESULT: string, the rendered template
    """
    t = Template(template)
    return t.render(config)
