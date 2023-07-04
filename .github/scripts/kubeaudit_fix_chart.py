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
    print("Starting to fix chart's issues ...\n")

    for check in results["checks"]:
        issue = check["AuditResultName"] + ": " + check["msg"]
        print(issue)
        fix_issue(check, template)

    print("\nAll issues fixed!")
    name = chart_folder + "_fixed"
    fix_template.save_yaml_template(template, name)


def get_resource_dict(template: dict, resource_path: str) -> dict:
    """Returns a dictionary of a K8s resource.
    
    Args:
        template (dict): The parsed YAML template.

    Returns:
        dict: The dictionary of the resource.
    """

    resource_path = resource_path.split("/")

    for document in template:
        if document["kind"] == resource_path[0] and \
           document["metadata"]["namespace"] == resource_path[1] and \
           document["metadata"]["name"] == resource_path[2]:
            return document

    return {}


def fix_issue(check: str, template: dict) -> None:
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

        # Get YAML document of the resource
        obj = get_resource_dict(template, resource_path)

        print(obj)

        # Set the object path based on check ID
        obj_path = ""

        check = {
            "resource_path": resource_path,
            "obj_path": obj_path
        }

        fix_template.set_template(template, check_id, check)

    else:
        print("No fix found for check ID: " + check["AuditResultName"])


# We ignore checks CKV_K8S_1-CKV_K8S_8 because they refer to
# Pod Security Policies, which are deprecated in Kubernetes 1.21.

class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "AppArmorAnnotationMissing": "check_32", 
        "CapabilityOrSecurityContextMissing": "check_34", 
        "LimitsCPUNotSet": "check_5", 
        "LimitsMemoryNotSet": "check_2", 
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
