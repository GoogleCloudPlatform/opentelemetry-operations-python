#!/usr/bin/env python3
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import re
import functools
import subprocess
import sys
from packaging.version import InvalidVersion, Version
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Sequence, Union

RELEASE_COMMIT_FMT = """Release {release_version} (Part 1/2) release commit

- Update version.py files
- Marked releases in changelogs
"""

NEW_DEV_COMMIT_FMT = """Release {release_version} (Part 2/2) bump version to {new_dev_version}

- Update version.py files to dev version
"""


ARGS_DESCRIPTION = """
Create release branch with bumped changelogs and updated versions.

Creates two commits in a new release branch (create new branch first). The first
commit (a) updates the changelogs for the new release_version, and updates
version.py files to the new release_version. This will be the tagged release
commit. The second commit (b) updates the version.py file to the
new_dev_version.

Create a PR and merge it with github's "Rebase and merge" option, so that the
two commits appear in the main history. Then, you can create a tag and release
for the first commit. Do NOT merge with "Squash and merge", or commit (a) will
be overwritten by (b).
"""

# Map of different suffixes to use instead of the given ones in release_version
ALTERNATE_SUFFIXES = {
    # Mark monitoring and resource detector alpha
    "opentelemetry-exporter-gcp-monitoring": "a0",
    "opentelemetry-exporter-gcp-logging": "a0",
    "opentelemetry-resourcedetector-gcp": "a0",
}


@functools.cache
def repo_root() -> Path:
    return Path(
        run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
        .stdout.decode()
        .strip()
    )


@functools.cache
def get_version_py_paths() -> list[Path]:
    return list(repo_root().glob("opentelemetry-*/**/version.py"))


@functools.cache
def get_current_version() -> str:
    package_info: Dict[str, str] = {}
    with get_version_py_paths()[0].open() as version_file:
        exec(version_file.read(), package_info)
    return package_info["__version__"]


def find_and_replace(
    pattern_str: str,
    replacement: str,
    file_paths: Iterable[Path],
    flags: int = 0,
) -> bool:
    pattern = re.compile(pattern_str, flags=flags)
    any_matches = False

    for file_path in file_paths:
        with open(file_path, "r+") as file:
            text = file.read()
            replaced_text, num_subs = pattern.subn(replacement, text)
            if num_subs > 0:
                file.seek(0)
                file.truncate()
                file.write(replaced_text)
                any_matches = True

    return any_matches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=ARGS_DESCRIPTION)
    required_named_args = parser.add_argument_group("required named arguments")
    required_named_args.add_argument(
        "--release_version",
        help="The version number to release. Must exactly match OT API/SDK version to pin against",
        required=True,
    )
    required_named_args.add_argument(
        "--new_dev_version",
        help="The new development version string to update main",
        required=True,
    )
    return parser.parse_args()


def run(
    args: Union[str, Sequence[str]], **kwargs
) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, **kwargs)


def git_commit_with_message(message: str) -> None:
    run(["git", "commit", "-a", "-m", message])


def create_release_commit(release_version: str,) -> None:
    release_version_parsed = Version(release_version)
    today = datetime.now().strftime("%Y-%m-%d")
    alternate_suffix_paths = {
        repo_root() / package_name: suffix
        for package_name, suffix in ALTERNATE_SUFFIXES.items()
    }

    for package_root in repo_root().glob("opentelemetry-*/"):
        if package_root in alternate_suffix_paths:
            suffix = alternate_suffix_paths[package_root]
            release_version_use = release_version_parsed.base_version + suffix
            # verify the resulting version is valid by PEP440
            try:
                Version(release_version_use)
            except InvalidVersion as e:
                raise Exception(
                    "Resulting version string for package {} with specified suffix '{}' "
                    "is not valid: {}".format(package_root.name, suffix, e,),
                )

        else:
            release_version_use = release_version

        # Update version.py files
        find_and_replace(
            r'__version__ = ".*"',
            '__version__ = "{}"'.format(release_version_use),
            package_root.glob("**/version.py"),
        )
        # Mark release in changelogs
        find_and_replace(
            r"\#\#\ Unreleased",
            rf"## Unreleased\n\n## Version {release_version_use}\n\nReleased {today}",
            [package_root / "CHANGELOG.md"],
        )

    git_commit_with_message(
        RELEASE_COMMIT_FMT.format(release_version=release_version)
    )


def create_new_dev_commit(release_version: str, new_dev_version: str) -> None:
    # Update version.py files
    find_and_replace(
        r'__version__ = ".*"',
        '__version__ = "{}"'.format(new_dev_version),
        get_version_py_paths(),
    )

    git_commit_with_message(
        NEW_DEV_COMMIT_FMT.format(
            release_version=release_version, new_dev_version=new_dev_version
        )
    )


def main() -> None:
    args = parse_args()
    current_version = get_current_version()
    release_version: str = args.release_version
    new_dev_version: str = args.new_dev_version

    git_status_output = (
        run(["git", "status", "-s"], capture_output=True)
        .stdout.decode()
        .strip()
    )
    if git_status_output != "":
        print(
            "Git working directory is not clean, commit or stash all changes. Exiting.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        "Current version: {}\nReleasing new version {}\nBumping dev version to {}".format(
            current_version, release_version, new_dev_version
        )
    )

    # create new release branch
    run(["git", "clean", "-fdx", "-e", "venv/", "-e", ".tox/"])
    run(
        [
            "git",
            "checkout",
            "-b",
            "release-pr/{}".format(release_version),
            "origin/main",
        ],
        cwd=repo_root(),
    )

    create_release_commit(release_version=release_version,)
    create_new_dev_commit(
        release_version=release_version, new_dev_version=new_dev_version,
    )


if __name__ == "__main__":
    main()
