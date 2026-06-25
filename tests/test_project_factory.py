"""Unit tests for atheneum_forge.project_factory internals.

These exercise methods that previously had no coverage: the git-detection
comparison, the config-editing routine, and the file-processing engine.
Instances are built with ``__new__`` to bypass the filesystem-heavy ``__init__``
and set only the attributes each method actually touches.
"""

import os
from subprocess import CalledProcessError

from jinja2 import Environment, FileSystemLoader

from atheneum_forge import core
from atheneum_forge.project_factory import GeneratedCPP


def _bare_cpp(tmp_path, environment=None):
    """Build a GeneratedCPP without running __init__ (no template/config setup)."""
    project = GeneratedCPP.__new__(GeneratedCPP)
    project.target_dir = tmp_path
    project.environment = environment
    project.do_not_update = set()
    project.manifest = {}
    return project


# ---------------------------------------------------------------------------
# _is_git_repo (high-priority gap #3)
#
# run_commands is faked so the comparison logic is tested deterministically
# across platforms; the previous code compared raw stdout (trailing newline,
# git's forward slashes) against os.getcwd() and so was effectively always False.
# ---------------------------------------------------------------------------


def test_is_git_repo_true_ignores_trailing_newline(tmp_path, monkeypatch):
    project = _bare_cpp(tmp_path)
    # git appends a newline; the method must still match the current directory.
    monkeypatch.setattr(core, "run_commands", lambda commands: [os.getcwd() + "\n"])
    assert project._is_git_repo() is True


def test_is_git_repo_false_when_toplevel_differs(tmp_path, monkeypatch):
    project = _bare_cpp(tmp_path)
    monkeypatch.setattr(core, "run_commands", lambda commands: [os.path.join(os.getcwd(), "nested") + "\n"])
    assert project._is_git_repo() is False


def test_is_git_repo_false_on_called_process_error(tmp_path, monkeypatch):
    project = _bare_cpp(tmp_path)

    def explode(commands):
        raise CalledProcessError(128, "git rev-parse")

    monkeypatch.setattr(core, "run_commands", explode)
    assert project._is_git_repo() is False


# ---------------------------------------------------------------------------
# edit_forge_config (high-priority gap #4)
# ---------------------------------------------------------------------------


def _config_project(tmp_path, text, parameters):
    (tmp_path / "forge.toml").write_text(text, encoding="utf-8")
    project = _bare_cpp(tmp_path)
    project.manifest = {"template-parameters": parameters}
    return project, tmp_path / "forge.toml"


def test_edit_forge_config_updates_and_uncomments(tmp_path):
    project, config_file = _config_project(
        tmp_path,
        'project_name = "Demo"\n# start_year = 2026\n',
        {"project_name": {"type": "str"}, "start_year": {"type": "int"}},
    )
    project.edit_forge_config({"start_year": "2030"})
    contents = config_file.read_text(encoding="utf-8")
    assert 'start_year = "2030"' in contents
    assert "# start_year" not in contents  # the comment marker is removed
    assert 'project_name = "Demo"' in contents


def test_edit_forge_config_matches_parameter_exactly(tmp_path):
    # "version" must not also clobber "version_major" via a substring match.
    project, config_file = _config_project(
        tmp_path,
        "version = 1\nversion_major = 0\n",
        {"version": {"type": "int"}, "version_major": {"type": "int"}},
    )
    project.edit_forge_config({"version": "9"})
    contents = config_file.read_text(encoding="utf-8")
    assert 'version = "9"' in contents
    assert "version_major = 0" in contents


def test_edit_forge_config_preserves_lines_when_no_valid_edits(tmp_path):
    # No valid edits used to drop every parameter line; they must be preserved.
    project, config_file = _config_project(
        tmp_path,
        'project_name = "Demo"\nversion = 1\nversion_major = 0\n',
        {"project_name": {"type": "str"}, "version": {"type": "int"}, "version_major": {"type": "int"}},
    )
    project.edit_forge_config({"not_a_real_parameter": "x"})
    contents = config_file.read_text(encoding="utf-8")
    assert 'project_name = "Demo"' in contents
    assert "version = 1" in contents
    assert "version_major = 0" in contents


