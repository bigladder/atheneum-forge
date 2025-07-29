import filecmp
import logging
import shutil
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from subprocess import CalledProcessError

from . import core, update

THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = (THIS_DIR / "data").resolve()
FORGE_CONFIG = "forge.toml"


console_log = logging.getLogger("rich")


class ProjectType(str, Enum):
    none = "none"
    cpp = "cpp"
    python = "python"


class GeneratedProject(ABC):
    """_summary_

    Args:
        ABC (_type_): _description_

    Raises:
        RuntimeError: _description_
        FileNotFoundError: _description_
        FileNotFoundError: _description_
        FileNotFoundError: _description_
        RuntimeError: _description_
    """

    @staticmethod
    def get_project_type(project_path: Path) -> ProjectType:
        try:
            config_toml = core.read_toml(project_path / FORGE_CONFIG)
        except FileNotFoundError:
            return ProjectType.none
        project_type = config_toml["project_type"]
        for type in ProjectType:
            if type.value == project_type:
                return type
        return ProjectType.none

    @property
    @abstractmethod
    def source_data_dir(self) -> Path:
        """The source data has varied values, but common usage"""
        pass

    @source_data_dir.setter
    def source_data_dir(self, source_path: Path) -> None:
        self.source_data_dir = source_path

    def __init__(self, project_path: Path, project_name: str = "", force: bool = False):
        """Set up project locations and data dictionaries"""
        self.target_dir = Path(project_path).resolve()
        self.target_dir.mkdir(parents=True, exist_ok=True)

        path_manifest = self.source_data_dir / "manifest.toml"
        self.manifest = core.read_toml(path_manifest)
        self.do_not_update: set[Path] = set()

        configuration_file = self.target_dir / FORGE_CONFIG

        if not project_name:  # Assume configuration toml exists, find name there
            if not configuration_file.exists():
                raise FileNotFoundError(
                    f"No project name given and no existing configuration exists at path {project_path}"
                )
            else:
                self.configuration = core.read_toml(configuration_file)
                self.do_not_update = set(
                    [Path(self.target_dir, exclude_file) for exclude_file in self.configuration.get("skip", [])]
                )
        elif not configuration_file.exists() or force:  # Create or overwrite existing configuration
            config_str = core.create_config_toml(self.manifest, project_name)
            with open(configuration_file, "w") as fid:
                fid.write(config_str)

            target_files: set[Path] = core.list_files_in(self.target_dir)
            try:
                # Read the created file back into a member dictionary
                self.configuration = core.merge_defaults_into_config(
                    core.read_toml(configuration_file), self.manifest["template-parameters"], target_files
                )
            except (TypeError, RuntimeError, FileNotFoundError):
                raise RuntimeError("Error while processing config file.")
        else:
            console_log.info(f'{configuration_file}" already exists. Use [red]--force[/red] to overwrite.')
            raise RuntimeError()

    def _check_directories(self, project_path: Path) -> None:
        """Ensure that the target (project) directory and config file exist, then collect configuration information.

        Args:
            config_path (Path): _description_

        Raises:
            FileNotFoundError: _description_
            RuntimeError: _description_

        Returns:
            _type_: _description_
        """
        configuration_file = project_path / FORGE_CONFIG
        self.target_dir = configuration_file.parent

        if not self.target_dir.exists():
            raise FileNotFoundError("Project directory does not exist.")
        if not configuration_file.exists():
            raise FileNotFoundError(f'Config file "{configuration_file}" doesn\'t exist.')
        if not configuration_file.is_file():
            raise FileNotFoundError(f'Config "{configuration_file}" is not a file.')

    def _process_single_file(  # noqa: PLR0912
        self, from_path: Path, to_path: Path, strategy: str, config: dict | None, onetime: bool, dry_run: bool
    ) -> str:
        """Process a single file from from_path to to_path: copy, update, render, or skip.

        Args:
            from_path (Path): path to a file to reference from
            to_path (Path): path to a file to generate/update
            config (dict | None): dict of parameters or None. If a dict, treat from_path as template.
            onetime (bool): if True do not regenerate if to_path exists
            dry_run (bool): if True, do a dry run. Don't actually update/generate.

        Returns:
            str: One-line processing status of the file
        """
        print("_process_single_file:")
        prefix = None
        width = 20
        if onetime and to_path.exists():
            prefix = f"{'SKIPPED (one-time)':<{width}}: "
            return f"{prefix}{to_path}"
        if not dry_run:
            if not from_path.exists():
                prefix = f"{'SKIPPED (no source file)':<{width}}: "
            elif from_path.is_dir():
                if not to_path.exists():
                    # Only create directory; don't populate it
                    to_path.mkdir(parents=True)
                    prefix = f"{'MAKE DIR':<{width}}: "
                else:
                    prefix = f"{'UP-TO-DATE(dir)':<{width}}: "
            elif config is None:
                if not to_path.exists():
                    if not to_path.parent.exists():
                        to_path.parent.mkdir(parents=True)
                    shutil.copyfile(from_path, to_path)  # This is always a wholesale COPY, not update/merge.
                    prefix = f"{'COPY':<{width}}: "
                elif not filecmp.cmp(from_path, to_path):  # OUT OF DATE
                    update.write_precursors_and_updated_file(strategy, from_path, to_path)
                    prefix = f"{'UPDATE':<{width}}: "
                else:
                    prefix = f"{'UP-TO-DATE(file)':<{width}}: "
            else:  # If you give this function a config, it's because it contains template params
                template = None
                with open(from_path, "r") as fid:
                    template = fid.read()
                out = core.render(template, config)  # Render template using config
                if not to_path.parent.exists():
                    to_path.parent.mkdir(parents=True, exist_ok=True)
                if to_path.exists():
                    with open(to_path, "r") as existing:
                        if existing.read() == out:
                            prefix = f"{'UP-TO-DATE(file)':<{width}}: "
                        else:  # OUT OF DATE
                            update.write_precursors_and_updated_file(strategy, from_path, to_path, out)
                            prefix = f"{'UPDATE':<{width}}: "
                else:  # File didn't exist, create (render)
                    with open(to_path, "w") as fid:
                        fid.write(out)
                    prefix = f"{'RENDER':<{width}}: "
        elif config is None:
            prefix = f"{'DRY-RUN(copy)':<{width}}: "
        else:
            prefix = f"{'DRY-RUN(render)':<{width}}: "
        return f"{prefix}{to_path}"

    def _is_git_repo(self) -> bool:
        cmd = [
            {
                "dir": Path(self.target_dir),
                "cmds": [
                    "git rev-parse --show-toplevel",
                ],
            }
        ]

        try:
            core.run_commands(cmd)
            return True
        except CalledProcessError:
            return False

    def init_git_repo(self) -> list:
        """
        Return the list of commands required to initialize a git repo. See setup_vendor for structure.
        """
        return (
            [
                {
                    "dir": Path(self.target_dir),
                    "cmds": ["git init --initial-branch=main", "git add .", 'git commit -m "Initial commit"'],
                }
            ]
            if not self._is_git_repo()
            else []
        )

    @abstractmethod
    def init_pre_commit(self) -> list:
        """
        Return the list of commands required to initialize the pre-commit tool.
        """
        pass

    @abstractmethod
    def init_submodules(self) -> list:
        """Return the commands to initialize git submodules."""
        pass

    @abstractmethod
    def generate(self, project_path: Path, dry_run: bool) -> list[str]:
        pass


