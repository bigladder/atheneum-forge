from datetime import datetime
from pathlib import Path, PurePath

import bigladder_boilerplate.core as bp


def test_template():
    config = {
        "project_name": "Athenium",
    }
    template = """
cmake_minimum_required(VERSION 3.10) # required for gtest_discover_tests
project({{ project_name | lower }}) # Replace
    """
    actual = bp.render(template, config)
    expected = """
cmake_minimum_required(VERSION 3.10) # required for gtest_discover_tests
project(athenium) # Replace
    """
    assert actual == expected


def test_read_manifest():
    toml_str = """
static = [
  {from=".clang-format", to="."},
  {from=".gitignore", to="."},
]
template = [
  {from="CMakeLists.txt", to="."}
]
    """
    data = bp.read_manifest(toml_str)
    assert len(data) > 0
    assert "static" in data
    assert "template" in data
    for s in data["static"]:
        assert "from" in s
        assert "to" in s
    for s in data["template"]:
        assert "from" in s
        assert "to" in s


def test_generate_task():
    toml_str = """
static = [
  {from=".clang-format", to="."},
  {from=".gitignore", to="."},
]
template = [
  {from="CMakeLists.txt", to="."}
]
    """
    manifest = bp.read_manifest(toml_str)
    repo_dir = "./data"
    target = "../new_repo"
    config = {
        "project_name": "Athenium",
    }
    results, is_ok = bp.generate(repo_dir, target, manifest, config, dry_run=True)
    assert is_ok == True
    assert len(results) == 3


def test_create_config():
    toml_str = """
static = [
  {from=".clang-format", to="."},
  {from=".gitignore", to="."},
]
template = [
  {from="CMakeLists.txt", to="."},
  {from="LICENSE.txt", to="."},
]
[parameters]
project_name = {type="str"}
start_year = {type="int:year", default="parameter:year"}
year = {type="int:year", default="current_year()"}
version_major = {type="int:>=0", default=0}
version_minor = {type="int:>=0", default=1}
version_patch = {type="int:>=0", default=0}
use_app = {type="bool", default=false}
    """
    data = bp.read_manifest(toml_str)
    actual = bp.create_config_toml(data)
    expected = """
project_name = # <-- str
# start_year = 2024
# use_app = false
# version_major = 0
# version_minor = 1
# version_patch = 0
# year = 2024
# [dep.dep_name]
# git_url = "" # <- add the url used to checkout this repository
# git_checkout = "" <- add the branch, sha, or tag to check out
    """.strip()
    assert expected == actual


def test_merge_config_with_defaults():
    manifest_toml = """
[parameters]
project_name = {type="str"}
start_year = {type="int:year", default="parameter:year"}
year = {type="int:year", default="current_year()"}
version_major = {type="int:>=0", default=0}
version_minor = {type="int:>=0", default=1}
version_patch = {type="int:>=0", default=0}
use_app = {type="bool", default=false}
    """
    manifest = bp.read_manifest(manifest_toml)
    config_toml = """
project_name = "bob"
start_year = 2022
# use_app = false
# version_major = 0
# version_minor = 1
# version_patch = 0
# year = 2024
    """
    actual, is_ok = bp.read_config(config_toml, manifest["parameters"])
    assert is_ok == True
    expected = {
        "project_name": "bob",
        "start_year": 2022,
        "use_app": False,
        "version_major": 0,
        "version_minor": 1,
        "version_patch": 0,
        "year": datetime.now().year,
    }
    assert actual == expected


def test_build_path():
    starting_dir = Path("/projects/example/data")
    path_str = "cmake/superstuff.cmake"
    actual = bp.build_path(starting_dir, path_str)
    expected = {
        "path": Path("/projects/example/data/cmake/superstuff.cmake"),
        "glob": None,
    }
    assert actual == expected


def test_build_path_2():
    starting_dir = Path("/projects/example/data")
    path_str = "cmake/*.cmake"
    actual = bp.build_path(starting_dir, path_str)
    expected = {
        "path": Path("/projects/example/data/cmake/"),
        "glob": "*.cmake",
    }
    assert actual == expected


def test_build_path_3():
    starting_dir = Path("/projects/example/data")
    path_str = "**/*.cpp"
    actual = bp.build_path(starting_dir, path_str)
    expected = {"path": Path("/projects/example/data"), "glob": "**/*.cpp"}
    assert actual == expected


