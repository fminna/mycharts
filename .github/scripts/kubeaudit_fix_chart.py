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

""" Fixing Helm Chart based on Kubeaudit results.
"""

from typing import Callable
import json
import fix_template
from kubelinter_fix_chart import get_container_path


def iterate_checks(chart_folder: str, json_path: str) -> None:
    """Parses JSON data and iterates "AuditResultName" keys.

    Args:
        chart_folder (str): The name of the chart to fix.
        json_path (str): The path to the JSON file to parse.
    """

    # Convert result to a valid JSON
    with open(json_path, 'r', encoding="utf-8") as file:
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
            with open(json_path, 'w', encoding="utf-8") as file:
                file.write(data)

    # Load the JSON file
    with open(json_path, 'r', encoding="utf-8") as file:
        results = json.load(file)

    template = fix_template.parse_yaml_template(chart_folder)

    # List of all checks
    all_checks = []

    print("Starting to fix chart's issues ...\n")

    for check in results["checks"]:
        print(f"{check['AuditResultName']}: {check['msg']}")
        check_id = fix_issue(check, template)
        all_checks.append(check_id)

    print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks = list(dict.fromkeys(all_checks))
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))

    name = f"{chart_folder}_kubeaudit_fixed"
    fix_template.save_yaml_template(template, name)


def fix_issue(check: str, template: dict) -> str:
    """Fixes an issue based on the Kubeaudit check ID.

    Source: https://github.com/Shopify/kubeaudit#global-flags

    Args:
        check (dict): The dictionary representing a check to fix.
        template (dict): The parsed YAML template.
    """

    # Get function from lookup dictionary
    my_lookup = LookupClass()
    check_id = my_lookup.get_value(check["AuditResultName"])

    # Check if the function exists and call it
    if check_id is not None:

        # Resource path (e.g., Pod/default/name)
        resource_path = check["ResourceKind"] + "/" + check["ResourceNamespace"] + \
                        "/" + check["ResourceName"]

        # spec/template/spec/containers/0/
        obj_path = ""

        if "Container" in check:
            # Find container path based on container name
            obj_path = get_container_path(template, resource_path, check["Container"])

        if check["AuditResultName"] == "AppArmorAnnotationMissing":
            obj_path = check["Container"]

        paths = {
            "resource_path": resource_path,
            "obj_path": obj_path
        }

        if check["AuditResultName"] == "":
            fix_template.set_template(template, "check_2", paths)
            fix_template.set_template(template, "check_5", paths)
            return "check_2", "check_5"

        else:
            fix_template.set_template(template, check_id, paths)
            return check_id

    else:
        print("No fix found for check ID: " + check["AuditResultName"])
        return None


class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "AppArmorAnnotationMissing": "check_32", 
        "CapabilityOrSecurityContextMissing": "check_34", 
        "LimitsCPUNotSet": "check_5", 
        "LimitsMemoryNotSet": "check_2", 
        "LimitsNotSet": "check_1",
        "AllowPrivilegeEscalationNil": "check_22", 
        "PrivilegedNil": "check_21", 
        "ReadOnlyRootFilesystemNil": "check_27", 
        "SeccompProfileMissing": "check_31",
        "AutomountServiceAccountTokenTrueAndDefaultSA": "check_35",
        "ImageTagMissing": "check_0",
        "RunAsNonRootPSCNilCSCNil": "check_28",
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
