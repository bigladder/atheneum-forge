import os
from datetime import datetime
from pathlib import Path, PurePath

from jinja2 import Environment, FileSystemLoader

from atheneum_forge import core


def test_template():
    config = {
        "project_name": "Atheneum",
    }
    template = """
cmake_minimum_required(VERSION 3.10) # required for gtest_discover_tests
project({{ project_name | lower }}) # Replace
    """
    actual = core.render(template, config)
    expected = """
cmake_minimum_required(VERSION 3.10) # required for gtest_discover_tests
project(atheneum) # Replace
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
    data = core.read_manifest(toml_str)
    assert len(data) > 0
    assert "static" in data
    assert "template" in data
    for s in data["static"]:
        assert "from" in s
        assert "to" in s
    for s in data["template"]:
        assert "from" in s
        assert "to" in s


# def test_generate_task():
#     toml_str = """
# static = [
#   {from=".clang-format", to="."},
#   {from=".gitignore", to="."},
# ]
# template = [
#   {from="CMakeLists.txt", to="."}
# ]
#     """
#     manifest = af.read_manifest(toml_str)
#     repo_dir = "./data"
#     target = "../new_repo"
#     config = {
#         "project_name": "Atheneum",
#     }
#     results = af.generate("Atheneum", repo_dir, target, manifest, config, dry_run=True)
#     assert len(results) == 3  # noqa: PLR2004


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
[template-parameters]
project_name = {type="str"}
start_year = {type="int:year", default="current_year()"}
version_major = {type="int:>=0", default=0}
version_minor = {type="int:>=0", default=1}
version_patch = {type="int:>=0", default=0}
use_app = {type="bool", default=false}
    """
    data = core.read_manifest(toml_str)
    actual = core.create_config_toml(data, "Atheneum")
    expected = """
project_name = "Atheneum"
# start_year = 2025
# use_app = false
# version_major = 0
# version_minor = 1
# version_patch = 0
# [[deps]]
# name = "" # <- name of the dependency; vendor/<name>
# git_url = "" # <- add the url used to checkout this repository
# git_checkout = "" # <- add the branch, sha, or tag to check out
# add_to_cmake = true # <- if true, add to CMakeLists.txt files
# link_library_spec = "" # <- how library should appear in target_link_library(.); if blank, use project name
    """.strip()
    print(actual)
    assert expected == actual


# def test_merge_config_with_defaults():
#     manifest_toml = """
# [template-parameters]
# project_name = {type="str"}
# start_year = {type="int:year", default="parameter:year"}
# year = {type="int:year", default="current_year()"}
# version_major = {type="int:>=0", default=0}
# version_minor = {type="int:>=0", default=1}
# version_patch = {type="int:>=0", default=0}
# use_app = {type="bool", default=false}
#     """
#     manifest = af.read_manifest(manifest_toml)
#     config_toml = """
# project_name = "bob"
# start_year = 2022
# # use_app = false
# # version_major = 0
# # version_minor = 1
# # version_patch = 0
# # year = 2024
#     """
#     actual = af.read_config(tomllib.loads(config_toml), manifest["template-parameters"])
#     expected = {
#         "project_name": "bob",
#         "start_year": 2022,
#         "use_app": False,
#         "version_major": 0,
#         "version_minor": 1,
#         "version_patch": 0,
#         "year": datetime.now().year,
#     }
#     assert actual == expected


def test_build_path():
    starting_dir = Path("/projects/example/data")
    path_str = "cmake/superstuff.cmake"
    actual = core.build_path(starting_dir, path_str)
    expected = {
        "path": Path("/projects/example/data/cmake/superstuff.cmake"),
        "glob": None,
    }
    assert actual == expected


def test_build_path_2():
    starting_dir = Path("/projects/example/data")
    path_str = "cmake/*.cmake"
    actual = core.build_path(starting_dir, path_str)
    expected = {
        "path": Path("/projects/example/data/cmake/"),
        "glob": "*.cmake",
    }
    assert actual == expected


def test_build_path_3():
    starting_dir = Path("/projects/example/data")
    path_str = "**/*.cpp"
    actual = core.build_path(starting_dir, path_str)
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
    actual = core.merge_defaults_into_config(config, defaults)
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
    actual = core.derive_default_parameter({}, "foo")
    expected = None
    assert actual == expected

    actual = core.derive_default_parameter({"foo": {}}, "foo")
    expected = None
    assert actual == expected

    actual = core.derive_default_parameter({"foo": {"default": "bar"}}, "foo")
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
    actual = core.derive_default_parameter(defaults, "files_src", all_files)
    expected = [
        {"path": "src/a.cpp", "name": "a.cpp", "code_path": "src/a.cpp"},
        {"path": "src/b.cpp", "name": "b.cpp", "code_path": "src/b.cpp"},
        {"path": "src/c.cpp", "name": "c.cpp", "code_path": "src/c.cpp"},
    ]
    assert actual == expected

    actual = core.derive_default_parameter(defaults, "headers_public", all_files)
    expected = [
        {"path": "include/abc/abc.h", "name": "abc.h", "code_path": "abc/abc.h"},
    ]
    assert actual == expected


def test_init_git_repo():
    dir = "/Users/frodo-baggins/projects/test-project/"
    actual = core.init_git_repo(dir)
    expected = [
        {
            "dir": PurePath(dir),
            "cmds": [
                "git init --initial-branch=main",
            ],
        }
    ]
    assert expected == actual


