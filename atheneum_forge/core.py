import filecmp
import logging
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePath
from typing import Any, List

import tomli_w
import tomllib
from jinja2 import Template

log = logging.getLogger("rich")

RECOGNIZED_CONFIG_KEYS = {"deps"}
RECOGNIZED_SRC_DIRS = {"src", "include", "test", "app"}
DEFAULT_LINE_COMMENTS_BY_EXT = {
    "*.cpp": "// ",
    "*.cpp.in": "// ",
    "*.h": "// ",
    "*.h.in": "// ",
    "*.c": "// ",
    "CMakeLists.txt": "# ",
    "*.py": "# ",
}


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


def process_single_file(  # noqa: PLR0912
    from_path: Path,
    to_path: Path,
    config: dict | None,
    onetime: bool,
    dry_run: bool,
) -> str:
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
    prefix = None
    if onetime and to_path.exists():
        prefix = "SKIPPED (one-time): "
        return f"{prefix}{from_path} => {to_path}"
    if not dry_run:
        if not from_path.exists():
            prefix = "SKIPPED (no source file): "
        elif config is None:
            if not to_path.exists() or not filecmp.cmp(from_path, to_path):
                if not to_path.parent.exists():
                    to_path.parent.mkdir(parents=True)
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
            if to_path.exists():
                with open(to_path, "r") as existing:
                    if existing.read() == out:
                        prefix = "UP-TO-DATE        : "
                    else:
                        with open(to_path, "w") as fid:
                            fid.write(out)
                        prefix = "RENDER            : "
            else:
                with open(to_path, "w") as fid:
                    fid.write(out)
                prefix = "RENDER            : "
    elif config is None:
        prefix = "DRY-RUN(copy)     : "
    else:
        prefix = "DRY-RUN(render)   : "
    return f"{prefix}{from_path} => {to_path}"


def process_files(
    src_dir: Path, tgt_dir: Path, file_paths: list, config: None | dict, dry_run: bool, status_list: List[str]
) -> None:
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
    for f in file_paths:
        onetime = f.get("onetime", False)
        test_param = f.get("if", None)
        if config is not None and test_param in config:
            if not config[test_param]:
                log.info(f"SKIPPING    : {f['from']}, skip flag is true")
                continue
        to_path_with_glob = build_path(tgt_dir, f["to"])
        if to_path_with_glob["glob"] is not None:
            log.error("Glob not allowed in 'to' path. Path must be directory or file.")
            log.error(f"... 'to' path  : {to_path_with_glob['path']}")
            log.error(f"... 'glob' path: {to_path_with_glob['glob']}")
            sys.exit(1)
        to_path = to_path_with_glob["path"]
        if to_path.is_dir():
            to_path.mkdir(parents=True, exist_ok=True)
        else:
            to_path.parent.mkdir(parents=True, exist_ok=True)
        from_path_with_glob = build_path(src_dir, f["from"])
        if from_path_with_glob["glob"] is None:
            from_path = from_path_with_glob["path"]
            result = process_single_file(
                from_path, to_path / (f.get("oname") if "oname" in f else from_path.name), config, onetime, dry_run
            )
            status_list.append(result)
        else:
            if not to_path.exists():
                to_path.mkdir(parents=True, exist_ok=True)
            from_path = from_path_with_glob["path"]
            glob = from_path_with_glob["glob"]
            for fpath in from_path.glob(glob):
                if fpath.is_dir():
                    continue
                result = process_single_file(fpath, to_path / fpath.name, config, onetime, dry_run)
                status_list.append(result)


def generate(source: str, target: str, manifest: dict, config: dict, dry_run: bool) -> list:
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
    result: List[str] = []
    if not dry_run:
        if not src_dir.exists():
            log.error(f"Source directory does not exist: {src_dir}")
            return result
        if not tgt_dir.exists():
            tgt_dir.mkdir(parents=True, exist_ok=True)
    process_files(src_dir, tgt_dir, manifest["static"], config=None, dry_run=dry_run, status_list=result)
    process_files(src_dir, tgt_dir, manifest["template"], config=config, dry_run=dry_run, status_list=result)
    return result


