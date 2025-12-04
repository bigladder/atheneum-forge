import logging
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePath
from typing import Any

import tomli_w
import tomllib
from jinja2 import Environment, Template

log = logging.getLogger("rich")

UNDEFAULTED_PARAMETERS = {"project_name", "deps"}
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
LINE_COMMENTS_BY_EXT = defaultdict(lambda: "#", {".cpp": "//", ".h": "//", ".py": "#"})


def render(template: str, config: dict) -> str:
    """Render a template using the given data

    Args:
        template (str): Jinja2 template to render
        config (dict): values to insert into template

    Returns:
        str: the rendered template
    """
    t = Template(template)
    return t.render(config)


def read_manifest(toml_str: str) -> dict:
    """Read a TOML manifest from a string.

    Args:
        toml_str (str):

    Returns:
        dict: {
        "static":[{"from": "path", "to": "path"},...],
        "template":[{"from": "path", "to": "path"},...],
    }
    """
    return tomllib.loads(toml_str)


def build_path(starting_dir: Path, path_str: str) -> dict:
    """Build a new path from a starting_dir and path_str."""
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


@dataclass
class ProjectFile:
    from_path: Path
    to_path: Path
    onetime: bool
    add_copyright: bool


def collect_source_files(source_directory: Path, target_directory: Path, file_directives: list) -> list[ProjectFile]:
    """Collect project files and folders; process them through generation engine.

    Args:
        source_directory (Path):
        tgt_dir (Path):
        file_paths (list): [{"from": "path", "to": "path"},...]
        config (None | dict): if a dict, try to render file as a template; else copy
        dry_run (bool): If true, treat as a dry-run
        status_list (List[str]): keeps a list of which actions were taken
    """
    project_files: list[ProjectFile] = []

    for f in file_directives:
        onetime = f.get("onetime", False)
        add_copyright = f.get("add_copyright", False)

        to_path_with_glob = build_path(target_directory, f["to"])
        if to_path_with_glob["glob"] is not None:  # TODO: Errors in the manifest shouldn't read out to the user!
            log.error("Glob not allowed in 'to' path. Path must be directory or file.")
            log.error(f"... 'to' path  : {to_path_with_glob['path']}")
            log.error(f"... 'glob' path: {to_path_with_glob['glob']}")
            raise FileNotFoundError
        to_path = to_path_with_glob["path"]
        if to_path.is_dir():
            to_path.mkdir(parents=True, exist_ok=True)
        else:
            to_path.parent.mkdir(parents=True, exist_ok=True)

        from_path_with_glob = build_path(source_directory, f["from"])
        from_path = from_path_with_glob["path"]
        if from_path_with_glob["glob"] is None:
            if from_path.is_dir():
                # Directory name (no name -> source dir) in the "from" field is unused;
                # "to" path will be resolved/created # TODO: What if to_path is "bad" / not a dir?
                to_name = to_path
            elif "oname" in f:
                # Single file output, new name
                to_name = to_path / f["oname"]
            else:
                # Single file output, same name
                to_name = to_path / from_path.name
            project_files.append(ProjectFile(from_path, to_name, onetime, add_copyright))
        else:
            if not to_path.exists():
                to_path.mkdir(parents=True, exist_ok=True)
            glob = from_path_with_glob["glob"]
            for fpath in from_path.glob(glob):
                if fpath.is_dir():
                    continue
                project_files.append(ProjectFile(fpath, to_path / fpath.name, onetime, add_copyright))
    return project_files


def derive_default_parameter(defaults: dict, key: str, all_files: set | None = None) -> Any:
    """Derive default parameters, running any computations.

    Args:
        defaults (dict): the dictionary of default parameters
        key (str): the key to fetch
        all_files (set | None, optional): maps a relative dir path to files in that dir
        - e.g., {".": ["README.md"], "src": ["main.cpp"], "test": ["test.cpp"]}
    Raises:
        TypeError:
        RuntimeError:

    Returns:
        Any: the processed default
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


def create_config_toml(manifest: dict, project_name: str, all_files: set | None = None) -> str:
    """Create config TOML data from the given manifest."""
    params = manifest.get("template-parameters", {})
    params["project_name"] = {type: "str", "required": True, "default": project_name}
    configuration_entries = []
    for p in sorted(params.keys()):
        is_private = params[p].get("private", False)
        if is_private:
            continue
        if "default" in params[p]:
            d = derive_default_parameter(params, p, all_files)
            value_str = tomli_w.dumps({p: d}).strip()
            if params[p].get("required", False):
                configuration_entries.append(f"{value_str}")
            else:
                configuration_entries.append(f"# {value_str}")
        else:
            configuration_entries.append(f"{p} = # <-- {params[p]['type']}")
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
    return "\n".join(configuration_entries) + "\n" + postfix + "\n"


def merge_defaults_into_config(config: dict, manifest_defaults: dict, target_files: set | None = None) -> dict:  # noqa: PLR0912
    """Collect all available configuration parameters and their correct values."""
    result = {}
    # For every attribute in the user-supplied configuration, check that the attribute is
    # 1. available in the manifest and
    # 2. of the type indicated by the manifest
    for p in config.keys():  # noqa: PLC0206
        if p not in manifest_defaults:
            if p not in UNDEFAULTED_PARAMETERS:
                log.warn(f"Unrecognized key '{p}' in config")
            else:
                result[p] = config[p]
        else:
            data_type = manifest_defaults[p].get("type", None)
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
                    options = manifest_defaults[p].get("options", [])
                    if v not in options:
                        raise TypeError("Enum error; {v} not in {options}")
    # For every attribute in the manifest, if it isn't called out in the user-supplied
    # config, populate its value with a correct default.
    for k, v in manifest_defaults.items():
        if k not in config:
            if "default" not in v:
                raise TypeError(f"Missing required config parameter '{p}'")
            result[k] = derive_default_parameter(manifest_defaults, k, target_files)
    return result


def read_toml(input_file: Path) -> dict:
    """Read and return a dictionary from toml file.

    Args:
        input_file (Path): Input .toml file path

    Raises:
        RuntimeError: Badly configured input file.
        FileNotFoundError: No input file.

    Returns:
        dict: Key-value pairs extracted from toml format.
    """
    if input_file.is_file():
        try:
            with open(input_file, "rb") as fid:
                output = tomllib.load(fid)
                return output
        except tomllib.TOMLDecodeError:
            log.error("Incorrect input file format detected. (Check for invalid key-value pairs.)")
            raise RuntimeError from None
    else:
        log.error(f"{input_file} does not exist.")
        raise FileNotFoundError(f"{input_file} does not exist.")


# def read_config(config: dict, parameters: dict, all_files: set | None = None) -> dict:
#     """Mix defaults from manifest's parameters section into the configuration toml data.

