from datetime import datetime
from pathlib import Path, PurePath
import re
import shutil
import sys
import tomli_w
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
    RESULT: {
        "static":[{"from": "path", "to": "path"},...],
        "template":[{"from": "path", "to": "path"},...],
    }
    """
    return tomllib.loads(toml_str)


def build_path(starting_dir: Path, path_str: str) -> dict:
    """
    Build a new path from a starting_dir and path_str.
    """
    result = starting_dir
    is_glob = False
    globs = []
    for piece in path_str.split("/"):
        if "*" in piece or is_glob:
            is_glob = True
        else:
            result = result / piece
        if is_glob:
            globs.append(piece)

    glob = "/".join(globs)
    return {"path": result, "glob": None if glob == "" else glob}


def process_single_file(
    from_path: Path,
    to_path: Path,
    config: dict | None,
    onetime: bool,
    dry_run: bool,
    result: [],
) -> bool:
    """
    Process a single file from from_path to to_path.
    - from_path: path to a file to reference from
    - to_path: path to a file to generate/update
    - config: dict of parameters or None. If a dict, treat from_path as template.
    - onetime: bool, if True do not regenerate if to_path exists
    - dry_run: bool, if True, do a dry run. Don't actually update/generate.
    - result: a list of result strings indicating the tasks run (or dry runned).
    RESULT: True if all successful, else False
    """
    is_ok = True
    prefix = None
    if onetime and to_path.exists():
        prefix = "SKIPPED (one-time): "
        result.append(f"{prefix}{from_path} => {to_path}")
        return True
    if not dry_run:
        if config is None:
            if (
                not to_path.exists()
                or from_path.stat().st_mtime > to_path.stat().st_mtime
            ):
                shutil.copyfile(from_path, to_path)
                prefix = "COPY              : "
            else:
                prefix = "UP-TO-DATE(copy)  : "
        else:
            template = None
            with open(from_path, "r") as fid:
                template = fid.read()
            out = render(template, config)
            if not to_path.parent.exists():
                to_path.parent.mkdir(parents=True, exist_ok=True)
            with open(to_path, "w") as fid:
                fid.write(out)
            prefix = "RENDER            : "
    elif config is None:
        prefix = "DRY-RUN(copy)     : "
    else:
        prefix = "DRY-RUN(render)   : "
    result.append(f"{prefix}{from_path} => {to_path}")
    return True


def process_files(
    src_dir: Path,
    tgt_dir: Path,
    file_paths: [],
    config: None | dict,
    dry_run: bool,
    result: [],
) -> bool:
    """
    Process files from src directory to target directory.
    - src_dir: the source directory
    - tgt_dir: the target directory
    - file_paths: [{"from": "path", "to": "path"},...]
    - config: None or a dict, if a dict, try to render file as a template; else copy
    - dry_run: bool. If true, treat as a dry-run
    - result: [str], keeps a list of which actions were taken
    RETURN: True if successful, False if error
    """
    is_ok = True
    for f in file_paths:
        if not is_ok:
            return False
        onetime = f.get("onetime", False)
        to_path_with_glob = build_path(tgt_dir, f["to"])
        if to_path_with_glob["glob"] is not None:
            print(
                "[ERROR] glob not allowed in 'to' path. Path must be directory or file."
            )
            print(f"... 'to' path  : {to_path_with_glob['path']}")
            print(f"... 'glob' path: {to_path_with_glob['glob']}")
            sys.exit(1)
        to_path = to_path_with_glob["path"]
        if to_path.is_dir():
            to_path.mkdir(parents=True, exist_ok=True)
        else:
            to_path.parent.mkdir(parents=True, exist_ok=True)
        from_path_with_glob = build_path(src_dir, f["from"])
        if from_path_with_glob["glob"] is None:
            from_path = from_path_with_glob["path"]
            is_ok = process_single_file(
                from_path, to_path / from_path.name, config, onetime, dry_run, result
            )
        else:
            if not to_path.exists():
                to_path.mkdir(parents=True, exist_ok=True)
            from_path = from_path_with_glob["path"]
            glob = from_path_with_glob["glob"]
            for fpath in from_path.glob(glob):
                is_ok = process_single_file(
                    fpath, to_path / fpath.name, config, onetime, dry_run, result
                )
                if not is_ok:
                    return False
    return is_ok


def generate(
    source: str, target: str, manifest: dict, config: dict, dry_run: bool
) -> ([], bool):
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
    result = []
    if not dry_run:
        if not src_dir.exists():
            print(f"[ERROR] source directory does not exist: {src_dir}")
            return (result, False)
        if not tgt_dir.exists():
            tgt_dir.mkdir(parents=True, exist_ok=True)
    is_ok = process_files(
        src_dir,
        tgt_dir,
        manifest["static"],
        config=None,
        dry_run=dry_run,
        result=result,
    )
    if not is_ok:
        print("[ERROR] Encountered error processing static files... stopping")
        return (result, False)
    is_ok = process_files(
        src_dir,
        tgt_dir,
        manifest["template"],
        config=config,
        dry_run=dry_run,
        result=result,
    )
    if not is_ok:
        print("[ERROR] Encountered error processing template files... stopping")
        return (result, False)
    return (result, True)


def derive_default_parameter(defaults: dict, key: str, all_files: set|None = None) -> any:
    """
    Derive default parameters, running any computations.
    - defaults: dict(str, {"default": any}), the dictionary of default parameters
    - key: str, the key to fetch
    - src_tree: dict(str, [str]), maps a relative dir path to files in that dir
        - e.g., {".": ["README.md"], "src": ["main.cpp"], "test": ["test.cpp"]}
    RESULT: any, the processed default
    """
    if key not in defaults:
        return None
    d = defaults[key].get("default", None)
    if isinstance(d, str):
        if d.startswith("parameter:"):
            d = defaults[re.sub("parameter:", "", d)]["default"]
        if d.endswith("()"):
            if d == "current_year()":
                d = datetime.now().year
    data_type = defaults[key].get("type", None)
    if data_type == "str:glob" and all_files is not None:
        matched = set()
        for file_path in all_files:
            if PurePath(file_path).match(d):
                matched.add(file_path)
        d = matched
    return d


def create_config_toml(manifest: dict, all_files: set|None = None) -> str:
    """
    Create config TOML data from the given manifest.
    """
    params = manifest["parameters"] if "parameters" in manifest else {}
    required = []
    defaults = []
    for p in sorted(params.keys()):
        if "default" in params[p]:
            d = derive_default_parameter(params, p, all_files)
            value_str = tomli_w.dumps({p: d}).strip()
            defaults.append(f"# {value_str}")
        else:
            required.append(f"{p} = # <-- {params[p]['type']}")
    all = required + defaults
    return "\n".join(all)


def merge_defaults_into_config(config: dict, defaults: dict, all_files: set|None = None) -> (dict, bool):
    """ """
    result = {}
    for p in config.keys():
        data_type = None
        if p not in defaults:
            print("[WARNING] unrecognized key '{p}' in config")
        else:
            date_type = defaults[p].get("type", None)
        v = config[p]
        result[p] = v
        if isinstance(data_type, str):
            if data_type.startswith("str"):
                if not isinstance(v, str):
                    print("[ERROR] type mismatch")
                    print(f"... expected type: {{ data_type }}")
                    print(f"... actual value : {{ repr(v) }}")
                    return result, False
            if data_type.startswith("int"):
                if not isinstance(v, int):
                    print("[ERROR] type mismatch")
                    print(f"... expected type: {{ data_type }}")
                    print(f"... actual value : {{ repr(v) }}")
                    return result, False
            if data_type.startswith("enum"):
                if not isinstance(v, str):
                    print("[ERROR] type mismatch")
                    print(f"... expected type: {{ data_type }}")
                    print(f"... actual value : {{ repr(v) }}")
                    return result, False
                options = defaults[p].get("options", [])
                if v not in options:
                    print("[ERROR] enum error; {v} not in {options}")
                    return result, False
    for p in defaults.keys():
        if p not in config:
            if "default" not in defaults[p]:
                print(f"[ERROR] missing required config parameter '{p}'")
                return result, False
            result[p] = derive_default_parameter(defaults, p, all_files)
    return result, True


def read_config(config_toml: str, parameters: dict, all_files: set|None = None) -> (dict, bool):
    """
    Read the config toml and mix in defaults from manifest's parameters section.
    RETURN: config dict and flag: True if all processes executed OK, else False.
    """
    config = tomllib.loads(config_toml)
    return merge_defaults_into_config(config, parameters, all_files)


def list_all_files(dir_path: Path) -> set:
    """
    List all files relative to a dir_path using relative path strings.
    """
    result = set()
    for item in dir_path.glob('**/*'):
        result.add(str(item.relative_to(dir_path)))
    return result
