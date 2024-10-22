import boilerplate.core as bp


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
    results = bp.generate(repo_dir, target, manifest, config, dry_run=True)
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
    """.strip()
    assert expected == actual
