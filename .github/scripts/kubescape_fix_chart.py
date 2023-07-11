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

""" Fixing Helm Chart based on Kubescape results.
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

    for resource in results["results"]:
        # Extract current resource path
        resource_path = resource["resourceID"].split("/")
        resource_path = resource_path[-2] + "/" + resource_path[-3] + "/" + resource_path[-1]

        # Extract only failed checks "status": { "status": "failed" }
        for control in resource["controls"]:
            if control["status"]["status"] == "failed":

                print(f"{control['controlID']}: {control['name']}")
                check_id = fix_issue(control, resource_path, template)

                for rule in control["rules"]:
                    if "paths" in rule:
                        for _ in rule["paths"]:
                            all_checks.append(check_id)
                    else:
                        all_checks.append(check_id)

    print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))

    name = f"fixed_{chart_folder}_kubescape_fixed"
    fix_template.save_yaml_template(template, name)


def fix_issue(control: str, resource_path: str, template: dict) -> str:
    """Fixes an issue based on the Kubescape check ID.

    Source: https://hub.armosec.io/docs/controls

    Args:
        control (dict): The dictionary representing a check to fix.
        resource_path (str): The path to the resource to fix.
        template (dict): The parsed YAML template.
    """

    # Get function from lookup dictionary
    my_lookup = LookupClass()
    check_id = my_lookup.get_value(control["controlID"])

    # Check if the function exists and call it
    if check_id is not None:
        for rule in control["rules"]:

            if control["controlID"] == "C-0030":
                # then there is no "paths"
                paths = {
                        "resource_path": resource_path,
                        "obj_path": ""
                }

            else:
                for path in rule["paths"]:
                    obj_path = path["fixPath"]["path"]

                    # Convert obj_path to the correct format
                    # 'spec.template.spec.containers[0].securityContext.capabilities.drop[0]'
                    if "containers" in obj_path:

                        # find the index of the first ']' occurrence
                        index = obj_path.find("]")
                        obj_path = obj_path[:index]
                        obj_path = obj_path.replace("[", "/")

                    # Resource labels
                    elif control["controlID"] == "C-0076" or control["controlID"] == "C-0077":
                        obj_path = ""

                    # 'spec.template.spec.securityContext.allowPrivilegeEscalation'
                    # 'spec.template.spec.automountServiceAccountToken'
                    else:
                        obj_path = obj_path.split(".")[:-2]
                        obj_path = ".".join(obj_path)

                    obj_path = obj_path.replace(".", "/")

                    paths = {
                        "resource_path": resource_path,
                        "obj_path": obj_path
                    }

            # Memory requests & limits
            if control["controlID"] == "C-0004":
                fix_template.set_template(template, "check_1", paths)
                fix_template.set_template(template, "check_2", paths)
                return "check_1, check_2"

            # CPU requests & limits
            elif control["controlID"] == "C-0050":
                fix_template.set_template(template, "check_4", paths)
                fix_template.set_template(template, "check_5", paths)
                return "check_4, check_5"

            # Memory & CPU limits
            elif control["controlID"] == "C-0009":
                fix_template.set_template(template, "check_2", paths)
                fix_template.set_template(template, "check_5", paths)
                return "check_2, check_5"

            # Linux hardening - AppArmor/Seccomp/SELinux/Capabilities
            elif control["controlID"] == "C-0055":
                fix_template.set_template(template, "check_31", paths)
                fix_template.set_template(template, "check_32", paths)
                # SeLinux ?
                fix_template.set_template(template, "check_34", paths)
                return "check_31, check_32, check_34"

            # Host PID/IPC privileges
            elif control["controlID"] == "C-0038":
                fix_template.set_template(template, "check_10", paths)
                fix_template.set_template(template, "check_11", paths)
                return "check_10, check_11"

            else:
                fix_template.set_template(template, check_id, paths)
                return check_id

    else:
        print("No fix found for check ID: " + control["controlID"])
        return None


class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "C-0075": "check_0",
        "C-0004": "check_1",
        "C-0009": "check_4",
        "C-0050": "check_4",
        "C-0056": "check_7",
        "C-0018": "check_8",
        "C-0038": "check_10",
        "C-0041": "check_12",
        "C-0074": "check_15",
        "C-0057": "check_21",
        "C-0016": "check_22",
        "C-0086": "check_22",
        "C-0046": "check_23",
        "C-0061": "check_26",
        "C-0017": "check_27",
        "C-0013": "check_28",
        "C-0044": "check_29",
        "C-0045": "check_29",
        "C-0055": "check_30",
        "C-0034": "check_35",
        "C-0014": "check_38",
        "C-0076": "check_43",
        "C-0077": "check_43",
        "C-0048": "check_46",
        "C-0030": "check_40",
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
