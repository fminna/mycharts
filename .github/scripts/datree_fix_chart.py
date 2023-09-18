# Copyright 2023
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

""" Fixing Helm Chart based on Datree results
"""

from typing import Callable
import json
import fix_template


def iterate_checks(chart_folder: str, json_path: str) -> None:
    """Parses JSON data and iterates "check_id" keys.

    Args:
        chart_folder (str): The name of the chart to fix.
        json_path (str): The path to the JSON file to parse.
    """

    # Load the JSON file
    with open(json_path, 'r', encoding="utf-8") as file:
        results = json.load(file)

    template = fix_template.parse_yaml_template(chart_folder)

    # List of all checks
    all_checks = []

    print("Starting to fix chart's issues ...\n")

    if "policyValidationResults" and results["policyValidationResults"] is not None:
        for check in results["policyValidationResults"][0]["ruleResults"]:
            print(f"{check['identifier']}: {check['name']}")
            check_id = fix_issue(check, template)

            for _ in check["occurrencesDetails"]:
                all_checks.append(check_id)

    print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks = ", ".join(all_checks)
    all_checks = all_checks.split(", ")
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))
    # For check_ from 0 to 66 (i.e., check_0, check_1, ..., check_66), print the
    # occurrences of each check in all_checks, all in one line
    # for i in range(0, 67):
    #     print(f"{all_checks.count(f'check_{i}')}", end=" ")

    name = f"fixed_{chart_folder}_datree_fixed"
    fix_template.save_yaml_template(template, name)


def fix_issue(check: str, template: dict) -> str:
    """Fixes a check based on the Datree check identifier.

    Source: https://hub.datree.io/built-in-rules

    Args:
        check (dict): The dictionary representing a check to fix.
        template (dict): The parsed YAML template.
    """

    # Get function from lookup dictionary
    my_lookup = LookupClass()
    check_id = my_lookup.get_value(check["identifier"])

    # Check if the function exists and call it
    if check_id is not None:
        check_list = [check_id]

        for occurrence in check["occurrencesDetails"]:
            # Get the resource path
            resource_path = f"{occurrence['kind']}/{occurrence['metadataName']}"

            for failure in occurrence["failureLocations"]:
                # Get the object path
                obj_path = failure["schemaPath"]

                if obj_path:

                    # If there is a number in the path, remove everything after it
                    # Example:
                    # /spec/template/spec/containers/0/securityContext/... -->
                    # /spec/template/spec/containers/0
                    if any(char.isdigit() for char in obj_path):
                        for idx, value in enumerate(obj_path):
                            if value.isdigit():
                                obj_path = obj_path[:idx+1]
                                break

                    else:
                        # Remove the last part of the path
                        # Example: /spec/template/spec/hostNetwork --> /spec/template/spec
                        obj_path = obj_path.rsplit('/', 1)[0]

                paths = {
                    "resource_path": resource_path,
                    "obj_path": obj_path
                }

                fix_template.set_template(template, check_id, paths)
                check_list.append(check_id)

        return ", ".join(check_list)

    else:
        print("No fix found for check ID: " + check["identifier"])
        return None


class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "CONTAINERS_MISSING_LIVENESSPROBE_KEY": "check_7",
        "CONTAINERS_MISSING_READINESSPROBE_KEY": "check_8",
        "CONTAINERS_MISSING_CPU_REQUEST_KEY": "check_4",
        "CONTAINERS_MISSING_CPU_LIMIT_KEY": "check_5",
        "CONTAINERS_MISSING_MEMORY_REQUEST_KEY": "check_1",
        "CONTAINERS_MISSING_MEMORY_LIMIT_KEY": "check_2",
        "CONTAINERS_MISSING_IMAGE_VALUE_VERSION": "check_0",
        "CONTAINERS_INCORRECT_PRIVILEGED_VALUE_TRUE": "check_21",
        "CONTAINERS_INCORRECT_HOSTPID_VALUE_TRUE": "check_10",
        "CONTAINERS_INCORRECT_HOSTIPC_VALUE_TRUE": "check_11",
        "CONTAINERS_INCORRECT_HOSTNETWORK_VALUE_TRUE": "check_12",
        "CONTAINERS_MISSING_KEY_ALLOWPRIVILEGEESCALATION": "check_22",
        "WORKLOAD_INCORRECT_NAMESPACE_VALUE_DEFAULT": "check_26",
        "CONTAINERS_INCORRECT_READONLYROOTFILESYSTEM_VALUE": "check_27",
        "CONTAINERS_INCORRECT_RUNASNONROOT_VALUE": "check_28",
        "CIS_MISSING_KEY_SECURITYCONTEXT": "check_30",
        "CONTAINERS_INCORRECT_SECCOMP_PROFILE": "check_31",
        "CIS_INVALID_VALUE_SECCOMP_PROFILE": "check_31",
        "CONTAINERS_INVALID_CAPABILITIES_VALUE": "check_23",
        "CIS_MISSING_VALUE_DROP_NET_RAW": "check_23",
        "CIS_INVALID_VALUE_AUTOMOUNTSERVICEACCOUNTTOKEN": "check_35",
        "SRVACC_INCORRECT_AUTOMOUNTSERVICEACCOUNTTOKEN_VALUE": "check_35",
        "CONTAINERS_MISSING_IMAGE_VALUE_DIGEST": "check_9",
        "CIS_INVALID_KEY_SECRETKEYREF_SECRETREF": "check_33",
        "DEPLOYMENT_INCORRECT_REPLICAS_VALUE": "check_45",
        "SERVICE_INCORRECT_TYPE_VALUE_NODEPORT": "check_56",
        "CONTAINERS_INCORRECT_RUNASUSER_VALUE_LOWUID": "check_13",
        "CONTAINERS_INCORRECT_KEY_HOSTPORT": "check_29",
        "CONTAINER_CVE2021_25741_INCORRECT_SUBPATH_KEY": "check_50",
        "CIS_INVALID_VERB_SECRETS": "check_54",
        "CONTAINERS_INCORRECT_RESOURCES_VERBS_VALUE": "check_54",
        "EKS_INVALID_CAPABILITIES_EKS": "check_34",
        "CIS_INVALID_VALUE_CREATE_POD": "check_54",
        "CIS_INVALID_WILDCARD_ROLE": "check_54",
        "CIS_INVALID_VALUE_BIND_IMPERSONATE_ESCALATE": "check_54",
        "CONTAINERS_INCORRECT_KEY_HOSTPATH": "check_47",
        "CIS_INVALID_ROLE_CLUSTER_ADMIN": "check_65",
        "INGRESS_INCORRECT_HOST_VALUE_PERMISSIVE": "check_66",
    }

    @classmethod
    def get_value(cls, key) -> Callable:
        """ Get the function to be called for each check.

        Args:
            key (str): The check number.
        """
        return cls._LOOKUP.get(key)

    @classmethod
    def print_value(cls, key) -> None:
        """ Print the function to be called for each check."""
        print(cls._LOOKUP.get(key))
