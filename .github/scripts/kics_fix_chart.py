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

""" Fixing Helm Chart based on KICS results
"""

from typing import Callable
import copy
import json
import re
import fix_template
import terrascan_fix_chart


def iterate_checks(chart_folder: str, json_path: str) -> None:
    """Parses JSON data and iterates "query_id" keys.

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

    # print("Starting to fix chart's issues ...\n")

    for check in results["queries"]:
        # print(f"{check['query_id']}: {check['query_name']}")

        # if check["query_id"] == "487f4be7-3fd9-4506-a07a-eae252180c08":
        #     remove_password(chart_folder, check["files"])

        check_id = fix_issue(check, template)

        for _ in check["files"]:
            all_checks.append(check_id)

    # print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks.sort()
    # print(f"Total number of checks: {len(all_checks)}")
    # print(", ".join(all_checks))
    # For check_ from 0 to 66 (i.e., check_0, check_1, ..., check_66), print the
    # occurrences of each check in all_checks, all in one line
    print(len(all_checks), end=" ")
    for i in range(0, 67):
        print(f"{all_checks.count(f'check_{i}')}", end=" ")

    name = f"fixed_{chart_folder}_kics_fixed"
    fix_template.save_yaml_template(template, name)


def find_resource_idx(template: dict, resource_path: str, obj_path: str, obj_name: str) -> str:
    """Finds the index of the resource in the YAML template.

    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the YAML template.
        obj_path (str): The path to the object in the YAML template.
        obj_name (str): The name of the resource.

    Returns:
        str: The index as a str of the resource in the YAML template.
    """

    resource_path = resource_path.split("/")

    for document in template:

        # Check if the document is not empty
        # Example: the document only contains a comment
        # ---
        # Source: metallb/charts/crds/templates/crds.yaml
        # ---
        if not document:
            continue

        elif document["kind"] == resource_path[0] and \
            document["metadata"]["name"] == resource_path[1]:

            # Find the object
            keys = obj_path.split("/")
            objects = document

            for key in keys:
                if key not in objects:
                    return ""
                objects = objects[key]

            for idx, obj in enumerate(objects):
                if obj["name"] == obj_name:
                    return str(idx)

    return ""


def fix_issue(check: str, template: dict) -> str:
    """Fixes a check based on the checkov check ID.

    Source: https://www.checkov.io/5.Policy%20Index/kubernetes.html

    Args:
        check (dict): The dictionary representing a check to fix.
        template (dict): The parsed YAML template.
    """

    # Get function from lookup dictionary
    my_lookup = LookupClass()
    check_id = my_lookup.get_value(check["query_id"])

    # Check if the function exists and call it
    if check_id is not None:
        for jdx, file in enumerate(check["files"]):

            resource_path = file["resource_type"] + "/" + \
                            file["resource_name"]
            obj_path = file["search_key"]

            no_path_checks = ["check_26", "check_36", "check_48", "check_49", "check_53", \
                              "check_56", "check_65", "check_13", "check_47", "check_15"]
            if check_id in no_path_checks:
                obj_path = ""

            elif check_id == "check_32":
                pattern = r"\{\{([^}]*)\}\}"
                matches = re.findall(pattern, file["expected_value"])
                obj_path = matches[-1]

            else:
                obj_path = obj_path.split("}}.")[1]

                obj_name = ""
                if ".name=" in obj_path:
                    obj_name = obj_path.split(".name=")[1]
                    obj_name = obj_name.replace("{{", "")
                    obj_name = obj_name.replace("}}", "")
                    if "." in obj_name:
                        obj_name = obj_name.split(".")[0]

                    obj_path = obj_path.split(".name=")[0]
                    obj_path = obj_path.replace(".", "/")

                    idx = find_resource_idx(template, resource_path, obj_path, obj_name)
                    if idx:
                        obj_path += "/" + idx

                # if "containers" in obj_path:
                #     obj_path = f"spec/template/spec/containers/{str(idx)}"
                # elif "initContainers" in obj_path:
                #     obj_path = f"spec/template/spec/initContainers/{str(idx)}"

            if check_id == "check_52":
                obj_path = obj_path.replace(".", "/")
                obj_path = obj_path.replace("volumeClaimTemplates", "volumeClaimTemplates/0")
                # Delete the last part of obj_path after requests
                obj_path = "/".join(obj_path.split("/")[:-2])

            paths = {
                "resource_path": resource_path,
                "obj_path": obj_path
            }

            if "." in obj_path:
                paths["obj_path"] = obj_path.replace(".", "/")

            if check_id == "check_53":
                service_name = get_headless_service_name(template)

                if not service_name:
                    # Get StatefulSet object
                    stateful_set = get_resource_dict(template, resource_path.split("/"))

                    if "serviceName" in stateful_set["spec"]:
                        service_name = stateful_set["spec"]["serviceName"]

                        # Build Service service_path
                        service_path = "Service/"
                        if "namespace" in stateful_set["metadata"]:
                            service_path += f"{stateful_set['metadata']['namespace']}/"
                        else:
                            service_path += "default/"
                        service_path += service_name

                        # Find Service and add ClusterIP: None
                        service = get_resource_dict(template, service_path.split("/"))
                        if service and "spec" in service and "clusterIP" in service["spec"]:
                            service["spec"]["clusterIP"] = "None"

                    else:
                        print("TODO: create headless service for statefulset!")

                paths["value"] = service_name

            elif check_id == "check_62":
                if jdx == 0:
                    continue
                # Get the shared Service Account
                k8s_resource = get_resource_dict(template, resource_path.split("/"))
                sa_resource_path = "ServiceAccount/"
                if "namespace" in k8s_resource["metadata"]:
                    sa_resource_path += k8s_resource["metadata"]["namespace"] + "/"
                else:
                    sa_resource_path += "default/"
                if "template" in k8s_resource["spec"]:
                    k8s_resource = k8s_resource["spec"]["template"]["spec"]
                else:
                    k8s_resource = k8s_resource["spec"]
                sa_resource_path += k8s_resource["serviceAccountName"]

                service_account = get_resource_dict(template, sa_resource_path.split("/"))
                if service_account:
                    service_account = copy.copy(service_account)
                    # Set new name
                    service_account["metadata"]["name"] = "test-SA" + str(jdx)
                    if "namespace" in service_account["metadata"] and \
                            service_account["metadata"]["namespace"] == "default":
                        service_account["metadata"]["namespace"] = "test-ns"
                    # Append new SA to the template
                    template.append(service_account)
                    # Add value to paths
                    paths["value"] = "test-SA" + str(jdx)
                    paths["obj_path"] = paths["obj_path"].replace("/serviceAccountName", "")
                    check_id = "check_37"
                else:
                    continue

            checks_remove_last = ["check_10", "check_11", "check_12"]
            if check_id in checks_remove_last:
                # Remove last part of paths["obj_path"] after the last "/"
                paths["obj_path"] = "/".join(paths["obj_path"].split("/")[:-1])

            if check["query_id"] == "268ca686-7fb7-4ae9-b129-955a2a89064e":
                cont_path, containers, _ = terrascan_fix_chart.get_container_path(template, resource_path.split("/"))
                for idx in range(len(containers)):
                    paths["obj_path"] = cont_path + str(idx)
                    fix_template.set_template(template, check_id, paths)

            else:
                fix_template.set_template(template, check_id, paths)

        # After iterating all files, return check_id
        return check_id

    else:
        print("No fix found for check ID: " + check["query_id"])
        return None


def get_resource_dict(template: dict, resource_path: str) -> dict:
    """Gets a K8s object from the YAML template.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (str): The path to the resource in the YAML template.
        
    Returns:
        document (dict): The K8s resource object.
    """

    for document in template:
        if document["kind"] == resource_path[0]:
            if "namespace" in document["metadata"]:

                # Ignore default ns
                if document["metadata"]["namespace"] == "default":
                    if document["metadata"]["name"] == resource_path[-1]:
                        return document

                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "test-ns":
                    if document["metadata"]["name"] == resource_path[-1]:
                        return document

                elif document["metadata"]["namespace"] == resource_path[1]:
                    if document["metadata"]["name"] == resource_path[-1]:
                        return document

                elif document["metadata"]["namespace"] == resource_path[1] and \
                    document["metadata"]["name"] == resource_path[-1]:
                    return document

            elif resource_path[1] == "default":
                if document["metadata"]["name"] == resource_path[-1]:
                    return document

            elif document["metadata"]["name"] == resource_path[1]:
                return document


def get_headless_service_name(template: dict) -> str:
    """Gets the name of the headless service.
    
    Args:
        template (dict): The parsed YAML template.
    
    Returns:
        name (str): The name of the headless service.
    """

    for document in template:
        if document["kind"] == "Service":
            if "clusterIP" in document["spec"] and document["spec"]["clusterIP"] is not None and \
                document["spec"]["clusterIP"]:
                if document["spec"]["clusterIP"] == "None":
                    return document["metadata"]["name"]

    return ""


def remove_password(chart_folder: str, files: list):
    """Remove password from K8s object.

    Policy: KICS - Passwords And Secrets - Generic Password
    
    Args:
        chart_folder (str): The name of the chart to fix.
        files (list): The list of files to fix.
    """

    file_path = "templates/" + chart_folder + "_template.yaml"
    file_path = "test_files/mysql_fixed_template.yaml"

    for file in files:

        # Read the contents of the file
        with open(file_path, 'r', encoding="utf-8") as file:
            lines = file.readlines()

        line = int(file["line"])
        # Check if the line_number is valid
        if line < 1 or line > len(lines):
            print("Invalid line number.")
            return

        # Remove the specified line from the list of lines
        lines.pop(line - 1)

        # Write the modified lines back to the file
        with open(file_path, 'w', encoding="utf-8") as file:
            file.writelines(lines)


class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    # KICS Policies: https://docs.kics.io/latest/queries/all-queries/

    _LOOKUP = {
        "5572cc5e-1e4c-4113-92a6-7a8a3bd25e6d": "check_22",
        "4ac0e2b7-d2d2-4af7-8799-e8de6721ccda": "check_5",
        "ca469dd4-c736-448f-8ac1-30a642705e0a": "check_4",
        "cf34805e-3872-4c08-bf92-6ff7bb0cfadb": "check_13",
        "02323c00-cdc3-4fdc-a310-4f2b3e7a1660": "check_13",
        "e3aa0612-4351-4a0d-983f-aefea25cf203": "check_13",
        "b14d1bc4-a208-45db-92f0-e21f8e2588e9": "check_2",
        "229588ef-8fde-40c8-8756-f4f2b5825ded": "check_1",
        "dbbc6705-d541-43b0-b166-dd4be8208b54": "check_23",
        "a659f3b5-9bf0-438a-bd9a-7d3a6427f1e3": "check_8",
        "f377b83e-bd07-4f48-a591-60c82b14a78b": "check_31",
        "591ade62-d6b0-4580-b1ae-209f80ba1cd9": "check_37",
        "48471392-d4d0-47c0-b135-cdec95eb3eef": "check_36",
        "611ab018-c4aa-4ba2-b0f6-a448337509a6": "check_26",
        "7c81d34c-8e5a-402b-9798-9f442630e678": "check_9",
        "583053b7-e632-46f0-b989-f81ff8045385": "check_0",
        "ade74944-a674-4e00-859e-c6eab5bde441": "check_7",
        "8b36775e-183d-4d46-b0f7-96a6f34a723f": "check_32",
        "268ca686-7fb7-4ae9-b129-955a2a89064e": "check_23",
        "4a20ebac-1060-4c81-95d1-1f7f620e983b": "check_48",
        "48a5beba-e4c0-4584-a2aa-e6894e4cf424": "check_49",
        "a97a340a-0063-418e-b3a1-3028941d0995": "check_30",
        "a9c2f49d-0671-4fc9-9ece-f4e261e128d0": "check_27",
        "dd29336b-fe57-445b-a26e-e6aa867ae609": "check_21",
        "2f1a0619-b12b-48a0-825f-993bb6f01d58": "check_23",
        "235236ee-ad78-4065-bd29-61b061f28ce0": "check_23",
        "19ebaa28-fc86-4a58-bcfa-015c9e22fe40": "check_23",
        "302736f4-b16c-41b8-befe-c0baffa0bd9d": "check_10",
        "cd290efd-6c82-4e9d-a698-be12ae31d536": "check_11",
        "6b6bdfb3-c3ae-44cb-88e4-7405c1ba2c8a": "check_12",
        "caa3479d-885d-4882-9aac-95e5e78ef5c2": "check_25",
        "3d658f8b-d988-41a0-a841-40043121de1e": "check_33",
        "8cf4671a-cf3d-46fc-8389-21e7405063a2": "check_52",
        "bb241e61-77c3-4b97-9575-c0f8a1e008d0": "check_53",
        "b7652612-de4e-4466-a0bf-1cd81f0c6063": "check_55",
        "845acfbe-3e10-4b8e-b656-3b404d36dfb2": "check_56",
        "056ac60e-fe07-4acc-9b34-8e1d51716ab9": "check_54",
        "b7bca5c4-1dab-4c2c-8cbe-3050b9d59b14": "check_54",
        "1db3a5a5-bf75-44e5-9e44-c56cfc8b1ac5": "check_60",
        "26763a1c-5dda-4772-b507-5fca7fb5f165": "check_56",
        "aee3c7d2-a811-4201-90c7-11c028be9a46": "check_6",
        "c1032cf7-3628-44e2-bd53-38c17cf31b6b": "check_62",
        "592ad21d-ad9b-46c6-8d2d-fad09d62a942": "check_54",
        "aa8f7a35-9923-4cad-bd61-a19b7f6aac91": "check_47",
        "5308a7a8-06f8-45ac-bf10-791fe21de46e": "check_47",
        "192fe40b-b1c3-448a-aba2-6cc19a300fe3": "check_63",
        "249328b8-5f0f-409f-b1dd-029f07882e11": "check_65",
        "b23e9b98-0cb6-4fc9-b257-1f3270442678": "check_60",
        "c589f42c-7924-4871-aee2-1cede9bc7cbc": "check_54",
        "85ab1c5b-014e-4352-b5f8-d7dea3bb4fd3": "",
        "a6f34658-fdfb-4154-9536-56d516f65828": "check_15",
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