def test_setup_vendor():
    dir = "/Users/frodo-baggins/projects/test-project/"
    tgt_dir = Path(dir)
    config: dict = {}
    actual = core.setup_vendor(config, tgt_dir, dry_run=True)
    expected: list = []
    assert actual == expected

    config = {
        "deps": [
            {
                "name": "CLI11",
                "git_url": "https://github.com/CLIUtils/CLI11.git",
                "git_checkout": "master",
            },
            {
                "name": "courier",
                "git_url": "https://github.com/bigladder/courier.git",
                "git_checkout": "main",
            },
            {
                "name": "toml11",
                "git_url": "https://github.com/ToruNiina/toml11.git",
                "git_checkout": "1234567",
            },
        ],
    }
    actual = core.setup_vendor(config, tgt_dir, dry_run=True)
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
        assert len(actual[idx]["cmds"]) == len(expected[idx]["cmds"])  # type: ignore
        for ca, ce in zip(actual[idx]["cmds"], expected[idx]["cmds"]):  # type: ignore
            assert ca == ce
    assert actual == expected


def test_gen_copyright():
    copy_template = (
        "COPYRIGHT (C) {% if start_year is defined and start_year != year %}{{ start_year }}-{% endif %}{{ year }} US"
    )
    year = datetime.now().year
    start_year = 2020
    params = {"year": year, "start_year": start_year}
    all_files = {
        Path("README.md"),
        Path("src/a.cpp"),
        Path("src/b.cpp"),
        Path("src/c.cpp"),
        Path("src/hidden.h"),
        Path("app/abc.cpp"),
        Path("include/abc/abc.h"),
    }
    expected_copy = f"// COPYRIGHT (C) {start_year}-{year} US"
    expected = {
        "src/a.cpp": [expected_copy],
        "src/b.cpp": [expected_copy],
        "src/c.cpp": [expected_copy],
        "src/hidden.h": [expected_copy],
        "app/abc.cpp": [expected_copy],
        "include/abc/abc.h": [expected_copy],
    }
    actual = core.gen_copyright(params, copy_template, all_files)
    assert actual == expected


def test_render_copyright_template():
    year = datetime.now().year
    start_year = 2020
    name_of_copyright_holder = "Big Ladder Software"
    contact = "info@bigladdersoftware.com"
    SPDX_license_name = "BSD-3-Clause"
    params = {
        "year": year,
        "start_year": start_year,
        "name_of_copyright_holder": name_of_copyright_holder,
        "contact_email": contact,
        "SPDX_license_name": SPDX_license_name,
    }
    filename = Path("src/a.cpp")
    expected_copy = f"// SPDX-FileCopyrightText: © {start_year} {name_of_copyright_holder} <{contact}>\n// SPDX-License-Identifier: {SPDX_license_name}\n"  # noqa: E501
    environment = Environment(
        loader=FileSystemLoader(Path(__file__).parent.parent / "atheneum_forge", encoding="utf-8"),
        keep_trailing_newline=True,
    )
    actual = core.render_copyright_string(environment, params, filename)
    assert actual == expected_copy


# TODO: This test has File IO - separate
def test_prepend_copyright():
    file_content = """
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
    """.strip()
    cpp_file = Path(__file__).parent / "test_prepend_copyright.cpp"
    with open(cpp_file, "w", encoding="utf-8") as f:
        f.write(file_content)
    copyright_text = "// Copyright 2025 Big Ladder Software\n"
    core.prepend_copyright_to_copy(cpp_file, copyright_text)
    with open(cpp_file, "r", encoding="utf-8") as readback:
        actual = readback.read()
        expected = copyright_text + file_content
        assert actual == expected
    os.remove(cpp_file)


# TODO: This test has File IO - separate out
def test_do_not_prepend_copyright():
    file_content = """
// COPYRIGHT (C) 2024 US
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
    """.strip()
    cpp_file = Path(__file__).parent / "test_prepend_copyright.cpp"
    with open(cpp_file, "w", encoding="utf-8") as f:
        f.write(file_content)
    copyright_text = "// Copyright 2025 Big Ladder Software\n"
    core.prepend_copyright_to_copy(cpp_file, copyright_text)
    with open(cpp_file, "r", encoding="utf-8") as readback:
        actual = readback.read()
        expected = file_content
        assert actual == expected
    os.remove(cpp_file)


def test_update_copyright():
    file_content = """
// COPYRIGHT (C) 2024 US
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
    """.strip()
    copy_lines = ["// COPYRIGHT (C) 2024 US"]
    expected = file_content
    actual = core.update_copyright(file_content, copy_lines)
    print(f"EXPECT:\n{expected}")
    print(f"ACTUAL:\n{actual}")
    assert actual == expected

    copy_lines = ["// COPYRIGHT (C) 2025 US"]
    expected = """
// COPYRIGHT (C) 2025 US
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
""".strip()
    actual = core.update_copyright(file_content, copy_lines)
    print(f"EXPECT:\n{expected}")
    print(f"ACTUAL:\n{actual}")
    assert actual == expected

    file_content = """
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
    """.strip()
    copy_lines = ["// COPYRIGHT (C) 2025 US"]
    expected = """
// COPYRIGHT (C) 2025 US
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
""".strip()
    actual = core.update_copyright(file_content, copy_lines)
    print(f"EXPECT:\n{expected}")
    print(f"ACTUAL:\n{actual}")
    assert actual == expected

    file_content = ""
    copy_lines = ["// COPYRIGHT (C) 2025 US"]
    expected = "// COPYRIGHT (C) 2025 US"
    actual = core.update_copyright(file_content, copy_lines)
    assert actual == expected

    file_content = """
// Copyright is a lost concept.
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
    """.strip()
    expected = """
// COPYRIGHT (C) 2025 US
// Copyright is a lost concept.
#include <iostream>
int main(void) {
  std::cout << "Hello, World!";
  return 0;
}
    """.strip()
    actual = core.update_copyright(file_content, copy_lines)
    assert actual == expected