class GeneratedCPP(GeneratedProject):
    """Generator methods for cpp project"""

    @property
    def source_data_dir(self) -> Path:
        return DATA_DIR / "cpp"

    @source_data_dir.setter
    def source_data_dir(self, source_path: Path) -> None:
        self.source_data_dir = source_path

    def __init__(self, project_path: Path, project_name: str = "", force: bool = False):
        """_summary_"""
        if not self.source_data_dir.exists():
            raise FileNotFoundError(f"Cannot find atheneum_forge source directory {self.source_data_dir}.")

        super().__init__(project_path, project_name, force)

    def generate(self, project_path: Path, dry_run: bool = False) -> list[str]:
        """_summary_"""
        result: list[str] = []
        self._check_directories(project_path)
        for f in core.collect_source_files(self.source_data_dir, self.target_dir, self.manifest["template"]):
            if f.to_path.resolve() not in self.do_not_update:
                update_type = "txt"  # TODO: robustify default
                for file_type in f.from_path.suffixes:
                    if file_type.lstrip(".") in self.manifest["update-strategies"]:
                        update_type = self.manifest["update-strategies"][file_type.lstrip(".")]
                result.append(
                    self._process_single_file(
                        f.from_path, f.to_path, update_type, self.configuration, f.onetime, dry_run
                    )
                )
        for f in core.collect_source_files(self.source_data_dir, self.target_dir, self.manifest["static"]):
            print(f.from_path, f.to_path)
            if f.to_path.resolve() not in self.do_not_update:
                result.append(
                    self._process_single_file(
                        f.from_path,
                        f.to_path,
                        self.manifest["update-strategies"][f.from_path.suffix.lstrip(".")],
                        None,
                        f.onetime,
                        dry_run,
                    )
                )

        return result

    def init_pre_commit(self) -> list:
        """
        Return the list of commands required to initialize the pre-commit tool.
        """
        return [
            {
                "dir": Path(self.target_dir),
                "cmds": [
                    "uvx pre-commit install",
                ],
            }
        ]

    def init_submodules(self) -> list:
        """Return the commands to initialize git submodules."""
        return core.setup_vendor(self.configuration, self.source_data_dir.parent)


