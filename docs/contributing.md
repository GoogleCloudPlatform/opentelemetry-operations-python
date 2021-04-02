# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution;
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

It is a good idea to create your pull request as a
[Draft](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests#draft-pull-requests).
Once you have looked over your pull request and all CI checks are passing,
publish your changes.

## Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Development Instructions

This project is a monorepo for several PyPI packages, each in a
`opentelemetry-*` subdirectory. Because each package may have different
dependencies, we use a virtual environment per package which can be created
with tox.

### Install tox

This project uses [tox](https://tox.readthedocs.io/en/latest/index.html) for
development, so make sure it is installed on your system:

```sh
pip install tox tox-factor
```

To create the virtual environment `venv/` in the root of each package for
development, run:

```sh
tox -f dev -pauto
```

### Running tests

This project supports python versions 3.4 to 3.8. To run tests, use `tox`:

```sh
# List all tox environments
tox -l

# Run python3.8 exporter tests
tox -e py38-ci-test-exporter

# Run all python3.8 tests in parallel
tox -f py38-test -pauto

# All checks that run in continuous integration use the "ci" factor, which
# makes it easy to test without submitting a PR. To run all of them in
# parallel, skipping any python versions that are not present on your system:
tox -s true -f ci -pauto
```

### Running lint and autofix

```sh
# Run lint checks
tox -f lint

# To fix formatting and import ordering lint issues automatically
tox -f fix
```

### Issues

`tox` usually recreates virtual environments for you whenever the config
changes. However, it doesn't fully track external requirements files and your
dependencies can be outdated. Either delete the `.tox/` directory or use the
`-r` flag with tox to recreate virtual environments.
