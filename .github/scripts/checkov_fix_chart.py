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

""" Fixing Helm Chart based on checkov results.
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

    for check in results["results"]["failed_checks"]:
        print(f"{check['check_id']}: {check['check_name']}")
        check_id = fix_issue(check, template)
        all_checks.append(check_id)

    print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks = list(dict.fromkeys(all_checks))
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))

    name = f"fixed_{chart_folder}_checkov_fixed"
    fix_template.save_yaml_template(template, name)


def fix_issue(check: str, template: dict) -> str:
    """Fixes an issue based on the checkov check ID.

    Source: https://www.checkov.io/5.Policy%20Index/kubernetes.html

    Args:
        check (dict): The dictionary representing a check to fix.
        template (dict): The parsed YAML template.
    """

    # Get function from lookup dictionary
    my_lookup = LookupClass()
    check_id = my_lookup.get_value(check["check_id"])

    # Check if the function exists and call it
    if check_id is not None:

        # Resource path (e.g., Pod/default/name)
        resource_path = check["resource"].replace(".", "/")

        # Object path
        obj_path = ""
        # If specified, get the object path (e.g., spec/containers/0)
        if check["check_result"]["evaluated_keys"]:
            obj_path = check["check_result"]["evaluated_keys"][0]
            index = obj_path.rfind("]/")
            if index != -1:
                obj_path = obj_path[:index+2]
            obj_path = obj_path.replace("[", "").replace("]", "")

        paths = {
            "resource_path": resource_path,
            "obj_path": obj_path
        }

        fix_template.set_template(template, check_id, paths)
        return check_id

    else:
        print("No fix found for check ID: " + check["check_id"])
        return None


# We ignore checks CKV_K8S_1-CKV_K8S_8 because they refer to
# Pod Security Policies, which are deprecated in Kubernetes 1.21.

class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "CKV_K8S_8": "check_7", 
        "CKV_K8S_9": "check_8", 
        "CKV_K8S_10": "check_4", 
        "CKV_K8S_11": "check_5", 
        "CKV_K8S_12": "check_1", 
        "CKV_K8S_13": "check_2", 
        "CKV_K8S_14": "check_0", 
        "CKV_K8S_15": "check_25", 
        "CKV_K8S_16": "check_21", 
        "CKV_K8S_17": "check_10", 
        "CKV_K8S_18": "check_11", 
        "CKV_K8S_19": "check_12",
        "CKV_K8S_20": "check_22", 
        "CKV_K8S_21": "check_26", 
        "CKV_K8S_22": "check_27", 
        "CKV_K8S_23": "check_28", 
        "CKV_K8S_25": "check_34", 
        "CKV_K8S_28": "check_34", 
        "CKV_K8S_29": "check_30", 
        "CKV_K8S_31": "check_31", 
        "CKV_K8S_35": "check_33", 
        "CKV_K8S_37": "check_34", 
        "CKV_K8S_38": "check_35", 
        "CKV_K8S_39": "check_34", 
        "CKV_K8S_40": "check_13", 
        "CKV_K8S_41": "check_35", 
        "CKV_K8S_42": "check_35", 
        "CKV_K8S_43": "check_9", 
        "CKV2_K8S_6": "check_40"
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
