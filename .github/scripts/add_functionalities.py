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


def get_original_uid(template: dict, resource_path: str, obj_path: str) -> str:
    """ Gets the original UID from the original template.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the original template.
        obj_path (str): The path of the object in the YAML document.

    Returns:
        str: The original UID.
    """

    uid = ""

    for document in template:
        if fix_template.check_resource_path(resource_path.split("/"), document):
            # Find the object
            keys = obj_path.split("/")
            obj = document

            for key in keys:
                if key:
                    if key.isdigit():
                        key = int(key)
                    obj = obj[key]

            if "securityContext" in obj:
                if  "runAsUser" in obj["securityContext"]:
                    uid = obj["securityContext"]["runAsUser"]

            if not uid:
                obj = document
                if "template" in obj:
                    obj = obj["spec"]["template"]["spec"]
                    if "securityContext" in obj:
                        if  "runAsUser" in obj["securityContext"]:
                            uid = obj["securityContext"]["runAsUser"]

    return uid


def get_original_gid(template: dict, resource_path: str, obj_path: str) -> str:
    """ Gets the original GID from the original template.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the original template.
        obj_path (str): The path of the object in the YAML document.

    Returns:
        str: The original GID.
    """

    gid = ""

    for document in template:
        if fix_template.check_resource_path(resource_path.split("/"), document):
            # Find the object
            keys = obj_path.split("/")
            obj = document

            for key in keys:
                if key:
                    if key.isdigit():
                        key = int(key)
                    obj = obj[key]

            if "securityContext" in obj:
                if  "fsGroup" in obj["securityContext"]:
                    gid = obj["securityContext"]["fsGroup"]

            if not gid:
                obj = document
                if "template" in obj:
                    obj = obj["spec"]["template"]["spec"]
                    if "securityContext" in obj:
                        if  "runAsUser" in obj["securityContext"]:
                            gid = obj["securityContext"]["runAsUser"]

    return gid


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
    # print("Starting to add chart's functionalities ...\n")

    all_checks = []

    for pod in results["pods"]:
        for container in pod["containers"]:
            aux_checks = add_functionality(container, template, chart_folder)
            all_checks.extend(aux_checks)

    # print("\nAll functionalities added!")
    all_checks = [x for x in all_checks if x is not None]
    all_checks.sort()
    # print(f"Total number of checks: {len(all_checks)}")
    # print(", ".join(all_checks))

    # For check_ from 0 to 66 (i.e., check_0, check_1, ..., check_66), print the
    # occurrences of each check in all_checks, all in one line
    for i in range(0, 67):
        print(f"{all_checks.count(f'check_{i}')}", end=" ")

    name = f"functionality_templates/{chart_folder}_func"
    fix_template.save_yaml_template(template, name)


def add_functionality(container: str, template: dict, chart_folder: str) -> list:
    """Adds the required functionalities to the object.

    Args:
        container (str): The K8s container to add functionalities to.
        template (dict): The parsed YAML template.
        chart_folder (str): The name of the Helm Chart to fix.

    Returns:
        list: The list of all checks.
    """

    # List of all checks
    all_checks = []

    # Iterate functionalities
    for check_id in container["functionalities"].keys():

        check = container["functionalities"][check_id]
        # issue = f"{check_id}: {check['description']}"
        # print(issue)

        # Capabilities
        if check_id == "check_34":
            # Check if any capability needs to be added --- "add" list not empty
            if check['add']:
                all_checks.append(check_id)
                fix_template.set_template(template, check_id, check)

        # Low UID
        elif check_id == "check_13":
            # Retrieve UID from original template
            original_template = fix_template.parse_yaml_template(f"templates/{chart_folder}")
            uid = get_original_uid(original_template, check["resource_path"], check["obj_path"])
            if not uid:
                uid = 1001
            all_checks.append(check_id)
            check["value"] = uid
            fix_template.set_template(template, check_id, check)

        # Low GID
        elif check_id == "check_14":

            # For now, we do not change anything in the functionality template, because
            # no tool checks the GID, thus is never modified from the original template.

            # Retrieve GID from original template
            # original_template = fix_template.parse_yaml_template(f"templates/{chart_folder}")
            # gid = get_original_gid(original_template, check["resource_path"], check["obj_path"])

            all_checks.append(check_id)

            # check["value"] = gid
            # fix_template.set_template(template, check_id, check)

        # Memory request
        elif check_id == "check_1":
            all_checks.append(check_id)
            fix_template.set_template(template, check_id, check)

        # Memory limit
        elif check_id == "check_2":
            all_checks.append(check_id)
            fix_template.set_template(template, check_id, check)

        # CPU request
        elif check_id == "check_4":
            all_checks.append(check_id)
            fix_template.set_template(template, check_id, check)

        # CPU limit
        elif check_id == "check_5":
            all_checks.append(check_id)
            fix_template.set_template(template, check_id, check)

        # Docker Socket
        elif check_id == "check_15":
            all_checks.append(check_id)
            # fix_template.set_template(template, check_id, check)

        # RunAsNonRoot, Read-only FS,
        elif check_id == "check_27" or check_id == "check_28":
            all_checks.append(check_id)
            check["value"] = False
            fix_template.set_template(template, check_id, check)

        # hostPath
        elif check_id == "check_47" and check['value'] is False:
            all_checks.append(check_id)
            for host_path in check["hostPaths"]:
                check["value"] = host_path
                fix_template.set_template(template, check_id, check)

        # Non-default values
        elif check['value'] is False:
            all_checks.append(check_id)
            check["value"] = True
            fix_template.set_template(template, check_id, check)

    return all_checks