def derive_default_parameter(defaults: dict, key: str, all_files: set | None = None) -> Any:
    """
    Derive default parameters, running any computations.
    - defaults: dict(str, {"default": any}), the dictionary of default parameters
    - key: str, the key to fetch
    - all_files: set(str) | None, maps a relative dir path to files in that dir
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
        matched = []
        for file_path in all_files:
            if PurePath(file_path).match(d):
                matched.append(
                    {
                        "path": file_path,
                        "name": str(PurePath(file_path).name),
                        "code_path": re.sub("^include/", "", file_path),
                    }
                )
        d = sorted(matched, key=lambda m: m["path"])
    return d


def create_config_toml(manifest: dict, all_files: set | None = None) -> str:
    """
    Create config TOML data from the given manifest.
    """
    params = manifest["parameters"] if "parameters" in manifest else {}
    required = []
    defaults = []
    for p in sorted(params.keys()):
        is_private = params[p].get("private", False)
        if is_private:
            continue
        if "default" in params[p]:
            d = derive_default_parameter(params, p, all_files)
            value_str = tomli_w.dumps({p: d}).strip()
            defaults.append(f"# {value_str}")
        else:
            required.append(f"{p} = # <-- {params[p]['type']}")
    all = required + defaults
    dependencies = manifest.get("deps", [])
    dep_strings = []
    if dependencies and dependencies[0]:
        deps = sorted(dependencies, key=lambda d: d["name"])
        for dep in deps:
            dep_strings.append("[[deps]]")
            dep_strings.append(f'name = "{dep["name"]}"')
            dep_strings.append(f'git_url = "{dep["git_url"]}"')
            dep_strings.append(f'git_checkout = "{dep["git_checkout"]}"')
            if "add_to_cmake" in dep and dep["add_to_cmake"]:
                dep_strings.append("add_to_cmake = true")
            else:
                dep_strings.append("add_to_cmake = false")
            if "link_library_spec" in dep and len(dep["link_library_spec"]) > 0:
                dep_strings.append(f'link_library_spec = "{dep["link_library_spec"]}"')
    dep_strings.append(
        """
