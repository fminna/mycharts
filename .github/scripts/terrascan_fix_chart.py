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

""" Fixing Helm Chart based on Terrascan results.
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

    for run in results["runs"]:
        for check in run["results"]:
            print(f"{check['ruleId']}: {check['message']['text']}")
            check_id = fix_issue(check, template)

            for logical_location in check["locations"]:
                for _ in logical_location["logicalLocations"]:
                    all_checks.append(check_id)

    print("\nAll issues fixed!\n")

    # Print all found checks
    all_checks = [x for x in all_checks if x is not None]
    all_checks.sort()
    print(f"Total number of checks: {len(all_checks)}")
    print(", ".join(all_checks))
    # For check_ from 0 to 66 (i.e., check_0, check_1, ..., check_66), print the
    # occurrences of each check in all_checks, all in one line
    # for i in range(0, 67):
    #     print(f"{all_checks.count(f'check_{i}')}", end=" ")

    name = f"fixed_{chart_folder}_terrascan_fixed"
    fix_template.save_yaml_template(template, name)


def get_resource_namespace(template: dict, kind: str, name: str) -> str:
    """Gets the namespace of a K8s resource.
    
    Args:
        template (dict): The parsed YAML template.
        kind (str): The kind of the resource.
        name (str): The name of the resource.

    Returns:
        str: The namespace of the resource.
    """

    for document in template:
        if document and document["kind"] == kind and document["metadata"]["name"] == name:
            if "namespace" in document["metadata"]:
                return document["metadata"]["namespace"]

    return "default"


def get_container_path(template: dict, resource_path: list) -> tuple:
    """Gets the path (e.g., spec/template/spec/containers/0) to a container in a K8s resource.
    
    Args:
        template (dict): The parsed YAML template.
        resource_path (list): The path to the resource.

    Returns:
        tuple: The path to the container and the list of containers.
    """

    cont_path = ""
    containers = []
    init_containers = []

    for document in template:
        aux_path = ""

        if fix_template.check_resource_path(resource_path, document):
            document = document["spec"]
            cont_path += "spec/"

            if "template" in document:
                document = document["template"]["spec"]
                cont_path += "template/spec/"
            elif "jobTemplate" in document:
                document = document["jobTemplate"]["spec"]["template"]["spec"]
                cont_path += "jobTemplate/spec/template/spec/"

            containers = document["containers"]
            aux_path = "containers/"

            if "initContainers" in document:
                init_containers = document["initContainers"]

        if containers:
            cont_path += aux_path
            break

    return cont_path, containers, init_containers


def fix_issue(check: str, template: dict) -> str:
    """Fixes an issue based on the Terrascan ruleId.

    Source: https://runterrascan.io/docs/policies/k8s/

    Args:
        check (dict): The dictionary representing a check to fix.
        template (dict): The parsed YAML template.
    """

    # Get function from lookup dictionary
    my_lookup = LookupClass()
    check_id = my_lookup.get_value(check['ruleId'])

    # Check if the function exists and call it
    if check_id is not None:
        # Iterate over all locations of the current issue
        for logical_location in check["locations"]:
            for location in logical_location["logicalLocations"]:

                kind = location["kind"]
                # convert kind to standard format --- removing kubernetes_
                kind = kind[11:]
                # convert each character after '_' to uppercase
                kind = ''.join([word.capitalize() for word in kind.split('_')])
                name = location["name"]
                namespace = get_resource_namespace(template, kind, name)
                resource_path = f"{kind}/{namespace}/{name}"
                paths = {
                        "resource_path": resource_path,
                        "obj_path": ""
                }

                checks_with_paths = ["AC_K8S_0069", "AC_K8S_0078", "AC_K8S_0085", \
                                     "AC_K8S_0097", "AC_K8S_0098", "AC_K8S_0099", \
                                     "AC_K8S_0100", "AC_K8S_0072", "AC_K8S_0070", \
                                     "AC_K8S_0087", "AC_K8S_0068", "AC_K8S_0080", \
                                      "AC_K8S_0079"]
                if check['ruleId'] in checks_with_paths:
                    # Call fix_template for each container in the K8s resource
                    cont_path, containers, init_containers = get_container_path(template, resource_path.split("/"))
                    for idx in range(len(containers)):
                        paths["obj_path"] = cont_path + str(idx)
                        fix_template.set_template(template, check_id, paths)

                    if init_containers:
                        for idx in range(len(init_containers)):
                            cont_path = cont_path.replace("containers", "initContainers")
                            paths["obj_path"] = cont_path + str(idx)
                            fix_template.set_template(template, check_id, paths)

                else :
                    fix_template.set_template(template, check_id, paths)

                return check_id

    else:
        print("No fix found for check ID: " + check['ruleId'])
        return None


# We ignore checks CKV_K8S_1-CKV_K8S_8 because they refer to
# Pod Security Policies, which are deprecated in Kubernetes 1.21.

class LookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
        "AC_K8S_0099": "check_1", 
        "AC_K8S_0100": "check_2", 
        "AC_K8S_0097": "check_4", 
        "AC_K8S_0098": "check_5", 
        "AC_K8S_0069": "check_9", 
        "AC_K8S_0085": "check_22", 
        "AC_K8S_0086": "check_26", 
        "AC_K8S_0078": "check_27", 
        "AC_K8S_0080": "check_31", 
        "AC_K8S_0073": "check_32", 
        "AC_K8S_0051": "check_33", 
        "AC_K8S_0045": "check_35",
        "AC_K8S_0087": "check_28",
        "AC_K8S_0070": "check_7",
        "AC_K8S_0064": "check_30",
        "AC_K8S_0072": "check_8",
        "AC_K8S_0079": "check_13",
        "AC_K8S_0084": "check_12",
        "AC_K8S_0111": "check_56",
        "AC_K8S_0068": "check_0",
        "AC_K8S_0076": "check_47",
        "AC_K8S_0081": "check_55",
        "AC_K8S_0082": "check_10",
        "AC_K8S_0088": "check_15",
        "AC_K8S_0021": "", # AlwaysPullImages plugin is not set https://docs.bridgecrew.io/docs/ensure-that-the-admission-control-plugin-alwayspullimages-is-set
        "AC_K8S_0002": "", # TLS disabled can affect the confidentiality of the data in transit
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
