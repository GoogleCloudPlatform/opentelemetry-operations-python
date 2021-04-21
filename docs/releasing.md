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

> Creates two commits in a new release branch (create new branch first). The
> first commit (a) updates the changelogs and version.py with the
> release_version specified for any packages in the release_config_json
> positional arg. This will be the tagged release commit. The second commit (b)
> updates the version.py file to the new_dev_version for each package specified
> in release_config_json.

This workflow guarantees that there won't be any commits between (a) and (b)
in the master branch history, as long as you merge with "Rebase and merge".

To create a release PR branch `release-pr/1.1.0` with
`opentelemetry-propagator-gcp` at version `1.0.1` and
`opentelemetry-resourcedetector-gcp` at version `1.1.0`, and then update
package versions in the repository:

```bash
./release.py \
    1.1.0 \
    '{ "opentelemetry-propagator-gcp": { "release_version": "1.10a0", "dev_version": "1.1.0dev0" }, "opentelemetry-exporter-gcp-trace": { "release_version": "1.0.0rc1", "dev_version": "1.1.0dev0" }, "opentelemetry-exporter-gcp-monitoring": { "release_version": "1.10a0", "dev_version": "1.1.0dev0" }, "opentelemetry-resourcedetector-gcp": { "release_version": "1.10a0", "dev_version": "1.1.0dev0" } }'
```

## Open and merge a PR

You will now have the new branch `release-pr/1.1.0` checked out with the two
commits. Push them to your fork and create a PR:

```bash
git push --set-upstream fork release-pr/1.1.0
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

- Tag version of `v` + `release_tag` you used above
**pointing at the first commit (a)** that was merged into
master. See [previous
releases](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/releases/)
for examples.
- In description, paste all of the individual changelogs f r the package
versions being released.

Once the release tag is created move the `stable` tag to point to the same
commit.

```bash
# pull in the new release tag
git fetch origin

# move stable
git tag -d stable
git push origin :refs/tags/stable
git tag stable v1.1.0
git push --tags
```

## Push to PyPI

TODO: incorporate these steps into `releasing.py`.

Finally, publish the packages. Use PyPI user
[`google_opentelemetry`](https://pypi.org/user/google_opentelemetry/),
consulting internal docs for how to get login credentials.

```bash
# make sure you're checked out to the release tag created before
git checkout v1.1.0

# clean and create fresh venv
git clean -fdx
python3 -m venv venv
source venv/bin/activate
pip install -U pip wheel twine

# Build the packages that you want to release
for setup_file in {opentelemetry-propagator-gcp,opentelemetry-exporter-gcp-trace}/setup.py; do
    pushd `dirname $setup_file`
    # to be safe
    rm -rf dist/ build/
    python setup.py sdist bdist_wheel
    popd
done

# See what was built and verify
twine check {opentelemetry-propagator-gcp,opentelemetry-exporter-gcp-trace}/dist/*

# First, publish to https://test.pypi.org/ to make sure everything goes
# correctly. Consult internal docs for populating TWINE_USERNAME and
# TWINE_PASSWORD environment variables.
twine upload -r testpypi {opentelemetry-propagator-gcp,opentelemetry-exporter-gcp-trace}/dist/*

# Go check the packages look correct on test pypi. If all is good, upload to
# pypi
twine upload {opentelemetry-propagator-gcp,opentelemetry-exporter-gcp-trace}/dist/*
```
