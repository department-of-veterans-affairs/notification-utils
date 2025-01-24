# notifications-utils

Shared Python 3 code for Notification to provide logging utilities, etc.  It has not been run against any version of python 2.x

## Installing Dependencies

Run these commands from the project's root directory to install and activate a virtual environment and to install Python dependencies, including dependencies for running unit tests.

1. `python3.10 -m venv venv`
2. `. venv/bin/activate`
3. `./scripts/bootstrap.sh`

If you encounter an error about Wheel failing to build, ensure you have the Python3 development libraries installed on your machine.  On Linux, this is the package `libpython3-dev`.

## Unit Tests

The `./scripts/run_tests.sh` script runs all unit tests using [py.test](http://pytest.org/latest/) and applies syntax checking using [pycodestyle](https://pypi.python.org/pypi/pycodestyle).

## Versioning

With the virtual environment active, run `python setup.py --version` to see the current version **on the current branch**.  

Before merging, update the version in the `notifications_utils/version.py` file. Once merged, while on the `main` branch use `git tag` to add release tags to commits, and push the tags. 

For example
```
git tag <current-utils-version>
git push origin <current-utils-version>
```

Please create and publish release notes when the [new tag is available in Github.](https://github.com/department-of-veterans-affairs/notification-utils/tags). This can be done by viewing [Releases](https://github.com/department-of-veterans-affairs/notification-utils/releases), selecting `Draft a new release` and selecting the most recent tag. 


After merging changes in this repository and creating the release notes, you must update notification-api to use the changes. Run `poetry update notification-utils` in an api branch, and then push the PR for approval/merge. The PR only should contain changes made to the lock file.

## E-mail Template Documentation

Documentation for the template used to render e-mails is in the [docs](./docs/README.md) folder.
