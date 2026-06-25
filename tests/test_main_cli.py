"""CLI tests for atheneum_forge.main_cli.

These lock in the exit codes for each failure path of the `init` and `generate`
commands, covering the independently-scoped error handling in
`initialize_configuration`. Constructing a generator only creates/validates the
config file (no subprocess), and `--no-generate` returns before any git work, so
these tests are hermetic and do not invoke git.
"""

from typer.testing import CliRunner

from atheneum_forge import main_cli, project_factory
from atheneum_forge.main_cli import app

runner = CliRunner()


def _init_args(tmp_path, *extra):
    return ["init", str(tmp_path), "demo", "--type", "cpp", *extra]


# --- init: deliberate control flow (type not specified) ---------------------


def test_init_without_type_exits_1(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path), "demo"])  # type defaults to none
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)  # clean Exit, not a leaked error


# --- init: successful configuration creation --------------------------------


def test_init_creates_config_and_succeeds(tmp_path):
    result = runner.invoke(app, _init_args(tmp_path, "--no-generate"))
    assert result.exit_code == 0
    assert (tmp_path / "forge.toml").exists()


# --- init step 1: generator construction failures ---------------------------


def test_init_existing_config_without_force_exits_1(tmp_path):
    assert runner.invoke(app, _init_args(tmp_path, "--no-generate")).exit_code == 0
    result = runner.invoke(app, _init_args(tmp_path, "--no-generate"))  # config now exists, no --force
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)  # RuntimeError was caught and converted


def test_init_existing_config_with_force_succeeds(tmp_path):
    assert runner.invoke(app, _init_args(tmp_path, "--no-generate")).exit_code == 0
    result = runner.invoke(app, _init_args(tmp_path, "--no-generate", "--force"))
    assert result.exit_code == 0


def test_init_construction_filenotfound_exits_1(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise FileNotFoundError("missing source directory")

    monkeypatch.setattr(project_factory, "GeneratedCPP", explode)
    result = runner.invoke(app, _init_args(tmp_path, "--no-generate"))
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)


# --- init step 2: generation failure ----------------------------------------


def test_init_generation_filenotfound_exits_1(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise FileNotFoundError("project directory does not exist")

    monkeypatch.setattr(main_cli, "generate_project_files", explode)
    result = runner.invoke(app, _init_args(tmp_path))  # generate is on by default
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)


# --- generate: unknown project type -----------------------------------------


def test_generate_unknown_project_type_exits_1(tmp_path):
    result = runner.invoke(app, ["generate", str(tmp_path)])  # no forge.toml -> type none
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
