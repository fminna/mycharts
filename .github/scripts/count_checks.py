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
                if check_id is None:
                    check_id = check["check_id"]
                all_checks.append(check_id)

    elif tool == "datree":
        if results and "policyValidationResults" in results:
            if results["policyValidationResults"] and \
                 "ruleResults" in results["policyValidationResults"][0]:
                for check in results["policyValidationResults"][0]["ruleResults"]:
                    for _ in check["occurrencesDetails"]:
                        my_lookup = datree_fix_chart.LookupClass()
                        check_id = my_lookup.get_value(check["identifier"])
                        if check_id is None:
                            check_id = check["identifier"]
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
                    if check_id is None:
                        check_id = check["query_id"]
                    all_checks.append(check_id)

    elif tool == "kubelinter":
        if results and "Reports" in results:
            if results["Reports"]:
                for check in results["Reports"]:
                    my_lookup = kubelinter_fix_chart.LookupClass()
                    check_id = my_lookup.get_value(check["Check"])

                    # Multi-check Kubelinter IDs
                    if check["Check"] == "unset-memory-requirements":
                        check_id = "check_1, check_2"
                    elif check["Check"] == "unset-cpu-requirements":
                        check_id = "check_4, check_5"
                    elif check["Check"] == "privilege-escalation-container":
                        check_id = "check_22, check_21, check_34"

                    # If the check is not yet implemented, append original ID
                    if check_id is None:
                        check_id = check["Check"]
                    all_checks.append(check_id)

    elif tool == "kubeaudit":
        if results and "checks" in results:
            for check in results["checks"]:
                my_lookup = kubeaudit_fix_chart.LookupClass()
                check_id = my_lookup.get_value(check["AuditResultName"])

                # Multi-check Kubeaudit IDs
                if check["AuditResultName"] == "LimitsNotSet":
                    check_id = "check_2, check_5"

                # If the check is not yet implemented, append original ID
                if check_id is None:
                    check_id = check["AuditResultName"]
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

                                    # Multi-check Kubeescape IDs
                                    if control["controlID"] == "C-0050":
                                        check_id = "check_4, check_5"
                                    elif control["controlID"] == "C-0009":
                                        check_id = "check_2, check_5"
                                    elif control["controlID"] == "C-0055":
                                        check_id = "check_31, check_32, check_34"
                                    elif control["controlID"] == "C-0038":
                                        check_id = "check_10, check_11"
                                    elif control["controlID"] == "C-0086":
                                        check_id = "check_22, check_28, check_32, check_34"

                                    # Ignore Secrets policies
                                    elif control["controlID"] == "C-0012":
                                        continue
                                    # Ignore Admission Controller policies
                                    elif control["controlID"] == "C-0036":
                                        continue

                                    # If the check is not yet implemented, append original ID
                                    if check_id is None:
                                        check_id = control["controlID"]
                                    all_checks.append(check_id)
                            else:
                                my_lookup = kubescape_fix_chart.LookupClass()
                                check_id = my_lookup.get_value(control["controlID"])

                                # Multi-check Kubeescape IDs
                                if control["controlID"] == "C-0050":
                                    check_id = "check_4, check_5"
                                elif control["controlID"] == "C-0009":
                                    check_id = "check_2, check_5"
                                elif control["controlID"] == "C-0055":
                                    check_id = "check_31, check_32, check_34"
                                elif control["controlID"] == "C-0038":
                                    check_id = "check_10, check_11"
                                elif control["controlID"] == "C-0086":
                                    check_id = "check_22, check_28, check_32, check_34"

                                # Ignore Secrets policies
                                elif control["controlID"] == "C-0012":
                                    continue
                                # Ignore Admission Controller policies
                                elif control["controlID"] == "C-0036":
                                    continue

                                # If the check is not yet implemented, append original ID
                                if check_id is None:
                                    check_id = control["controlID"]
                                all_checks.append(check_id)

    elif tool == "terrascan":
        if results and "runs" in results:
            for run in results["runs"]:
                for check in run["results"]:
                    my_lookup = terrascan_fix_chart.LookupClass()
                    check_id = my_lookup.get_value(check['ruleId'])
                    if check_id is None:
                        check_id = check["ruleId"]
                    all_checks.append(check_id)


    # IGNORE IMAGE TAG/DIGEST POLICIES
    all_checks = list(filter(("check_0").__ne__, all_checks))
    all_checks = list(filter(("check_9").__ne__, all_checks))
    ##################################


    # Print all found checks
    all_checks = [str(x) for x in all_checks if x is not None]

    # Convert all_checks to string
    # Needed to convert multi-check elements (e.g., "check_1, check_2")
    all_checks = ", ".join(all_checks)

    # Convert all checks back to list
    all_checks = all_checks.split(", ")
    all_checks.sort()

    # Print info
    # print(f"Total number of checks: {len(all_checks)}")
    # print(", ".join(all_checks))

    # For check_ from 0 to 66 (i.e., check_0, check_1, ..., check_66), print the
    # occurrences of each check in all_checks, all in one line
    print(len(all_checks), end=" ")
    for i in range(0, 67):
        print(f"{all_checks.count(f'check_{i}')}", end=" ")

    return all_checks
