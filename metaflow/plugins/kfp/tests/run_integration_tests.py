from os import listdir
from os.path import isfile, join
from subprocess import run, PIPE
from typing import List

from .... import R

import kfp
from metaflow import Flow, Metaflow
import pytest
import logging

"""
To run these tests from your terminal, go to the tests directory and run: 
`python -m pytest -s -n 3 run_integration_tests.py`

This script runs all the flows in the `flows` directory. It creates
each kfp run, waits for the run to fully complete, and prints whether
or not the run was successful. It also checks to make sure the logging
functionality works.

More specifically, the tests spawn KFP runs and ensure the spawning processes
have a returncode of 0. If any test fails within KFP, an exception
is raised, the test fails, and the user can access the run link to the failed
KFP run.

Parameters:
-n: specifies the number of parallel processes used by PyTest.

Sometimes, the tests may fail on KFP due to resource quota issues. If they do,
try reducing -n (number of parallel processes) so less simultaneous
KFP runs will be scheduled.

"""


def _python():
    if R.use_r():
        return "python3"
    else:
        return "python"


def obtain_flow_file_paths(flow_dir_path: str) -> List[str]:
    file_paths = [
        file_name
        for file_name in listdir(flow_dir_path)
        if isfile(join(flow_dir_path, file_name)) and not file_name.startswith(".") and not "raise_failure_flow" in file_name
    ]
    return file_paths


# this test ensures the integration tests fail correctly
def test_raise_failure_flow(pytestconfig) -> None:
    test_cmd = (
        f"{_python()} flows/raise_failure_flow.py --datastore=s3 kfp run "
        f"--wait-for-completion --workflow-timeout 1800 "
        f"--max-parallelism 3 --experiment metaflow_test --tag test_t1 "
    )
    if pytestconfig.getoption("image"):
        test_cmd += (
            f"--no-s3-code-package --base-image {pytestconfig.getoption('image')}"
        )

    run_and_wait_process = run(
        test_cmd,
        universal_newlines=True,
        stdout=PIPE,
        shell=True,
    )
    # this ensures the integration testing framework correctly catches a failing flow
    # and reports the error
    assert run_and_wait_process.returncode == 1

    def remove_prefix(text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text

    # prior_runs = list(Flow('RaiseErrorFlow'))
    all_flows = list(Metaflow())
    print("all_flows: ", all_flows)
    raise_error_flow_runs = all_flows['RaiseErrorFlow']
    print("prior runs: ", raise_error_flow_runs)
    # get the most recent run
    # the metadata service should grab the previous run in time because we wait for completion
    latest_run = raise_error_flow_runs[0]
    print("latest_run: ", latest_run)
    pathspec = latest_run.pathspec
    print("pathspec: ", pathspec)
    run_id = remove_prefix(pathspec, 'RaiseErrorFlow/')
    print("run_id: ", run_id)

    pulling_logs_cmd = (
        f"{_python()} flows/raise_failure_flow.py --datastore=s3 logs "
        f"{run_id}/error_step "
        f"--experiment metaflow_test --tag test_t1 "
    )

    print("Pulling log command: ", pulling_logs_cmd)

    pulling_logs_process = run(
        pulling_logs_cmd,
        universal_newlines=True,
        stdout=PIPE,
        shell=True,
    )
    # ensure we can pull logs of steps in failure
    assert pulling_logs_process.returncode == 0

    return


# @pytest.mark.parametrize("flow_file_path", obtain_flow_file_paths("flows"))
# def test_flows(pytestconfig, flow_file_path: str) -> None:
#     full_path = join("flows", flow_file_path)
#     # In the process below, stdout=PIPE because we only want to capture stdout.
#     # The reason is that the click echo function prints to stderr, and contains
#     # the main logs (run link, graph validation, package uploading, etc). We
#     # want to ensure these logs are visible to users and not captured.
#     # We use the print function in kfp_cli.py to print a magic token containing the
#     # run id and capture this to correctly test logging. See the
#     # `check_valid_logs_process` process.

#     test_cmd = (
#         f"{_python()} {full_path} --datastore=s3 kfp run "
#         f"--wait-for-completion --workflow-timeout 1800 "
#         f"--max-parallelism 3 --experiment metaflow_test --tag test_t1 "
#     )
#     if pytestconfig.getoption("image"):
#         test_cmd += (
#             f"--no-s3-code-package --base-image {pytestconfig.getoption('image')}"
#         )

#     run_and_wait_process = run(
#         test_cmd,
#         universal_newlines=True,
#         stdout=PIPE,
#         shell=True,
#     )
#     assert run_and_wait_process.returncode == 0

#     return
