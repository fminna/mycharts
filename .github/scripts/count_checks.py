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

""" This script counts the checks from a tool JSON result file.
"""

import json


def count_checks(result_path: str, tool: str) -> list:
    """
    Count the checks from a tool JSON result file.

    Args:
        result_path (str): The path to the JSON file to parse.
        tool (str): The tool to count the checks for.

    Returns:
        int: The number of checks.
    """

    # Parse JSON result file
    with open(result_path, 'r', encoding="utf-8") as file:
        results = json.load(file)




    print(result_path)
    print(results)




    # List of all checks
    all_checks = []

    if tool == "checkov":
        for check in results["results"]["failed_checks"]:
            all_checks.append(check['check_id'])

    elif tool == "datree":
        for check in results["policyValidationResults"][0]["ruleResults"]:
            for _ in check["occurrencesDetails"]:
                all_checks.append(check['identifier'])

    elif tool == "kics":
        for check in results["queries"]:
            for _ in check["files"]:
                all_checks.append(check['query_id'])

    elif tool == "kubelinter":
        for check in results["Reports"]:
            all_checks.append(check['Check'])

    elif tool == "kubeaudit":
        for check in results["checks"]:
            all_checks.append(check['AuditResultName'])

    elif tool == "kubescape":
        for resource in results["results"]:
            for control in resource["controls"]:
                if control["status"]["status"] == "failed":
                    for rule in control["rules"]:
                        for _ in rule["paths"]:
                            all_checks.append(control['controlID'])

    elif tool == "terrascan":
        for run in results["runs"]:
            for check in run["results"]:
                all_checks.append(check['ruleId'])

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))

    return all_checks
