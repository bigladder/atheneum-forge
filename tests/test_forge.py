"""Tests for atheneum_forge.forge.AtheneumForge.initialize_configuration.

These lock in the error behavior of the orchestration layer: construction and
generation failures propagate (the library re-raises so the caller can surface
them), while a git/submodule failure is logged but does not abort once the
project files already exist. Constructing a generator only creates/validates the
config file (no subprocess), so most tests are hermetic; the git-failure test
stubs generation and fakes run_commands to avoid touching git.
"""

from subprocess import CalledProcessError

import pytest

from atheneum_forge import core, project_factory
from atheneum_forge.forge import AtheneumForge

CPP = project_factory.ProjectType.cpp


# --- deliberate control flow ------------------------------------------------


def test_invalid_type_raises_runtimeerror(tmp_path):
    forge = AtheneumForge()
    with pytest.raises(RuntimeError):
        forge.initialize_configuration(tmp_path, "demo")  # type defaults to none


# --- step 1: generator construction -----------------------------------------


def test_config_only_init_creates_config(tmp_path):
    forge = AtheneumForge()
    forge.initialize_configuration(tmp_path, "demo", type=CPP, generate=False)
    assert (tmp_path / "forge.toml").exists()
    assert forge.generator is not None


def test_existing_config_without_force_raises(tmp_path):
    AtheneumForge().initialize_configuration(tmp_path, "demo", type=CPP, generate=False)
    with pytest.raises(RuntimeError):
        AtheneumForge().initialize_configuration(tmp_path, "demo", type=CPP, generate=False)


def test_existing_config_with_force_succeeds(tmp_path):
    AtheneumForge().initialize_configuration(tmp_path, "demo", type=CPP, generate=False)
    AtheneumForge().initialize_configuration(tmp_path, "demo", type=CPP, generate=False, force=True)
    assert (tmp_path / "forge.toml").exists()


def test_construction_filenotfound_propagates(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise FileNotFoundError("missing source directory")

    monkeypatch.setattr(project_factory, "GeneratedCPP", explode)
    with pytest.raises(FileNotFoundError):
        AtheneumForge().initialize_configuration(tmp_path, "demo", type=CPP, generate=False)


# --- step 2: generation -----------------------------------------------------


def test_generation_error_propagates(tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise FileNotFoundError("project directory does not exist")

    monkeypatch.setattr(AtheneumForge, "generate_project_files", explode)
    with pytest.raises(FileNotFoundError):
        AtheneumForge().initialize_configuration(tmp_path, "demo", type=CPP)  # generate is on by default


def test_git_failure_does_not_abort(tmp_path, monkeypatch):
    # Stub generation so the test focuses purely on the git-init step.
    monkeypatch.setattr(project_factory.GeneratedCPP, "generate", lambda self, project_path, dry_run=False: [])

    def explode(commands):
        raise CalledProcessError(1, "git")

    monkeypatch.setattr(core, "run_commands", explode)
    forge = AtheneumForge()
    # Should return normally despite the git failure; the config file is still produced.
    forge.initialize_configuration(tmp_path, "demo", type=CPP)
    assert (tmp_path / "forge.toml").exists()
