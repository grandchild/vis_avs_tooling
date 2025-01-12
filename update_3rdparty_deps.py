#!/usr/bin/env python3
"""
Check for updates to third-party dependencies.

Usage:
    # Go to "vis_avs" repo root (i.e. not this tooling repo)
    cd vis_avs/
    ./update_3rdparty_deps.py [check] [run]

If "check" is specified, the script will only check for updates and print the files that
updates are available for. The return code will be the number of files that have updates
available.
If no argument is given, the script will interactively prompt the user to update the
files.
If "run" is specified, the script will update the files without any user interaction.
"""

from dataclasses import dataclass, field
from difflib import unified_diff
from pathlib import Path
from typing import Iterator
import sys

import requests


@dataclass
class Update:
    destination: Path
    content: str


@dataclass
class Dependency:
    name: str
    local_files: list[Path]
    remote_files: list[str]
    updates: list[Update] = field(default_factory=list)


THIRDPARTY_DIR = Path("avs/3rdparty")
DEPS = [
    Dependency(
        "stb_image",
        [THIRDPARTY_DIR / "stb_image.h"],
        ["https://raw.githubusercontent.com/nothings/stb/master/stb_image.h"],
    ),
    Dependency(
        "json.hpp",
        [THIRDPARTY_DIR / "json.h"],
        [
            "https://raw.githubusercontent.com/nlohmann/json/master/single_include/nlohmann/json.hpp"
        ],
    ),
    Dependency(
        "pevents",
        [
            THIRDPARTY_DIR / "pevents.h",
            THIRDPARTY_DIR / "pevents.hpp",
            THIRDPARTY_DIR / "pevents.cpp",
        ],
        [
            "https://raw.githubusercontent.com/aholzinger/pevents/master/src/pevents.h",
            "https://raw.githubusercontent.com/aholzinger/pevents/master/src/pevents.hpp",
            "https://raw.githubusercontent.com/aholzinger/pevents/master/src/pevents.cpp",
        ],
    ),
]


def check_dependencies(quiet: bool = False) -> Iterator[Dependency]:
    for dep in DEPS:
        dep.updates = []
        for local_file, remote_file in zip(dep.local_files, dep.remote_files):
            if not quiet:
                print(f"Checking {local_file.name} from {remote_file}")
            response = requests.get(remote_file)
            if response.status_code != 200:
                print(
                    f"Error checking {dep.name}/{local_file.name}: {response.status_code}",
                    file=sys.stderr,
                )
                continue
            remote_content = response.text
            show_diff = True
            try:
                local_content = local_file.read_text()
            except FileNotFoundError:
                local_content = ""
                show_diff = False
            diff = list(
                unified_diff(
                    local_content.splitlines(keepends=True),
                    remote_content.splitlines(keepends=True),
                    fromfile=str(local_file),
                    tofile=remote_file,
                )
            )
            diff_str = "".join(diff)
            # -1 because the first two lines contain the file names
            additions = sum(line.startswith("+") for line in diff) - 1
            deletions = sum(line.startswith("-") for line in diff) - 1
            if diff_str:
                if not quiet:
                    if show_diff:
                        print(diff_str)
                    print(f"{local_file}: +{additions} / -{deletions}")
                dep.updates.append(Update(local_file, remote_content))
        if dep.updates:
            yield dep


def do_update(dependency):
    for update in dependency.updates:
        print(f"Updating {dependency.name}: {update.destination}")
        update.destination.write_text(update.content)


def main(argv: list[str]) -> int:
    check_only: bool = "check" in argv
    dont_ask: bool = "run" in argv and not check_only
    num_updates_check_mode_exitcode: int = 0  # stays zero if not in check_only mode
    for dep in check_dependencies(quiet=check_only or dont_ask):
        if check_only:
            for update in dep.updates:
                print(update.destination)
                num_updates_check_mode_exitcode += 1
        else:
            if dont_ask or input(f"Update {dep.name}? ")[:1].lower() == "y":
                do_update(dep)
    return num_updates_check_mode_exitcode


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
