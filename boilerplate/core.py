import tomllib
from pathlib import Path
import shutil

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
    RESULT: {
        "static":[{"from": "path", "to": "path"},...],
        "template":[{"from": "path", "to": "path"},...],
    }
    """
    return tomllib.loads(toml_str)


def process_files(src_dir: Path, tgt_dir: Path, file_paths: [], config: None|dict, dry_run: bool, result: []):
    """
    Process files from src directory to target directory.
    - src_dir: the source directory
    - tgt_dir: the target directory
    - file_paths: [{"from": "path", "to": "path"},...]
    - config: None or a dict, if a dict, try to render file as a template; else copy
    - dry_run: bool. If true, treat as a dry-run
    - result: [str], keeps a list of which actions were taken
    """
    for f in file_paths:
        from_path = src_dir / f["from"]
        to_path = tgt_dir / f["to"]
        prefix = None
        if not dry_run:
            if config is None:
                if not to_path.exists() or from_path.stat().st_mtime > to_path.stat().st_mtime:
                    shutil.copyfile(from_path, to_path)
                    prefix = "COPY              : "
                else:
                    prefix = "UP-TO-DATE(copy)  : "
            else:
                template = None
                with open(from_path, 'r') as fid:
                    template = fid.read()
                out = render(template, config)
                with open(to_path, 'w') as fid:
                    fid.write(out)
                prefix = "RENDER            : "
        elif config is None:
            prefix = "DRY-RUN(copy)     : "
        else:
            prefix = "DRY-RUN(render)   : "
        result.append(f"{prefix}{f['from']} => {f['to']}")


def generate(source: str, target: str, manifest: dict, config: dict, dry_run: bool) -> []:
    """
    Generate (or regenerate) the manifest files in repo_dir at target.
    - source: path to repo directory
    - target: path to target directory
    - manifest: dict, see read_manifest for data format
    - config: dict, the configuration of template parameters
    - dry_run: bool, if True, doesn't actually do the actions
    RETURN: array of str indicating what was done
    """
    src_dir = Path(source)
    tgt_dir = Path(target)
    if not dry_run:
        # confirm repo_dir exists
        # check if target dir exists, creating if necessary (mkdir -p)
        pass
    result = []
    process_files(src_dir, tgt_dir, manifest["static"], config = None, dry_run = dry_run, result = result)
    process_files(src_dir, tgt_dir, manifest["template"], config = config, dry_run = dry_run, result = result)
    return result