#     Args:
#         config (dict):
#         parameters (dict):
#         all_files (set | None, optional):

#     Returns:
#         dict: _description_
#     """
#     return merge_defaults_into_config(config, parameters, all_files)


def list_files_in(dir_path: Path) -> set:
    """List all files relative to a dir_path using relative path strings.

    Args:
        dir_path (Path): Input path
    Returns:
        set: A set of relative paths in string form
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


def setup_vendor(config: dict, target_directory: Path, dry_run: bool = False) -> list:
    """Return the list of commands necessary to set up vendor directory.

    Args:
        config (dict): must contain the key "deps" which is a list:
                       [{"name": "dep_name", "git_url": "", "git_checkout": "branch/sha/tag name"}, ...]
        tgt_dir (Path): Path to directory where setup should occur. (root path)
        dry_run (bool, optional): if True doesn't touch the file system.

    Returns:
        list: list of commands where a command is {"dir": Path, "cmds": list(str)}
    """
    cmds = []
    for dep in sorted(config.get("deps", []), key=lambda d: d["name"]):
        dep_name = dep["name"]
        tgt_dep = target_directory / "vendor" / dep_name
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
    return [{"dir": target_directory, "cmds": cmds}]


def init_git_repo(target_directory: Path | str) -> list:
    """
    Return the list of commands required to initialize a git repo. See setup_vendor for structure.
    """
    return [
        {
            "dir": Path(target_directory),
            "cmds": [
                "git init --initial-branch=main",
            ],
        }
    ]


def init_pre_commit(target_directory: Path | str, type: str) -> list:
    """
    Return the list of commands required to initialize the pre-commit tool.
    """
    if type == "cpp":
        return [
            {
                "dir": Path(target_directory),
                "cmds": [
                    "uvx pre-commit install",
                ],
            }
        ]
    elif type == "python":
        return [
            {
                "dir": Path(target_directory),
                "cmds": [
                    "uv run pre-commit install",  # uv run syncs the venv first, so pre-commit gets installed
                ],
            }
        ]
    return []


def run_commands(commands: list) -> None:
    """
    Run a list of commands.
    A command is documented as for setup_vendor.

    Raises:
        CalledProcessError: The subprocess had a nonzero return code.
    """
    for c in commands:
        for cmd in c["cmds"]:
            if not c["dir"].exists():
                c["dir"].mkdir(parents=True)
            log.info(cmd)
            result = subprocess.run(cmd, cwd=c["dir"], shell=True, check=False, capture_output=True, encoding="utf8")
            result.check_returncode()
            log.info(result.stdout)  # Only reached if success code (0) returned


def gen_copyright(config: dict, copy_template: str, all_files: set[Path]) -> dict:
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


def render_copyright_string(environment: Environment, config: dict, for_file: Path) -> str:
    """
    Generate copyright headers for the single file.
    """
    copyright_template_file = "copyright.j2"
    template = environment.get_template(copyright_template_file)
    config.update({"comment_characters": LINE_COMMENTS_BY_EXT[PurePath(for_file).suffix]})
    return template.render(config)


def prepend_copyright_to_copy(from_path, copyright_text):
    copyright_indicators = ["Copyright", "copyright", "(C)", "(c)", "©"]
    already_copyrighted = False
    try:
        with open(from_path, "r", encoding="utf-8") as from_file:
            # Allow copyright information from the first two lines
            head = [next(from_file) for _ in range(2)]
            for line in head:
                already_copyrighted = any(c in line for c in copyright_indicators)
                if already_copyrighted:
                    break
    except UnicodeDecodeError as u:
        raise RuntimeError(f"{u} in file {from_path}")
    with open(from_path, "r+", encoding="utf-8") as f:
        contents = f.read()
        f.seek(0)
        if not already_copyrighted:
            f.write(copyright_text)
        f.write(contents)


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
