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

""" Adding required functionalities to Helm Chart.
"""

import json
import fix_template


def iterate_functionalities(chart_folder: str, json_path: str, tool: str) -> None:
    """Parses JSON data and iterates "functionality_id" keys.

    Args:
        chart_folder (str): The name of the Helm Chart to fix. 
        json_path (str): The path to the JSON file to parse.
        tool (str): The name of the tool used to scan the Helm Chart.
    """

    # Load the JSON file
    with open(json_path, 'r', encoding="utf-8") as file:
        results = json.load(file)

    name = f"fixed_templates/{chart_folder}_{tool}_fixed"
    template = fix_template.parse_yaml_template(name)
    print("Starting to add chart's functionalities ...\n")

    for pod in results["pods"]:
        for container in pod["containers"]:
            add_functionality(container, template)

    print("\nAll functionalities added!")
    name = f"functionality_templates/{chart_folder}_func"
    fix_template.save_yaml_template(template, name)


def add_functionality(container: str, template: dict) -> None:
    """Adds the required functionalities to the object.

    Args:
        container (str): The K8s container to add functionalities to.
        template (dict): The parsed YAML template.
    """

    # List of all checks
    all_checks = []

    # Iterate functionalities
    for check_id in container["functionalities"]:

        if check_id == "check_34":
            # Check if any capability needs to be added --- "add" list not empty
            if container['functionalities'][check_id]['add'] is not None:
                issue = f"{check_id}: {container['functionalities'][check_id]['description']}"
                print(issue)
                all_checks.append(check_id)

                fix_template.set_template(template, check_id, container["functionalities"][check_id])

        
        else:
            print(container['functionalities'][check_id])
        
            if container['functionalities'][check_id]['value'] == "true":
                continue

            else:
                issue = f"{check_id}: {container['functionalities'][check_id]['description']}"
                print(issue)
                all_checks.append(check_id)

                fix_template.set_template(template, check_id, container["functionalities"][check_id])

    print("\nAll functionalities added!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks = list(dict.fromkeys(all_checks))
    all_checks.sort()
    print(f"Total number of functionalities: {len(all_checks)}")
    print(", ".join(all_checks))
