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

    for check in results["policyValidationResults"][0]["ruleResults"]:
        print(f"{check['identifier']}: {check['name']}")
        check_id = fix_issue(check, template)
        all_checks.append(check_id)

    print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks.sort()
    print(", ".join(all_checks))

    name = chart_folder + "_fixed"
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

        resource_path = check["occurrencesDetails"][0]["kind"] + "/" + \
                        check["occurrencesDetails"][0]["metadataName"]

        obj_path = check["occurrencesDetails"][0]["failureLocations"][0]["schemaPath"]
        # Remove characters after the first digit
        for idx, value in enumerate(obj_path):
            if value.isdigit():
                obj_path = obj_path[:idx+1]
                break

        paths = {
            "resource_path": resource_path,
            "obj_path": obj_path
        }

        fix_template.set_template(template, check_id, paths)
        return check_id

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
        "CONTAINERS_INCORRECT_INITIALDELAYSECONDS_VALUE": "",
        "CONTAINERS_INCORRECT_PERIODSECONDS_VALUE": "",
        "CONTAINERS_INCORRECT_TIMEOUTSECONDS_VALUE": "",
        "CONTAINERS_INCORRECT_SUCCESSTHRESHOLD_VALUE": "",
        "CONTAINERS_INCORRECT_FAILURETHRESHOLD_VALUE": "",
        "CONTAINERS_MISSING_PRESTOP_KEY": "",
        "WORKLOAD_INVALID_LABELS_VALUE": "",
        "WORKLOAD_INCORRECT_RESTARTPOLICY_VALUE_ALWAYS": "",
        "DEPLOYMENT_INCORRECT_REPLICAS_VALUE": "",
        "WORKLOAD_MISSING_LABEL_OWNER_VALUE": "",
        "DEPLOYMENT_MISSING_LABEL_ENV_VALUE": "",
        "CRONJOB_INVALID_SCHEDULE_VALUE": "",
        "CRONJOB_MISSING_STARTINGDEADLINESECOND_KEY": "",
        "CRONJOB_MISSING_CONCURRENCYPOLICY_KEY": "",
        "INGRESS_INCORRECT_HOST_VALUE_PERMISSIVE": "",
        "SERVICE_INCORRECT_TYPE_VALUE_NODEPORT": "",
        "CONTAINERS_INCORRECT_RUNASUSER_VALUE_LOWUID": "check_13",
        "CONTAINERS_INCORRECT_KEY_HOSTPORT": "check_29",
        "CONTAINER_CVE2021_25741_INCORRECT_SUBPATH_KEY": "check_50",
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
