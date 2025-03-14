#!/bin/bash
#
# Run project tests
#
# NOTE: This script expects to be run from the project root with ./scripts/run_tests.sh.
# It is part of the Github CI workflow.

# Use default environment vars for localhost if not already set.

set -o pipefail

function display_result {
  RESULT=$1
  EXIT_STATUS=$2
  TEST=$3

  if [ $RESULT -ne 0 ]; then
    echo -e "\033[31m$TEST failed\033[0m"
    exit $EXIT_STATUS
  else
    echo -e "\033[32m$TEST passed\033[0m"
  fi
}

flake8 --config .flake8 .
display_result $? 1 "Code style check"

pytest -n4 tests/
display_result $? 3 "Unit tests"

python setup.py sdist
