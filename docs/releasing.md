Releasing - For Maintainers only <!-- omit in toc --> 
================

The release process is:

- [Checkout a clean repo](#checkout-a-clean-repo)
- [Run release script](#run-release-script)
- [Open and merge a PR](#open-and-merge-a-pr)
- [Create a release tag and update stable tag](#create-a-release-tag-and-update-stable-tag)
- [Push to PyPI](#push-to-pypi)

Here is an [example PR
#55](<https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/55>)
and an [example tag
v0.11b0](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/releases/tag/v0.11b0):

## Checkout a clean repo

Optional, but `release.py` runs `git clean -fdx` which will delete any temporary
files in the checkout.

```bash
git clone \
    https://github.com/GoogleCloudPlatform/opentelemetry-operations-python.git \
    opentelemetry-operations-python-release
cd opentelemetry-operations-python-release
git remote add fork git@github.com:$GH_USERNAME/opentelemetry-operations-python.git
```

## Run release script

Run the `release.py` script which creates two commits in a new release
branch. The script does the following:

> Creates two commits in a new release branch (create new branch first). The first
> commit (a) updates the changelogs for the new release_version, and updates
> version.py files to the new release_version. This will be the tagged release
> commit. The second commit (b) updates the version.py file to the
> new_dev_version.

This workflow guarantees that there won't be any commits between (a) and (b)
in the master branch history, as long as you merge with "Rebase and merge".

To create a release at version `0.11b1` and then update package versions in
the repository to `0.12.dev0`:

```bash
./release.py \
    --release_version 0.11b1 \
    --new_dev_version 0.12.dev0
```

You can also specify alternative suffixes to add for certain packages by
updated the `ALTERNATE_SUFFIXES` map in `release.py`. This lets you mark some
packages as rc/alpha/beta/etc. Check the code comments for details.

Besides the suffixes at the end of the version, all packages in this repo are
tied to the same base version. For example, they are all 1.0.0 base version,
but some can be 1.0.0 and others 1.0.0a0.

## Open and merge a PR

You will now have the new branch `release-pr/0.11b1` checked out with the two
commits. Push them to your fork and create a PR:

```bash
git push --set-upstream fork release-pr/0.11b1
# if you have GH cli installed, or create the PR regularly
gh pr create -f -d
```

- **Make sure you review the the commits in the PR INDIVIDUALLY.** The first
commit (a) will be tagged as the release in the next step, so it needs to be
correct.
- After review, **merge your PR with ["Rebase and
merge"](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-request-merges#rebase-and-merge-your-pull-request-commits)
on github.** This is crucial; if you use the regular "Squash and merge", you
will not have the two sequential commits you need to create a release tag.

## Create a release tag and update stable tag

TODO: incorporate these steps into `releasing.py`.

Now, [create a
release](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/releases/new)
with:

- Tag version of `v` + `--new_dev_version` you used above -
**pointing at the first commit (a)** that was merged into master. For the
example PR listed above, that creates release
[`v0.11b0@4ad9ccd`](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/releases/tag/v0.11b0).
- In description, paste a changelog for the packages. I used this (probably
buggy) small script for the example PR's tag:

  ```bash
  for cl in opentelemetry-*/CHANGELOG.md; do
      if cl_entries=`pcregrep -M -o1 "^## Version 0\.10b0$\n\n^Released.*\n\n((?:- [\s\S]+?)*?)(?=(\s+##|\Z))" $cl`
      then
          echo -e "# `dirname $cl`\n$cl_entries"
      fi
  done
  ```

Once the release tag is created, move the `stable` tag to point to the same
commit.

```bash
# pull in the new release tag
git fetch origin

# move stable
git tag -d stable
git push origin :refs/tags/stable
git tag stable v0.11b0

# push
git push --tags
```

## Push to PyPI

TODO: incorporate these steps into `releasing.py`.

Finally, publish the packages. Use PyPI user
[`google_opentelemetry`](https://pypi.org/user/google_opentelemetry/),
consulting internal docs for how to get login credentials.

```bash
# make sure you're checked out to the release tag created before
git checkout v0.11b0

# clean and create fresh venv
git clean -fdx
python3 -m venv venv
source venv/bin/activate
pip install -U pip wheel twine

# Build the packages
for setup_file in opentelemetry-*/setup.py; do
    pushd `dirname $setup_file`
    # to be safe
    rm -rf dist/ build/
    python setup.py sdist bdist_wheel
    popd
done

# See what was built and verify
twine check opentelemetry-*/dist/*

# First, publish to https://test.pypi.org/ to make sure everything goes
# correctly. Consult internal docs for populating TWINE_USERNAME and
# TWINE_PASSWORD environment variables.
twine upload -r testpypi opentelemetry-*/dist/*

# Go check the packages look correct on test pypi. If all is good, upload to
# pypi
twine upload opentelemetry-*/dist/*
```
