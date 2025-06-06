import atheneum_forge.update as updater


def test_update_dictionary():
    source_dict = {
        "project": {"name": "python_generator", "readme": "README.md", "dependencies": []},
        "dependency-groups": {
            "dev": [
                "doit",
                "mypy",
                "pre-commit",
                "pytest",
                "ruff",
            ]
        },
        "tool.mypy": {"disallow_incomplete_defs": "True", "no_implicit_optional": "True", "check_untyped_defs": "True"},
        "[tool.mypy.overrides]": {"module": "lattice.*", "disable_error_code": ["annotation-unchecked", "import"]},
    }
    destination_dict = {
        "project": {"name": "python_generator", "readme": "README.md", "dependencies": []},
        "dependency-groups": {
            "dev": [
                "black",
                "doit",
                "pre-commit",
                "pytest",
                "ruff",
            ]
        },
        "tool.ruff": {"line-length": 120},
    }
    merged_dict = {
        "project": {"name": "python_generator", "readme": "README.md", "dependencies": []},
        "dependency-groups": {
            "dev": [  # This list is sorted for the purposes of testing (FUT sorts lists)
                "black",
                "doit",
                "mypy",
                "pre-commit",
                "pytest",
                "ruff",
            ]
        },
        "tool.ruff": {"line-length": 120},
        "tool.mypy": {"disallow_incomplete_defs": "True", "no_implicit_optional": "True", "check_untyped_defs": "True"},
        "[tool.mypy.overrides]": {"module": "lattice.*", "disable_error_code": ["annotation-unchecked", "import"]},
    }

    updater._update_destination_dict(source_dict, destination_dict)
    assert destination_dict == merged_dict


def test_update_text():
    source_txt_lines = [
        "Lorem ipsum dolor",
        "sed do eiusmod tempor ",
        "incididunt ut labore et ",
        "dolore magna aliqua.",
    ]
    destination_txt_lines = [
        "Lorem ipsum dolor",
        "sit amet, consectetur adipiscing elit,",
        "sed do eiusmod tempor ",
        "dolore magna aliqua.",
    ]
    updater._update_destination_text_list(source_txt_lines, destination_txt_lines)
    merged_text = [
        "Lorem ipsum dolor",
        "sit amet, consectetur adipiscing elit,",
        "sed do eiusmod tempor ",
        "incididunt ut labore et ",
        "dolore magna aliqua.",
    ]

    assert destination_txt_lines == merged_text
