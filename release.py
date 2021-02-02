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
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Sequence, Union

RELEASE_COMMIT_FMT = """Release {release_version} (Part 1/2) release commit

- Update version.py files
- Marked releases in changelogs
- Pinned `opentelemetry-{{api,sdk}}` versions in dev-constraints
- Pinned `opentelemetry-{{api,sdk}}` versions in each package's `setup.cfg` file
"""

NEW_DEV_COMMIT_FMT = """Release {release_version} (Part 2/2) bump version to {new_dev_version}

- Update version.py files
- Unpin `opentelemetry-{{api,sdk}}` versions in each package's `setup.cfg` file
"""


ARGS_DESCRIPTION = """
Create release branch with bumped changelogs and updated versions.

Creates two commits in a new release branch (create new branch first). The first
commit (a) updates the changelogs for the new release_version, and updates
version.py files to the new release_version. This will be the tagged release
commit. The second commit (b) updates the version.py file to the
new_dev_version.

Create a PR and merge it with github's "Rebase and merge" option, so that the
two commits appear in the master history. Then, you can create a tag and release
for the first commit. Do NOT merge with "Squash and merge", or commit (a) will
be overwritten by (b).
"""


def get_current_version() -> str:
    package_info: Dict[str, str] = {}
    with open(
        Path("opentelemetry-exporter-google-cloud")
        / "src"
        / "opentelemetry"
        / "exporter"
        / "google"
        / "version.py"
    ) as version_file:
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
        help="The new developement version string to update master",
        required=True,
    )
    required_named_args.add_argument(
        "--ot_version",
        help="The version specifer for opentelemetry packages. E.g. '~=0.11.b0'",
        required=True,
    )
    return parser.parse_args()


def run(
    args: Union[str, Sequence[str]], **kwargs
) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, **kwargs)


def git_commit_with_message(message: str) -> None:
    run(["git", "commit", "-a", "-m", message])


def create_release_commit(
    git_files: Iterable[Path],
    current_version: str,
    release_version: str,
    ot_version: str,
    repo_root: Path,
) -> None:
    # Update version.py files
    find_and_replace(
        re.escape(current_version),
        release_version,
        (path for path in git_files if path.name == "version.py"),
    )

    # Mark release in changelogs
    today = datetime.now().strftime("%Y-%m-%d")
    find_and_replace(
        r"\#\#\ Unreleased",
        rf"## Unreleased\n\n## Version {release_version}\n\nReleased {today}",
        (path for path in git_files if path.name == "CHANGELOG.md"),
    )

    # Pin the OT version in dev-constraints.txt
    find_regex = (
        r"^"
        + re.escape(
            "-e git+https://github.com/open-telemetry/opentelemetry-python.git@"
        )
        + r".+#egg=(.+)&subdirectory=.+$"
    )
    matched = find_and_replace(
        find_regex,
        rf"\1{ot_version}",
        [repo_root / "dev-constraints.txt"],
        flags=re.MULTILINE,
    )
    if not matched:
        find_and_replace(
            r"^(opentelemetry-(?:api-sdk)).*",
            rf"\1{ot_version}",
            [repo_root / "dev-constraints.txt"],
            flags=re.MULTILINE,
        )

    # Pin the OT version in each package's setup.cfg file
    find_and_replace(
        r"(opentelemetry-(?:api|sdk))",
        rf"\1{ot_version}",
        (path for path in git_files if path.name == "setup.cfg"),
    )

    git_commit_with_message(
        RELEASE_COMMIT_FMT.format(release_version=release_version)
    )


def create_new_dev_commit(
    git_files: Iterable[Path], release_version: str, new_dev_version: str,
) -> None:
    # Update version.py files
    find_and_replace(
        re.escape(release_version),
        new_dev_version,
        (path for path in git_files if path.name == "version.py"),
    )

    # Unpin the OT version in each package's setup.cfg file, so it comes from
    # dev-constraints.txt
    find_and_replace(
        r"(opentelemetry-(?:api|sdk)).+$",
        r"\1",
        (path for path in git_files if path.name == "setup.cfg"),
        flags=re.MULTILINE,
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
    ot_version: str = args.ot_version

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

    repo_root = Path(
        run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
        .stdout.decode()
        .strip()
    ).absolute()

    # create new release branch
    run(["git", "clean", "-fdx", "-e", "venv/", "-e", ".tox/"])
    run(
        [
            "git",
            "checkout",
            "-b",
            "release-pr/{}".format(release_version),
            "origin/master",
        ],
        cwd=repo_root,
    )

    git_files = [
        repo_root / path
        for path in run(
            ["git", "ls-files"], cwd=repo_root, capture_output=True
        )
        .stdout.decode()
        .strip()
        .split()
        if __file__ not in path
    ]

    create_release_commit(
        git_files=git_files,
        current_version=current_version,
        release_version=release_version,
        ot_version=ot_version,
        repo_root=repo_root,
    )
    create_new_dev_commit(
        git_files=git_files,
        release_version=release_version,
        new_dev_version=new_dev_version,
    )


if __name__ == "__main__":
    main()
