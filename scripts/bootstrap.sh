#!/bin/bash
#
# NOTE: This script expects to be run from the project root with ./scripts/bootstrap.sh.
# It is part of the Github CI workflow.

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

# Install Python development dependencies
pip3 install -r requirements_for_test.txt
