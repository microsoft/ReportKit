#!/usr/bin/env python3
"""Reject tracked or untracked drift in CI's generated artifact scopes."""

import argparse
from pathlib import Path
import subprocess
import sys


GENERATED_PATHS = (
    "templates",
    "showcase",
    "examples/operational-snapshot/generated",
    "examples/custom-template-project/generated",
    "docs/assets/screenshots",
)


def check_generated_clean(root: Path) -> int:
    root = root.resolve()
    command = ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root)]
    try:
        repository = subprocess.run(
            command + ["rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True,
        )
        if Path(repository.stdout.strip()).resolve() != root:
            print(f"Expected a Git repository root: {root}", file=sys.stderr)
            return 2
        result = subprocess.run(
            command + ["status", "--porcelain", "--untracked-files=all", "--", *GENERATED_PATHS],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Unable to inspect generated artifacts: {error}", file=sys.stderr)
        return 2
    if result.stdout:
        print("Generated artifacts differ from the checkout:", file=sys.stderr)
        print(result.stdout, end="", file=sys.stderr)
        print("Review and regenerate the intended outputs; nothing was staged.", file=sys.stderr)
        return 1
    print("Generated artifact scopes are clean (including untracked files).")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sys.exit(check_generated_clean(parser.parse_args().root))