def test_edit_forge_config_no_file_is_noop(tmp_path):
    # With no forge.toml present, the call logs and returns without raising or creating a file.
    project = _bare_cpp(tmp_path)
    project.manifest = {"template-parameters": {"start_year": {"type": "int"}}}
    project.edit_forge_config({"start_year": "2030"})
    assert not (tmp_path / "forge.toml").exists()


# ---------------------------------------------------------------------------
# _process_single_file (high-priority gap #5)
# ---------------------------------------------------------------------------


def test_process_single_file_copy(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "src.txt"
    source.write_text("hello", encoding="utf-8")
    dest = tmp_path / "out" / "dest.txt"  # parent does not exist yet
    status = project._process_single_file(source, dest, "", "text", None, onetime=False, dry_run=False)
    assert status.startswith("COPY")
    assert dest.read_text(encoding="utf-8") == "hello"


def test_process_single_file_skips_onetime_existing(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "src.txt"
    source.write_text("new", encoding="utf-8")
    dest = tmp_path / "dest.txt"
    dest.write_text("original", encoding="utf-8")
    status = project._process_single_file(source, dest, "", "text", None, onetime=True, dry_run=False)
    assert status.startswith("SKIPPED (one-time)")
    assert dest.read_text(encoding="utf-8") == "original"  # left untouched


def test_process_single_file_missing_source(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "does_not_exist.txt"
    dest = tmp_path / "dest.txt"
    status = project._process_single_file(source, dest, "", "text", None, onetime=False, dry_run=False)
    assert status.startswith("SKIPPED (no source file)")
    assert not dest.exists()


def test_process_single_file_make_dir(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "a_source_dir"
    source.mkdir()
    dest = tmp_path / "made_dir"
    status = project._process_single_file(source, dest, "", "text", None, onetime=False, dry_run=False)
    assert status.startswith("MAKE DIR")
    assert dest.is_dir()


def test_process_single_file_up_to_date(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "src.txt"
    source.write_text("same", encoding="utf-8")
    dest = tmp_path / "dest.txt"
    dest.write_text("same", encoding="utf-8")
    status = project._process_single_file(source, dest, "", "text", None, onetime=False, dry_run=False)
    assert status.startswith("UP-TO-DATE(file)")


def test_process_single_file_update_static_merges_and_writes_precursors(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "src.txt"
    source.write_text("line-a\nline-b\nline-c\n", encoding="utf-8")
    dest = tmp_path / "dest.txt"
    dest.write_text("line-a\nline-c\n", encoding="utf-8")
    status = project._process_single_file(source, dest, "", "text", None, onetime=False, dry_run=False)
    assert status.startswith("UPDATE")
    assert "line-b" in dest.read_text(encoding="utf-8")  # source-only line merged in
    # the merge leaves .ours/.theirs precursor files next to the destination
    assert (tmp_path / "dest.txt.ours").exists()
    assert (tmp_path / "dest.txt.theirs").exists()


def test_process_single_file_render_template(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "greeting.txt").write_text("Hello {{ name }}!", encoding="utf-8")
    environment = Environment(loader=FileSystemLoader(template_dir, encoding="utf-8"), keep_trailing_newline=True)
    project = _bare_cpp(tmp_path, environment=environment)
    source = template_dir / "greeting.txt"
    dest = tmp_path / "greeting.txt"
    status = project._process_single_file(
        source, dest, "// (C)\n", "text", {"name": "World"}, onetime=False, dry_run=False
    )
    assert status.startswith("RENDER")
    assert dest.read_text(encoding="utf-8") == "// (C)\nHello World!"


def test_process_single_file_dry_run_copy(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "src.txt"
    source.write_text("hello", encoding="utf-8")
    dest = tmp_path / "dest.txt"
    status = project._process_single_file(source, dest, "", "text", None, onetime=False, dry_run=True)
    assert status.startswith("DRY-RUN(copy)")
    assert not dest.exists()  # dry run touches nothing


def test_process_single_file_dry_run_render(tmp_path):
    project = _bare_cpp(tmp_path)
    source = tmp_path / "src.txt"
    dest = tmp_path / "dest.txt"
    status = project._process_single_file(source, dest, "", "text", {"name": "x"}, onetime=False, dry_run=True)
    assert status.startswith("DRY-RUN(render)")
    assert not dest.exists()
