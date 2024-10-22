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
[source.athenium]
git = "git@github.com:bigladder/atheneum.git"
git-checkout = "main"
[source.local]
path = "./data"
[files]
static = [
  {source="athenium", from=".clang-format", to="."},
  {source="athenium", from=".gitignore", to="."},
]
template = [
  {source="local", from="CMakeLists.txt", to="."}
]
    """
    data = bp.read_manifest(toml_str)
    assert len(data) > 0
