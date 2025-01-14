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
from tempfile import TemporaryDirectory
from typing import Iterator
import subprocess
import sys

import requests


@dataclass
class Update:
    destination: Path
    source: Path
    content: str


@dataclass
class Dependency:
    name: str
    local_files: list[Path]
    remote_files: list[str]
    custom_patches: list[Path] | None = None
    updates: list[Update] = field(default_factory=list)
    tmpdir: TemporaryDirectory | None = None


THIRDPARTY_DIR = Path("avs/3rdparty")
DEPS = [
    Dependency(
        "stb_image",
        [THIRDPARTY_DIR / "stb_image.h"],
        ["https://raw.githubusercontent.com/nothings/stb/master/stb_image.h"],
        [THIRDPARTY_DIR / "stb_image.h-unused-png-chunk.patch"],
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
        [THIRDPARTY_DIR / "pevents.cpp-wait-for-multiple-events-return-signal.patch"],
    ),
]


def download_remote_files(dep: Dependency, tmpdir: Path, quiet: bool) -> list[Path]:
    upstream_files = []
    for local_file, remote_file in zip(dep.local_files, dep.remote_files):
        if not quiet:
            print(f"Checking {local_file.name} from {remote_file}")
        response = requests.get(remote_file)
        if response.status_code != 200:
            print(
                f"Error getting {dep.name} | {local_file}: {response.status_code} ({remote_file})",
                file=sys.stderr,
            )
            return []
        tmp_file = tmpdir / local_file.relative_to(THIRDPARTY_DIR)
        tmp_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file.write_text(response.text)
        upstream_files.append(tmp_file)
    return upstream_files


def apply_patches(dep: Dependency, tmpdir: Path, quiet: bool):
    # patch file appended to command below
    patch_cmd = ["patch", "-s", "-p1", "-d", str(tmpdir), "-i"]
    if not dep.custom_patches:
        return
    for patch in dep.custom_patches:
        if not quiet:
            print(f"Applying patch {patch}")
        try:
            subprocess.run(patch_cmd + [Path(".").absolute() / patch], check=True)
        except subprocess.CalledProcessError:
            print(f"Error applying {patch} to {dep.name}, ignoring", file=sys.stderr)
            continue


def check_dependencies(quiet: bool = False) -> Iterator[Dependency]:
    for dep in DEPS:
        tmp = TemporaryDirectory()
        dep.tmpdir = tmp
        tmpdir = Path(tmp.name)
        upstream_files = download_remote_files(dep, tmpdir, quiet)
        if not upstream_files:
            continue
        dep.updates = []
        if dep.custom_patches:
            apply_patches(dep, tmpdir, quiet)
        for local_file, upstream_file in zip(dep.local_files, upstream_files):
            show_diff = True
            try:
                local_content = local_file.read_text()
            except FileNotFoundError:
                local_content = ""
                show_diff = False
            try:
                upstream_content = upstream_file.read_text()
            except FileNotFoundError:
                upstream_content = ""
                show_diff = False
            diff = list(
                unified_diff(
                    local_content.splitlines(keepends=True),
                    upstream_content.splitlines(keepends=True),
                    fromfile=str(local_file),
                    tofile=str(upstream_file),
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
                dep.updates.append(Update(local_file, upstream_file, upstream_content))
        if dep.updates:
            yield dep


def do_update(dependency):
    for update in dependency.updates:
        print(f"Updating {dependency.name}: {update.destination}")
        update.destination.parent.mkdir(parents=True, exist_ok=True)
        update.destination.write_text(update.content)


def create_patch(dep: Dependency, patch_filename: str, quiet: bool):
    patch_content = ""
    if not dep.tmpdir:
        print(f"Error creating patch for {dep.name}: no tmpdir", file=sys.stderr)
        return
    for update in dep.updates:
        # Flags recommended in "man patch(1) > Notes for Patch Senders"
        diff_cmd = [
            "diff",
            "--new-file",
            "--text",
            "--unified",
            "--recursive",
            str(update.source),
            str(update.destination.relative_to(THIRDPARTY_DIR)),
        ]
        diff_proc = subprocess.run(
            diff_cmd, cwd=THIRDPARTY_DIR, capture_output=True, text=True
        )
        if diff_proc.returncode > 1:
            print(
                f"Error diffing {update.source} vs. {update.destination}:"
                f"\n{' '.join([str(s) for s in diff_cmd])}: {diff_proc.stderr}",
                file=sys.stderr,
            )
        # "--- /tmp/tmp01234567/foo/bar"  ->  "--- foo/bar"
        patch_content += "\n" + diff_proc.stdout.replace(dep.tmpdir.name + "/", "")
    patch_file = THIRDPARTY_DIR / patch_filename
    if not quiet:
        print(f"Creating patch {patch_file.absolute()}")
    patch_file.write_text(patch_content.strip())


def update_patch_menu(name: str, dont_ask: bool) -> str:
    choice = ""
    while not choice:
        choice_str = input(
            f"[U]pdate {name}?\nSave as [P]atch?\n[I]gnore this dependency\nE[X]it?\n> "
        )
        choice_str = choice_str[:1].lower()
        if choice_str in "upix":
            choice = choice_str
    return choice


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
            match update_patch_menu(dep.name, dont_ask):
                case "u":
                    do_update(dep)
                case "s":
                    name = ""
                    while not name:
                        name = input("Patch name: ")
                    name = name.removesuffix(".patch").removesuffix(".diff")
                    create_patch(dep, name + ".patch", quiet=False)
                case "i":
                    continue
                case "x":
                    return 0
    return num_updates_check_mode_exitcode


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        pass
