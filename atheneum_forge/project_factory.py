import logging
from abc import ABC, abstractmethod
from pathlib import Path

from . import core
from .main import DATA_DIR, FORGE_CONFIG

console_log = logging.getLogger("rich")


class GeneratedProject(ABC):
    def __init__(self, project_path: Path, project_name: str):
        """Set up project locations and data dictionaries"""
        self.target_dir = Path(project_path).resolve()
        self.target_dir.mkdir(parents=True, exist_ok=True)

        path_manifest = self.source_data_dir / "manifest.toml"  # type: ignore # Because this is an ABC, we control when __init__ is called.
        self.manifest = core.read_toml(path_manifest)

        configuration_file = self.target_dir / FORGE_CONFIG
        if not configuration_file.exists():
            config_str = core.create_config_toml(self.manifest, project_name)
            with open(configuration_file, "w") as fid:
                fid.write(config_str)

        self.target_files: set[Path] = core.list_all_files(self.target_dir)
        try:
            self.configuration = core.merge_defaults_into_config(
                core.read_toml(configuration_file), self.manifest["parameters"], self.target_files
            )
        except (TypeError, RuntimeError):
            raise RuntimeError("Error while processing config file.")

    def check_directories(self, project_path: Path) -> None:
        """_summary_

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

        self.target_files = core.list_all_files(self.target_dir)
        try:
            self.configuration = core.merge_defaults_into_config(
                core.read_toml(configuration_file), self.manifest["parameters"], self.target_files
            )
        except (TypeError, RuntimeError):
            raise RuntimeError("Error while processing config file.")

    @abstractmethod
    def update(self, project_path: Path) -> None:
        pass

    @abstractmethod
    def generate(self, project_path: Path, dry_run: bool) -> list[str]:
        pass


class GeneratedCPP(GeneratedProject):
    def __init__(self, project_path: Path, project_name: str):
        """_summary_"""
        self.source_data_dir = DATA_DIR / "cpp"
        if not self.source_data_dir.exists():
            raise FileNotFoundError(f"Cannot find atheneum_forge source directory {self.source_data_dir}.")

        super().__init__(project_path, project_name)

    def generate(self, project_path: Path, dry_run: bool = False) -> list[str]:
        """_summary_"""
        result: list[str] = []
        self.check_directories(project_path)
        core.process_files(
            self.source_data_dir,
            self.target_dir,
            self.manifest["static"],
            config=None,
            dry_run=dry_run,
            status_list=result,
        )
        core.process_files(
            self.source_data_dir,
            self.target_dir,
            self.manifest["template"],
            config=self.configuration,
            dry_run=dry_run,
            status_list=result,
        )
        return result


class GeneratedPython(GeneratedProject):
    def __init__(self, project_path: Path, project_name: str, force: bool):
        """_summary_

        Args:
            project_path (Path): _description_
            project_name (str): _description_

        """
        self.source_data_dir = DATA_DIR / "python"
        if not self.source_data_dir.exists():
            raise FileNotFoundError(f"Cannot find atheneum_forge source directory {self.source_data_dir}.")

        super().__init__(project_path, project_name)

    def generate(self, project_path: Path, dry_run: bool = False) -> list[str]:
        """_summary_"""
        result: list[str] = []
        self.check_directories(project_path)
        core.process_files(
            self.source_data_dir,
            self.target_dir,
            [{"from": "", "to": "self.configuration[project_name]"}],
            config=None,
            dry_run=dry_run,
            status_list=result,
        )
        core.process_files(
            self.source_data_dir,
            self.target_dir,
            self.manifest["static"],
            config=None,
            dry_run=dry_run,
            status_list=result,
        )
        core.process_files(
            self.source_data_dir,
            self.target_dir,
            self.manifest["template"],
            config=self.configuration,
            dry_run=dry_run,
            status_list=result,
        )
        return result

    def update(self, project_path: Path) -> None:
        pass
