"""Tests for previously-uncovered edge cases and error paths in atheneum_forge.core."""

import pytest

from atheneum_forge import core

# ---------------------------------------------------------------------------
# prepend_copyright_to_copy: short/empty files (high-priority gap #1)
#
# Reading the first two lines with `next()` used to raise StopIteration on
# files shorter than two lines; these pin the safe behavior.
# ---------------------------------------------------------------------------


def test_prepend_copyright_to_empty_file(tmp_path):
    target = tmp_path / "empty.cpp"
    target.write_text("", encoding="utf-8")
    core.prepend_copyright_to_copy(target, "// (C) Example\n")
    assert target.read_text(encoding="utf-8") == "// (C) Example\n"


def test_prepend_copyright_to_single_line_file(tmp_path):
    target = tmp_path / "one_line.cpp"
    target.write_text("int main() { return 0; }", encoding="utf-8")
    core.prepend_copyright_to_copy(target, "// (C) Example\n")
    assert target.read_text(encoding="utf-8") == "// (C) Example\nint main() { return 0; }"


def test_prepend_copyright_skips_single_line_with_existing_notice(tmp_path):
    target = tmp_path / "noticed.cpp"
    target.write_text("// Copyright 2024 Someone", encoding="utf-8")
    core.prepend_copyright_to_copy(target, "// (C) Example\n")
    assert target.read_text(encoding="utf-8") == "// Copyright 2024 Someone"


def test_prepend_copyright_noop_when_text_empty(tmp_path):
    target = tmp_path / "untouched.cpp"
    target.write_text("body", encoding="utf-8")
    core.prepend_copyright_to_copy(target, "")
    assert target.read_text(encoding="utf-8") == "body"


# ---------------------------------------------------------------------------
# merge_defaults_into_config: validation/error paths (high-priority gap #2)
#
# Each distinct TypeError branch is exercised, and the message is asserted so
# the tests prove the f-string interpolation actually works (the messages used
# to contain literal "{v}" / "{ repr(v) }", and the missing-required branch
# referenced a stale loop variable).
# ---------------------------------------------------------------------------


def test_merge_defaults_str_type_mismatch():
    with pytest.raises(TypeError) as exc:
        core.merge_defaults_into_config({"project_name": 123}, {"project_name": {"type": "str"}})
    message = str(exc.value)
    assert "project_name" in message
    assert "str" in message
    assert "123" in message  # value is interpolated, not literal "{ repr(v) }"


def test_merge_defaults_int_type_mismatch():
    with pytest.raises(TypeError):
        core.merge_defaults_into_config({"version_major": "oops"}, {"version_major": {"type": "int:>=0"}})


def test_merge_defaults_enum_requires_string():
    with pytest.raises(TypeError):
        core.merge_defaults_into_config(
            {"license": 7},
            {"license": {"type": "enum", "options": ["BSD-3-Clause"]}},
        )


def test_merge_defaults_enum_invalid_option():
    with pytest.raises(TypeError) as exc:
        core.merge_defaults_into_config(
            {"license": "MIT"},
            {"license": {"type": "enum", "options": ["BSD-3-Clause", "Apache-2.0"]}},
        )
    assert "MIT" in str(exc.value)  # f-string interpolates the offending value


def test_merge_defaults_missing_required_names_the_key():
    with pytest.raises(TypeError) as exc:
        core.merge_defaults_into_config({}, {"needs_value": {"type": "str"}})
    assert "needs_value" in str(exc.value)  # names the missing key, not a stale loop var