# [[deps]]
# name = "" # <- name of the dependency; vendor/<name>
# git_url = "" # <- add the url used to checkout this repository
# git_checkout = "" # <- add the branch, sha, or tag to check out
# add_to_cmake = true # <- if true, add to CMakeLists.txt files
# link_library_spec = "" # <- how library should appear in target_link_library(.); if blank, use project name
    """.strip()
    )
    postfix = "\n".join(dep_strings)
    return "\n".join(all) + "\n" + postfix


def merge_defaults_into_config(config: dict, defaults: dict, all_files: set | None = None) -> dict:  # noqa: PLR0912
    """
    Collect all available configuration parameters and their correct values.
    """
    result = {}
    # For every attribute in the user-supplied configuration, check that the attribute is
    # 1. available in the manifest and
    # 2. of the type indicated by the manifest
    for p in config.keys():  # noqa: PLC0206
        if p not in defaults:
            if p not in RECOGNIZED_CONFIG_KEYS:
                log.warn(f"Unrecognized key '{p}' in config")
            else:
                ...
        else:
            data_type = defaults[p].get("type", None)
            v = config[p]
            result[p] = v
            if isinstance(data_type, str):
                type_error = (
                    f"Type mismatch in attribute {p}"
                    f"\n... expected type: {{ data_type }}"
                    f"\n... actual value : {{ repr(v) }}"
                )
                if data_type.startswith("str") and not isinstance(v, str):
                    raise TypeError(type_error)
                if data_type.startswith("int") and not isinstance(v, int):
                    raise TypeError(type_error)
                if data_type.startswith("enum"):
                    if not isinstance(v, str):
                        raise TypeError(type_error)
                    options = defaults[p].get("options", [])
                    if v not in options:
                        raise TypeError("Enum error; {v} not in {options}")
    # For every attribute in the manifest, if it isn't called out in the user-supplied
    # config, populate its value with a correct default.
    for k, v in defaults.items():
        if k not in config:
            if "default" not in v:
                raise TypeError(f"Missing required config parameter '{p}'")
            result[k] = derive_default_parameter(defaults, k, all_files)
    return result


def read_config(config_toml: str, parameters: dict, all_files: set | None = None) -> dict:
    """
    Read the config toml and mix in defaults from manifest's parameters section.
    RETURN: config dict and flag: True if all processes executed OK, else False.
    """
    try:
        config = tomllib.loads(config_toml)
    except tomllib.TOMLDecodeError as err:
        log.error("Incorrect configuration file detected. Please check for invalid key-value pairs.")
        raise RuntimeError(err)
    return merge_defaults_into_config(config, parameters, all_files)


def list_all_files(dir_path: Path) -> set:
    """
    List all files relative to a dir_path using relative path strings.
    """
    result = set()
    for item in dir_path.glob("**/*"):
        candidate = str(item.relative_to(dir_path))
        is_src = False
        for dir_name in RECOGNIZED_SRC_DIRS:
            if candidate.startswith(dir_name):
                is_src = True
                break
        if not is_src:
            continue
        result.add(str(item.relative_to(dir_path)))
    return result


def setup_vendor(config: dict, tgt_dir: Path, dry_run: bool = False) -> list:
    """
    Return the list of commands necessary to set up vendor directory.
    - config: dict, must contain the key "deps" which is a list:
        [{"name": "dep_name", "git_url": "", "git_checkout": "branch/sha/tag name"}, ...]
    - tgt_dir: Path to directory where setup should occur. (root path)
    - dry_run: bool, if True doesn't touch the file system.
    RETURN: list of commands where a command is {"dir": Path, "cmds": list(str)}
    """
    cmds = []
    for dep in sorted(config.get("deps", []), key=lambda d: d["name"]):
        dep_name = dep["name"]
        tgt_dep = tgt_dir / "vendor" / dep_name
        if dry_run or not tgt_dep.exists():
            cmd = f"git submodule add {dep['git_url']} vendor/{dep_name}"
            cmds.append(cmd)
            cmd = " && ".join(
                [
                    f"cd vendor/{dep_name}",
                    "git fetch",
                    f"git checkout {dep['git_checkout']}",
                    "cd ../..",
                ]
            )
            cmds.append(cmd)
    if len(cmds) == 0:
        return []
    return [{"dir": tgt_dir, "cmds": cmds}]


def init_git_repo(tgt_dir: Path | str) -> list:
    """
    Return the list of commands required to initialize a git repo.
    RETURN: list of commands. See setup_vendor for structure.
    """
    return [
        {
            "dir": Path(tgt_dir),
            "cmds": [
                "git init --initial-branch=main",
            ],
        }
    ]


def run_commands(cmds: list) -> bool:
    """
    Run a list of commands.
    A command is documented as for setup_vendor.
    RETURN: True if all commands ran OK. Else false.
    """
    for c in cmds:
        for cmd in c["cmds"]:
            if not c["dir"].exists():
                c["dir"].mkdir(parents=True)
            result = subprocess.run(cmd, cwd=c["dir"], shell=True, check=False)
            if result.returncode != 0:
                log.error(f"Error running '{cmd}'.")
                return False
    return True


def gen_copyright(config: dict, copy_template: str, all_files: set) -> dict:
    """
    Generate copyright headers for the file tree.
    """
    copy = render(copy_template, config)
    copy_lines = copy.splitlines()
    result = {}
    for file_name in all_files:
        for match_str, prefix in DEFAULT_LINE_COMMENTS_BY_EXT.items():
            if PurePath(file_name).match(match_str):
                result[file_name] = list(map(lambda line: prefix + line, copy_lines))
    return result


def update_copyright(file_content: str, copy_lines: list) -> str:
    """
    Update copyright for a file as lines, returning (possibly updated) content.
    If the copy in the first N number of lines of file_content match the
    copy lines substantially, then overwrite. Else, prepend.
    """
    file_lines = file_content.splitlines()
    lines_match_substantially = True
    for line_idx, cline in enumerate(copy_lines):
        if line_idx < len(file_lines):
            line = file_lines[line_idx]
            if cline != line:
                copy_items = cline.split()
                existing_items = line.split()
                if len(copy_items) > 1 and len(existing_items) > 1:
                    if copy_items[1] != existing_items[1]:
                        lines_match_substantially = False
                        break
                    if copy_items[0] != existing_items[0]:
                        lines_match_substantially = False
                        break
                    continue
                if len(copy_items) > 0 and len(existing_items) > 0:
                    if copy_items[0] != existing_items[0]:
                        lines_match_substantially = False
                        break
                    continue
                lines_match_substantially = False
                break
    new_lines = []
    new_lines.extend(copy_lines)
    if lines_match_substantially:
        new_lines.extend(file_lines[len(copy_lines) :])
    else:
        new_lines.extend(file_lines)
    return "\n".join(new_lines)
