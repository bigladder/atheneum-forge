from pathlib import Path


def task_test():
    """Performs tests"""
    return {
        "actions": ["pytest -v test"],
        "clean": True,
        "verbosity": 2,
    }


def task_examples():
    """Run examples"""
    for file_path in Path("examples").glob("*.py"):
        yield {
            "name": file_path.name,
            "actions": [f"python {file_path}"],
            "clean": True,
            "verbosity": 2,
        }
