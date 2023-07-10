# Copyright 2023 AssureMOSS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" This script implements the main function.
"""

import sys
import os
import json
import argparse
import checkov_fix_chart
import datree_fix_chart
import kics_fix_chart
import kubelinter_fix_chart
import kubeaudit_fix_chart
import kubescape_fix_chart
import terrascan_fix_chart
import add_functionalities
import generate_docker_run
import count_checks


# Define the argument parser
parser = argparse.ArgumentParser(description='Script to fix Helm Charts based on results from \
                                 security tools and add required functionalities.')

# Add the --check argument
parser.add_argument('--check', action='store_true', help='Fix the chart based on the results \
                                                        of a tool.')
# Add the --add-func argument
parser.add_argument('--add-func', action='store_true', help='Add required functionality to \
                                                            the chart.')

# Add the --add-func argument
parser.add_argument('--docker-run', action='store_true', help='Generate Docker run command')

# Add the --add-func argument
parser.add_argument('--count-checks', action='store_true', help='Count final checks')

# Parse the arguments
args = parser.parse_args()


def check_for_failures(json_path: str, json_field: str) -> bool :
    """Parses a JSON file and checks whether there are any failed tests.
    
    Args:
        json_path (str): The path to the JSON file to parse.
        json_field (str): The field to check for failures. Format: key1/key2/...
        
    Returns:
        bool: True if there are any failed tests, False otherwise.
    """

    # Load the JSON file
    with open(json_path, 'r', encoding="utf-8") as file:
        results = json.load(file)

    # Get the "failed" count from the summary
    keys = json_field.split("/")
    failed_count = results

    for key in keys:
        failed_count = failed_count[key]

    # Check if there are any failed tests
    return failed_count > 0


def main():
    """ The main function.
    """

    # Get chart_folder from ENV
    # For local testing on macOS, add env variables to ~/.zshrc
    chart_folder = os.environ.get("chart_folder")
    tool = os.environ.get("first_tool")

    # Fix the chart based on the results of a tool
    if args.check:
        # Get ENV variables
        iteration = os.environ.get("iteration")
        result_path = f"results_{iteration}.json"

        if iteration == "1":
            chart_folder = f"templates/{chart_folder}"
        elif iteration == "2" or iteration == "3":
            chart_folder = f"fixed_templates/{chart_folder}"

        # Check if there are any failed tests
        if tool == "checkov":
            if check_for_failures(result_path, "summary/failed"):
                # Iterate the failed checks
                checkov_fix_chart.iterate_checks(chart_folder, result_path)

        elif tool == "datree":
            if check_for_failures(result_path, "policySummary/totalRulesFailed"):
                # Iterate the failed checks
                datree_fix_chart.iterate_checks(chart_folder, result_path)

        elif tool == "kics":
            if check_for_failures(result_path, "total_counter"):
                # Iterate the failed checks
                kics_fix_chart.iterate_checks(chart_folder, result_path)

        elif tool == "kubelinter":
            # check if result["Summary"]["ChecksStatus"] == "Failed"
            kubelinter_fix_chart.iterate_checks(chart_folder, result_path)

        elif tool == "kubeaudit":
            # JSON format is not valid; failed checks are only given by file lines
            kubeaudit_fix_chart.iterate_checks(chart_folder, result_path)

        elif tool == "kubescape":
            # "resourcesSeverityCounters" + "controlsSeverityCounters" + "ResourceCounters"
            kubescape_fix_chart.iterate_checks(chart_folder, result_path)

        elif tool == "terrascan":
            # "runs" + "results"
            terrascan_fix_chart.iterate_checks(chart_folder, result_path)

        else:
            print("Tool not supported. Exiting...")
            sys.exit(1)

    # Add required functionality to the chart
    elif args.add_func:
        json_path = f"functionality_profiles/{chart_folder}/{chart_folder}_functionality.json"
        add_functionalities.iterate_functionalities(chart_folder, json_path, tool)

    # Generate Docker run command from YAML template
    elif args.docker_run:
        resource_path = os.environ.get("resource_path")
        obj_path = os.environ.get("obj_path")
        generate_docker_run.get_docker_run_cmd(chart_folder, resource_path, obj_path)

    # Count final checks
    elif args.count_checks:
        # Get ENV variables
        iteration = os.environ.get("iteration")
        tool = os.environ.get("second_tool")
        count_checks.count_checks(result_path, tool)

    else:
        print("No arguments passed. Exiting...")
        sys.exit(1)


if __name__ == "__main__":
    main()
