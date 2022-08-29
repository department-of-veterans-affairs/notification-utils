# notifications-utils

Shared Python 3 code for Notification to provide logging utilities, etc.  It has not been run against any version of python 2.x

## Installing Dependencies

Run these commands from the project's root directory to install and activate a virtual environment and to install Python dependencies, including dependencies for running unit tests.

1. python3 -m venv venv/
2. scripts/bootstrap.sh

If you encounter an error about Wheel failing to build, ensure you have the Python3 development libraries installed on your machine.  On Linux, this is the package `libpython3-dev`.

## Unit Tests

The `./scripts/run_tests.sh` script runs all unit tests using [py.test](http://pytest.org/latest/) and applies syntax checking using [pycodestyle](https://pypi.python.org/pypi/pycodestyle).

## Versioning

After making changes in this repository, complete the following steps to see those changes in `notification-api`. 
Note: To test locally before pushing, do steps #1 and #4 below and then follow instructions in the `notification-api` README.

1. Increment the version in `notifications_utils/version.py`.
2. Push this change.
3. Manually run `./scripts/push-tag.sh`, which will look at `version.py` and push a tag with that version.
4. In `notification-api`, update `requirements.txt` and `requirements-app.txt` to point at the newly generated tag.
5. Push this change again to push the new tag.

## E-mail Template Documentation

Documentation for the template used to render e-mails is in the [docs](./docs/README.md) folder.
