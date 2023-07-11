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
import checkov_fix_chart
import datree_fix_chart
import kics_fix_chart
import kubelinter_fix_chart
import kubeaudit_fix_chart
import kubescape_fix_chart
import terrascan_fix_chart


def count_checks(result_path: str, tool: str) -> list:
    """
    Count the checks from a tool JSON result file.

    Args:
        result_path (str): The path to the JSON file to parse.
        tool (str): The tool to count the checks for.

    Returns:
        int: The number of checks.
    """

    if tool == "kubeaudit":
        # Convert result to a valid JSON
        with open(result_path, 'r', encoding="utf-8") as file:
            data = file.read()

        # If data does not begin with '{"checks": [', then it is not a valid JSON
        if not data.startswith('{"checks": ['):
            # Add '{"checks": [' at the beginning of data
            data = '{"checks": [' + data
            # Substitue all '}' with '},' except the last one
            data = data.replace('}', '},', data.count('}') - 1)
            # Add ']}' at the end of data
            data = data + ']}'

            # Save data to a new JSON file
            with open(result_path, 'w', encoding="utf-8") as file:
                file.write(data)

    # Parse JSON result file
    with open(result_path, 'r', encoding="utf-8") as file:
        results = json.load(file)

    # List of all checks
    all_checks = []

    if tool == "checkov":
        if results and "results" in results:
            for check in results["results"]["failed_checks"]:
                my_lookup = checkov_fix_chart.LookupClass()
                check_id = my_lookup.get_value(check["check_id"])
                all_checks.append(check_id)

    elif tool == "datree":
        if results and "policyValidationResults" in results:
            for check in results["policyValidationResults"][0]["ruleResults"]:
                for _ in check["occurrencesDetails"]:
                    my_lookup = datree_fix_chart.LookupClass()
                    check_id = my_lookup.get_value(check["identifier"])
                    all_checks.append(check_id)

    elif tool == "kics":
        if results and "queries" in results:
            for check in results["queries"]:
                for _ in check["files"]:

                    # IGNORE PASSWORDS AND SECRETS POLICIES
                    if check["query_id"] == "487f4be7-3fd9-4506-a07a-eae252180c08":
                        continue

                    my_lookup = kics_fix_chart.LookupClass()
                    check_id = my_lookup.get_value(check["query_id"])
                    all_checks.append(check_id)

    elif tool == "kubelinter":
        if results and "Reports" in results:
            if results["Reports"]:
                for check in results["Reports"]:
                    my_lookup = kubelinter_fix_chart.LookupClass()
                    check_id = my_lookup.get_value(check["Check"])
                    all_checks.append(check_id)

    elif tool == "kubeaudit":
        if results and "checks" in results:
            for check in results["checks"]:
                my_lookup = kubeaudit_fix_chart.LookupClass()
                check_id = my_lookup.get_value(check["AuditResultName"])
                all_checks.append(check_id)

    elif tool == "kubescape":
        if results and "results" in results:
            for resource in results["results"]:
                for control in resource["controls"]:
                    if control["status"]["status"] == "failed":
                        for rule in control["rules"]:
                            if "paths" in rule:
                                for _ in rule["paths"]:
                                    my_lookup = kubescape_fix_chart.LookupClass()
                                    check_id = my_lookup.get_value(control["controlID"])
                                    all_checks.append(check_id)
                            else:
                                my_lookup = kubescape_fix_chart.LookupClass()
                                check_id = my_lookup.get_value(control["controlID"])
                                all_checks.append(check_id)

    elif tool == "terrascan":
        if results and "runs" in results:
            for run in results["runs"]:
                for check in run["results"]:
                    my_lookup = terrascan_fix_chart.LookupClass()
                    check_id = my_lookup.get_value(check['ruleId'])
                    all_checks.append(check_id)


    # IGNORE IMAGE TAG/DIGEST POLICIES
    all_checks = list(filter(("check_0").__ne__, all_checks))
    all_checks = list(filter(("check_9").__ne__, all_checks))
    ##################################


    # Print all found checks
    all_checks = [str(x) for x in all_checks if x is not None]
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))

    return all_checks
