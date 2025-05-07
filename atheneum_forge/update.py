import filecmp
import importlib
import logging
import shutil
from io import StringIO
from pathlib import Path
from typing import Callable

console_log = logging.getLogger("rich")

MergeFunction = Callable[[Path, Path], StringIO]


def dict_merge(source_file: Path, destination_file: Path) -> StringIO:
    """
    Add keys and subdictionaries from source to destination if destination doesn't contain those
    keys. Otherwise, leave values alone.
    """
    source_dict, extension = _load_dict(source_file)
    destination_dict, _ = _load_dict(destination_file)
    _update_destination_dict(source_dict, destination_dict)
    return _dump_str(extension, destination_dict)


def _update_destination_dict(source: dict, destination: dict) -> None:
    if not destination:
        destination.update(source)
    if not source == destination:
        if isinstance(source, dict) and isinstance(destination, dict):
            replacement_keys = sorted(list(source.keys()))
            existing_keys = sorted(list(destination.keys()))
            for k in replacement_keys:
                if k not in existing_keys:
                    destination[k] = source[k]  # If the key doesn't exist, insert the subdict associated with the key
                elif isinstance(source[k], list) and isinstance(destination[k], list):
                    destination[k] = sorted(list(set(destination[k] + source[k])))
                elif isinstance(source[k], str) and isinstance(destination[k], str):
                    pass  # TODO: Leave strings alone, assuming generated project has ground truth?
                else:
                    # Repeat comparison one level down until the values are no longer dictionaries
                    _update_destination_dict(source[k], destination[k])


def text_merge(source_file: Path, destination_file: Path) -> StringIO:
    """
    Compare two text files line-by-line. Leave all lines in the existing file that do not
    appear in the replacement, but add lines from the replacement that do not appear in the
    existing.
    """
    if filecmp.cmp(destination_file, source_file):
        return StringIO()
    with open(destination_file, "r") as existing:
        with open(source_file, "r") as replacement:
            existing_lines = existing.readlines()
            replacement_lines = replacement.readlines()
            _update_destination_text_list(replacement_lines, existing_lines)
    with StringIO() as output:
        output.writelines(existing_lines)
        return output


def _update_destination_text_list(replacement_lines, existing_lines):
    insert_index = 0
    for line_index, line in enumerate(replacement_lines):
        if line not in existing_lines:
            existing_lines.insert(insert_index, line)
            insert_index += 1
        else:
            insert_index = existing_lines.index(line) + 1


def _load_dict(source_file: Path) -> tuple[dict, str]:  # noqa: PLR0911 too-many-return-statements
    suffixes = source_file.suffixes
    if ".json" in suffixes:
        try:
            module = importlib.import_module("json")
            with open(source_file, "r", encoding="utf-8") as input_file:
                return module.load(input_file), "json"
        except Exception:
            return {}, "json"
    elif ".yaml" in suffixes or ".yml" in suffixes:
        try:
            module = importlib.import_module("yaml")
            yamlcore = importlib.import_module("yamlcore")
            with open(source_file, "r", encoding="utf-8") as input_file:
                return module.load(input_file, Loader=yamlcore.CoreLoader), "yaml"
        except module.scanner.ScannerError:
            return {}, "yaml"
    elif ".toml" in suffixes:
        try:
            module = importlib.import_module("toml")
            with open(source_file, "r", encoding="utf-8") as input_file:
                return module.load(input_file), "toml"
        except Exception:
            return {}, "toml"
    else:
        return {}, ""


def _dump_str(extension: str, data: dict) -> StringIO:
    match extension:
        case "json":
            module = importlib.import_module("json")
            return StringIO(module.dumps(data))
        case "yaml" | "yml":
            module = importlib.import_module("yaml")
            return StringIO(module.dump(data, default_flow_style=False, sort_keys=False))
        case "toml":
            module = importlib.import_module("toml")
            return StringIO(module.dump(data))
        case _:
            return StringIO("")


strategies: dict[str, MergeFunction] = {"dict": dict_merge, "text": text_merge}


def update_single_file(strategy_name: str, source_file: Path, destination_file: Path) -> StringIO:
    """The context function that calls a dict or string strategy to update files."""
    return strategies[strategy_name](source_file, destination_file)


def write_precursors_and_updated_file(
    strategy_name: str, from_path: Path, to_path: Path, from_contents: str = ""
) -> None:
    """_summary_

    Args:
        strategy_name (str): _description_
        from_path (Path): _description_
        to_path (Path): _description_
        from_contents (str, optional): New contents as a rendered string. Defaults to "".
    """
    ours = to_path.with_name(to_path.name + ".ours")
    theirs = to_path.with_name(to_path.name + ".theirs")

    shutil.copyfile(to_path, ours)  # Make a copy of the destination before merging

    # Save the source (rendered string or file) as a file before merging
    if not from_contents:
        shutil.copyfile(from_path, theirs)
    else:
        with open(theirs, "w") as their_render:
            their_render.write(from_contents)

    buffer = update_single_file(strategy_name, theirs, ours)
    with open(to_path, "w") as updated_file:
        buffer.seek(0)
        shutil.copyfileobj(buffer, updated_file)