class GeneratedPython(GeneratedProject):
    @property
    def source_data_dir(self) -> Path:
        return DATA_DIR / "python"

    @source_data_dir.setter
    def source_data_dir(self, source_path: Path) -> None:
        self.source_data_dir = source_path

    def __init__(self, project_path: Path, project_name: str = "", force: bool = False):
        """_summary_

        Args:
            project_path (Path): _description_
            project_name (str): _description_

        """
        if not self.source_data_dir.exists():
            raise FileNotFoundError(f"Cannot find atheneum_forge source directory {self.source_data_dir}.")

        super().__init__(project_path, project_name, force)

    def generate(self, project_path: Path, dry_run: bool = False) -> list[str]:
        """_summary_"""
        result: list[str] = []
        self._check_directories(project_path)
        # Generate a package folder with the same name as the project
        for f in core.collect_source_files(
            self.source_data_dir, self.target_dir, [{"from": "", "to": f"{self.configuration['project_name']}"}]
        ):
            result.append(
                self._process_single_file(
                    f.from_path,
                    f.to_path,
                    self.manifest["update-strategies"][f.from_path.suffix.lstrip(".")],
                    None,
                    f.onetime,
                    dry_run,
                )
            )
        for f in core.collect_source_files(self.source_data_dir, self.target_dir, self.manifest["static"]):
            if f.to_path.resolve() not in self.do_not_update:
                result.append(
                    self._process_single_file(
                        f.from_path,
                        f.to_path,
                        self.manifest["update-strategies"][f.from_path.suffix.lstrip(".")],
                        None,
                        f.onetime,
                        dry_run,
                    )
                )
        for f in core.collect_source_files(self.source_data_dir, self.target_dir, self.manifest["template"]):
            if f.to_path.resolve() not in self.do_not_update:
                result.append(
                    self._process_single_file(
                        f.from_path,
                        f.to_path,
                        self.manifest["update-strategies"][f.from_path.suffix.lstrip(".")],
                        self.configuration,
                        f.onetime,
                        dry_run,
                    )
                )
        return result

    def init_pre_commit(self) -> list:
        """
        Return the list of commands required to initialize the pre-commit tool.
        """
        return [
            {
                "dir": Path(self.target_dir),
                "cmds": [
                    "uv run pre-commit install",  # uv run syncs the venv first, so pre-commit gets installed
                ],
            }
        ]

    def init_submodules(self) -> list:
        return []
