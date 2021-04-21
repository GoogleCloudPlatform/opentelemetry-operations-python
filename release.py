#!/usr/bin/env python3
# Copyright 2021 Google
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
import functools
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Literal, Sequence, TypedDict, Union

RELEASE_COMMIT_FMT = """Release {release_tag} (Part 1/2) release commit

- Update version.py files
- Marked releases in changelogs
{bump_strs}
"""

NEW_DEV_COMMIT_FMT = """Release {release_tag} (Part 2/2) bump version to new dev versions

- Update version.py files
{bump_strs}
"""

ARGS_DESCRIPTION = """
Create release branch with bumped changelogs and updated versions.

Creates two commits in a new release branch (create new branch first). The
first commit (a) updates the changelogs and version.py with the
release_version specified for any packages in the release_config_json
positional arg. This will be the tagged release commit. The second commit (b)
updates the version.py file to the new_dev_version for each package specified
in release_config_json.

Create a PR and merge it with github's "Rebase and merge" option, so that the
two commits appear in the master history. Then, you can create a tag and release
for the first commit. Do NOT merge with "Squash and merge", or commit (a) will
be overwritten by (b).
"""


BumpConfig = TypedDict(
    "BumpConfig",
    {
        # The version to bump to for releasing
        "release_version": str,
        # The version to set in main branch after release commit
        "dev_version": str,
    },
)
ReleaseConfig = Dict[
    Literal[
        "opentelemetry-exporter-gcp-monitoring",
        "opentelemetry-exporter-gcp-trace",
        "opentelemetry-propagator-gcp",
        "opentelemetry-resourcedetector-gcp",
    ],
    BumpConfig,
]


def get_version_py_path(package_name: str) -> Path:
    return next((repo_root() / package_name).glob("**/version.py"))


def get_current_version(package_name: str) -> str:
    version_py_path = get_version_py_path(package_name)
    package_info: Dict[str, str] = {}
    with open(version_py_path) as version_file:
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
    parser.add_argument(
        "release_tag",
        help="The tag name to use for the release. Use the highest version number being released",
    )
    parser.add_argument(
        "release_config_json",
        help="A json string object of the package names to bump to what new version. "
        'For example, {"opentelemetry-propagator-gcp": {"release_version": "1.1.0rc1",'
        ' "dev_version": "1.1.0dev0"}}. '
        "See source code for details of json structure.",
    )
    return parser.parse_args()


@functools.cache
def repo_root() -> Path:
    return Path(
        run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
        .stdout.decode()
        .strip()
    )


def run(
    args: Union[str, Sequence[str]], **kwargs
) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, **kwargs)


def git_commit_with_message(message: str) -> None:
    run(["git", "commit", "-a", "-m", message])


def create_release_commit(
    release_config: ReleaseConfig, release_tag: str
) -> None:
    for package_name, bump_config in release_config.items():
        current_version = get_current_version(package_name)
        print(
            "Updating version.py and CHANGELOG.md for package {}. Current version: {}\nReleasing new version {}\nBumping dev version to {}".format(
                package_name,
                current_version,
                bump_config["release_version"],
                bump_config["dev_version"],
            )
        )

        # update the version.py files
        find_and_replace(
            re.escape(get_current_version(package_name)),
            bump_config["release_version"],
            [get_version_py_path(package_name)],
        )

        # Mark release in changelogs
        today = datetime.now().strftime("%Y-%m-%d")
        find_and_replace(
            r"\#\#\ Unreleased",
            r"## Unreleased\n\n## Version {}\n\nReleased {}".format(
                bump_config["release_version"], today
            ),
            [repo_root() / package_name / "CHANGELOG.md"],
        )

    git_commit_with_message(
        RELEASE_COMMIT_FMT.format(
            release_tag=release_tag,
            bump_strs="\n".join(
                "- Bump {} to v{}".format(
                    package_name,
                    bump_config["release_version"],
                )
                for package_name, bump_config in release_config.items()
            ),
        )
    )


def create_new_dev_commit(
    release_config: ReleaseConfig, release_tag: str
) -> None:
    for package_name, bump_config in release_config.items():
        # Update version.py file to dev version
        find_and_replace(
            re.escape(bump_config["release_version"]),
            bump_config["dev_version"],
            [get_version_py_path(package_name)],
        )

    git_commit_with_message(
        NEW_DEV_COMMIT_FMT.format(
            release_tag=release_tag,
            bump_strs="\n".join(
                "- Bump {} to v{}".format(
                    package_name,
                    bump_config["dev_version"],
                )
                for package_name, bump_config in release_config.items()
            ),
        )
    )


def main() -> None:
    args = parse_args()
    release_config: ReleaseConfig = json.loads(args.release_config_json)
    release_tag: str = args.release_tag

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

    # create new release branch
    run(["git", "clean", "-fdx", "-e", "venv/", "-e", ".tox/"])
    run(
        [
            "git",
            "checkout",
            "-b",
            "release-pr/{}".format(release_tag),
            # "origin/master",
        ],
        cwd=repo_root(),
    )

    create_release_commit(
        release_config=release_config,
        release_tag=release_tag,
    )
    create_new_dev_commit(
        release_config=release_config,
        release_tag=release_tag,
    )


if __name__ == "__main__":
    main()