def test_merge_defaults_into_config():
    config = {
        "project_name": "bob",
        "start_year": 2022,
    }
    defaults = {
        "project_name": {"type": "str"},
        "start_year": {
            "type": "int:year",
            "default": "parameter:year",
        },
        "year": {
            "type": "int:year",
            "default": "current_year()",
        },
        "version_major": {
            "type": "int:>=0",
            "default": 0,
        },
        "version_minor": {
            "type": "int:>=0",
            "default": 1,
        },
        "version_patch": {
            "type": "int:>=0",
            "default": 0,
        },
        "use_app": {
            "type": "bool",
            "default": False,
        },
    }
    actual, is_ok = bp.merge_defaults_into_config(config, defaults)
    assert is_ok == True
    expected = {
        "project_name": "bob",
        "start_year": 2022,
        "year": datetime.now().year,
        "version_major": 0,
        "version_minor": 1,
        "version_patch": 0,
        "use_app": False,
    }
    assert actual == expected


def test_derive_default_param():
    actual = bp.derive_default_parameter({}, "foo")
    expected = None
    assert actual == expected

    actual = bp.derive_default_parameter({"foo": {}}, "foo")
    expected = None
    assert actual == expected

    actual = bp.derive_default_parameter({"foo": {"default": "bar"}}, "foo")
    expected = "bar"
    assert actual == expected


def test_derive_default_parameter_with_src_tree():
    all_files = {
        "README.md",
        "src/a.cpp",
        "src/b.cpp",
        "src/c.cpp",
        "src/hidden.h",
        "app/abc.cpp",
        "include/abc/abc.h",
    }
    defaults = {
        "files_src": {
            "type": "str:glob",
            "default": "src/[a-zA-Z]*.cpp",
        },
        "headers_public": {
            "type": "str:glob",
            "default": "include/*/*.h",
        },
    }
    actual = bp.derive_default_parameter(defaults, "files_src", all_files)
    expected = {"src/a.cpp", "src/b.cpp", "src/c.cpp"}
    assert actual == expected

    actual = bp.derive_default_parameter(defaults, "headers_public", all_files)
    expected = {"include/abc/abc.h"}
    assert actual == expected


def test_init_git_repo():
    dir = "/Users/frodo-baggins/projects/test-project/"
    actual = bp.init_git_repo(dir)
    expected = [{
        "dir": PurePath(dir),
        "cmds": [
            "git init --initial-branch=main",
        ],
    }]
    assert expected == actual


def test_setup_vendor():
    dir = "/Users/frodo-baggins/projects/test-project/"
    tgt_dir = PurePath(dir)
    config = {}
    actual = bp.setup_vendor(config, tgt_dir, dry_run=True)
    expected = []
    assert actual == expected

    config = {
        "deps": {
            "CLI11": {
                "git_url": "https://github.com/CLIUtils/CLI11.git",
                "git_checkout": "master",
            },
            "courier": {
                "git_url": "https://github.com/bigladder/courier.git",
                "git_checkout": "main",
            },
            "toml11": {
                "git_url": "https://github.com/ToruNiina/toml11.git",
                "git_checkout": "1234567",
            },
        },
    }
    actual = bp.setup_vendor(config, tgt_dir, dry_run=True)
    expected = [
        {
            "dir": PurePath(dir),
            "cmds": [
                "git submodule add https://github.com/CLIUtils/CLI11.git vendor/CLI11",
                "cd vendor/CLI11 && git fetch && git checkout master && cd ../..",
                "git submodule add https://github.com/bigladder/courier.git vendor/courier",
                "cd vendor/courier && git fetch && git checkout main && cd ../..",
                "git submodule add https://github.com/ToruNiina/toml11.git vendor/toml11",
                "cd vendor/toml11 && git fetch && git checkout 1234567 && cd ../..",
            ],
        },
    ]
    assert len(actual) == len(expected)
    for idx in range(len(expected)):
        assert actual[idx]["dir"] == expected[idx]["dir"]
        assert len(actual[idx]["cmds"]) == len(expected[idx]["cmds"])
        for ca, ce in zip(actual[idx]["cmds"], expected[idx]["cmds"]):
            assert ca == ce
    assert actual == expected
