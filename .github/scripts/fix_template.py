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

""" This script implements the fixes (adding/removing lines) into a Helm Chart YAML template
"""

from typing import Callable
import yaml
import requests


def parse_yaml_template(chart_folder: str) -> list:
    """Parses a Helm chart template yaml file and returns it as a dictionary.

    Args:
        folder: The folder containing the Helm Chart template.
        chart_folder: The name of the Helm Chart to parse.

    Returns:
        A dictionary containing the parsed contents of the template.yaml file.
    """

    # Parse and return the multi-document YAML file while preserving comments
    file_path = f"{chart_folder}_template.yaml"
    with open(file_path, "r", encoding="utf-8") as file:
        template = list(yaml.load_all(file, Loader=yaml.FullLoader))

    # Remove null document (--- null) from template
    template = [document for document in template if document is not None and document["kind"] != "PodSecurityPolicy"]
    return template


def save_yaml_template(template: str, chart_folder: str):
    """Save chart template data to a file.

    Args:
        template: A dictionary containing the template data to be saved.
        chart_folder: The name of the Helm Chart to save.

    Raises:
        IOError: If there is an error writing to the file.
    """

    file_path = f"{chart_folder}_template.yaml"
    # Remove null document (--- null) from template
    for document in template:
        if document is None:
            template.remove(document)

    with open(file_path, 'w', encoding="utf-8") as file:
        yaml.safe_dump_all(template, file, sort_keys=False)


def get_docker_img_tag(image_name: str) -> str:
    """
    Retrieves the latest container image tag that is not "latest" for a given image name
    using the Docker Registry HTTP API.

    Args:
        image_name (str): A string representing the name of the container image to 
        retrieve the tag for.
        registry (str): A string representing the name of the container registry

    Returns:
        A string representing the latest image tag that is not "latest", or None 
        if no such tag exists.
    """

    url = f'https://hub.docker.com/v2/repositories/library/{image_name}/tags'

    try:
        # Send the API request
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse the response JSON
        response_json = response.json()

        # Extract the tag names from the response JSON
        tags = [tag['name'] for tag in response_json['results']]
        # Order the tags in ascending order
        tags.sort()

        # Find the first tag that is not "latest"
        for tag in tags:
            if tag != "latest":
                return tag

        # If no tag was found, return None
        return None

    except requests.exceptions.HTTPError:
        return ""


def get_docker_img_digest(image_name: str, image_tag: str) -> str:
    """Retrieves the digest of a Docker image with the given name and tag, using
    the specified Docker Hub access token for authentication.

    Args:
        image_name: A string representing the name of the Docker image.
        image_tag: A string representing the tag of the Docker image.
        registry: The name of the container registry.

    Returns:
        A string representing the digest of the Docker image.
    """

    url = f'https://hub.docker.com/v2/repositories/library/{image_name}/tags'

    try:
        # Send the API request
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse the response JSON
        response_json = response.json()

        # Return the digest of the image
        for img in response_json["results"]:
            if img["name"] == image_tag:
                return img["images"][0]["digest"]

        # If no digest was found, return None
        return None

    except requests.exceptions.HTTPError:
        return ""


def check_resource_path(path_list: str, document: dict) -> bool:
    """Check if the resource path exists in the template.

    Args:
        path_list: The resource path to check.
        document: The template to check.

    Returns:
        True if the resource path exists, False otherwise.
    """

    if path_list and document:
        if document["kind"].casefold() == path_list[0].casefold():

            if "namespace" in document["metadata"]:

                # Ignore default ns
                if document["metadata"]["namespace"] == "default":
                    return document["metadata"]["name"] == path_list[-1]

                # If the namespace was added during fixing, ignore it
                elif document["metadata"]["namespace"] == "test-ns":
                    return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == "kube-system":
                    return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1]:
                    return document["metadata"]["name"] == path_list[-1]

                elif document["metadata"]["namespace"] == path_list[1] and \
                    document["metadata"]["name"] == path_list[-1]:
                    return True

            # "namespace" not in document["metadata"]
            elif path_list[1] == "default":
                return document["metadata"]["name"] == path_list[-1]

            elif document["metadata"]["name"] == path_list[1]:
                return True

    return False


def get_app_label(template: dict, resource_path: str) -> str:
    """Get the app label of the resource.
    
    Args:
        template: The template to check.
        resource_path: The resource path to check.
        
    Returns:
        The app label of the resource.
    """

    app = "test-app"
    for document in template:
        if check_resource_path(resource_path.split("/"), document):
            if "labels" in document["metadata"] and document["metadata"]["labels"] is not None:
                if "app" in document["metadata"]["labels"]:
                    app = document["metadata"]["labels"]["app"]

    return app


global resource_quota
resource_quota = False

global limit_range
limit_range = False

global network_policy
network_policy = False

global service_account_idx
service_account_idx = 0


def set_template(template: dict, check_id: str, check: dict) -> None:
    """Change the chart template for the Helm Chart.
    
    Args:
        template: The template to change.
        check_id: The ID of the check to change.
        check: The dictionary container resource_path, object_path and value.
    
    Returns: None
    """

    if not check:
        return

    # If Network Policy missing issue, create and append one
    elif check_id == "check_40":
        # app = get_app_label(template, check["resource_path"])
        # Append Network Policy to the template
        net_policy1, net_policy2 = set_net_policy()
        template.append(net_policy1)
        template.append(net_policy2)

        # Set global variable to True
        global network_policy
        network_policy = True

    else:

        # Get function from lookup dictionary
        my_lookup = FuncLookupClass()
        process_func = my_lookup.get_value(check_id)

        # Check if the function exists and call it
        if process_func is not None:
            # Iterate with index through the document dictionaries
            for document in template:
                # If the resource to fix is in the current YAML document
                if check_resource_path(check["resource_path"].split("/"), document):

                    # Find the object
                    keys = check["obj_path"].split("/")
                    obj = document

                    no_path_checks = ["check_31", "check_29", "check_26", \
                                      "check_45", "check_54", "check_56", \
                                      "check_36", "check_12", "check_35", \
                                      "check_37", "check_47", "check_63", \
                                      "check_64", "check_65", "check_67", \
                                      "check_13"]
                    if check_id in no_path_checks:
                        if "value" in check:
                            process_func(obj, check["value"])
                        else:
                            process_func(obj)
                        break

                    if check_id == "check_33":
                        if "template" in obj["spec"]:
                            process_func(obj["spec"]["template"]["spec"])
                        else:
                            process_func(obj["spec"])
                        break

                    for key in keys:
                        if key:
                            if key.isdigit():
                                key = int(key)
                            elif key not in obj:
                                continue
                            obj = obj[key]

                    if check_id == "check_60":
                        # app = get_app_label(template, check["resource_path"])
                        pdp = set_pod_disruption_budget(obj)
                        template.append(pdp)

                    elif check_id in ("check_23", "check_24", "check_34"):
                        if "add" in check and "drop" in check:
                            process_func(obj, check["add"], check["drop"])
                        elif "add" in check:
                            process_func(obj, check["add"])
                        elif "drop" in check:
                            process_func(obj, "", check["drop"])
                        else:
                            process_func(obj, "", ["ALL"])

                    elif check_id == "check_48":
                        # Append namespace LimitRange to the template
                        limit_range1, limit_range2 = process_func(obj)
                        global limit_range
                        if not limit_range:
                            template.append(limit_range1)
                            template.append(limit_range2)
                            limit_range = True

                    elif check_id == "check_49":
                        # Append namespace ResourceQuota to the template
                        resource_quota1, resource_quota2 = process_func(obj)
                        global resource_quota
                        if not resource_quota:
                            template.append(resource_quota1)
                            template.append(resource_quota2)
                            resource_quota = True

                    elif "value" in check:
                        process_func(obj, check["value"])

                    else:
                        process_func(obj)


def set_liveness_probe(obj: dict, value=30):
    """Set the Liveness Probe command to each K8s object.

    Policy: Ensure each container has a configured liveness probe
    
    Args:
        obj (dict): K8s object to modify.
        value (int): value to set the initial delay to.
    """

    obj["livenessProbe"] = {
        "exec": {"command": ["ls", "/"]}, 
        "initialDelaySeconds": value, 
        "periodSeconds": 10
    }


def set_readiness_probe(obj: dict, value=30):
    """Set the Readiness Probe command to each K8s object.

    Policy: Readiness Probe Should be Configured
    
    Args:
        obj (dict): K8s object to modify.
        value (int): value to set the initial delay to.
    """

    # Set the readiness probe to the container
    obj["readinessProbe"] = {
        "exec": {"command": ["ls", "/"]}, 
        "initialDelaySeconds": value, 
        "periodSeconds": 10
    }


def set_privileged(obj: dict, value=False):
    """Set the privileged permission to K8s objects.

    Policy: Containers should not run as privileged
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): value to set the privileged permission to.
    """

    # securityContext is not set, Set it
    if not "securityContext" in obj:
        obj["securityContext"] = {
            "privileged": value
        }
    # If securityContext is set, but privileged is not, Set it
    elif not "privileged" in obj["securityContext"]:
        obj["securityContext"]["privileged"] = value
    else:
        obj["securityContext"]["privileged"] = value


def set_capabilities(obj: dict, add="", drop=""):
    """Set capabilities from K8s objects. If the capabilities key is not defined, 
    or ALL capabilities are granted, we drop all capabilities. Otherwise, we only 
    Set the insure ones.

    Insecure capabilities: ALL, BPF, MAC_ADMIN, MAC_OVERRIDE, NET_ADMIN, NET_RAW, 
    SETPCAP, PERFMON, SYS_ADMIN, SYS_BOOT, SYS_MODULE, SYS_PTRACE, SYS_RAWIO
    
    Args:
        obj (dict): K8s object dict to modify.
        add (str): capabilities to add.
        drop (str): capabilities to drop.
    """

    # Only set this property at the container level
    if "image" not in obj:
        return

    if not drop:
        drop = ["ALL"]

    if "securityContext" not in obj or \
        obj["securityContext"] is None or \
            not obj["securityContext"]:
        obj["securityContext"] = {
            "capabilities": {
                "drop": drop
            }
        }

    # If no "capabilities" in securityContext, add "capabilities" and set drop to all
    if "capabilities" not in obj["securityContext"] or \
        obj["securityContext"]["capabilities"] is None or \
            not obj["securityContext"]["capabilities"]:
        obj["securityContext"]["capabilities"] = {
            "drop": drop
        }

    # Drop ALL by default
    if "add" in obj["securityContext"]["capabilities"]:
        del obj["securityContext"]["capabilities"]["add"]

    obj["securityContext"]["capabilities"]= {
        "drop": drop
    }

    # Eventually, add/drop capabilities
    if add:
        obj["securityContext"]["capabilities"]["add"] = add


    # insecure_caps = ["ALL", "All", "all", "BPF", "MAC_ADMIN", "MAC_OVERRIDE", "NET_ADMIN",
    #                 "NET_RAW", "SETPCAP", "PERFMON", "SYS_ADMIN", "SYS_BOOT", "SYS_MODULE", 
    #                 "SYS_PTRACE", "SYS_RAWIO"]
    #
    # # If "capabilities" in securityContext, but insecure capabilities are granted,
    # # drop only insecure ones
    # if "add" in obj["securityContext"]["capabilities"] and \
    #     set(obj["securityContext"]["capabilities"]["add"]).intersection(insecure_caps):

    #     # Remove insecure capabilities from "add"
    #     obj["securityContext"]["capabilities"]["add"] = [cap \
    #         for cap in obj["securityContext"]["capabilities"]["add"]
    #             if cap not in insecure_caps
    #     ]

    #     # If add is not empty, add capabilities from argument
    #     if add:
    #         obj["securityContext"]["capabilities"]["add"] += add

    #     # If "add" is empty, delete it
    #     if not obj["securityContext"]["capabilities"]["add"]:
    #         del obj["securityContext"]["capabilities"]["add"]

    # # If add not in "capabilities", but the add argument is set, add it
    # elif add:
    #     obj["securityContext"]["capabilities"]= {
    #             "add": add
    #     }

    # if "add" not in obj["securityContext"]["capabilities"]:
    #     if "drop" in obj["securityContext"]["capabilities"]:
    #         obj["securityContext"]["capabilities"]["drop"] = drop
    #     else:
    #         obj["securityContext"]["capabilities"]= {
    #             "drop": drop
    #         }

    # elif obj["securityContext"]["capabilities"]["add"] != "all":

    #     insecure_caps.remove("ALL")
    #     insecure_caps.remove("All")
    #     insecure_caps.remove("all")

    #     drop = [cap for cap in drop \
    #             if cap not in obj["securityContext"]["capabilities"]["add"]]

    #     obj["securityContext"]["capabilities"]["drop"] = drop


def set_cpu_limit(obj: dict, value="250m"):
    """Set the CPU limit to each K8s object.

    Policy: CPU limits should be set
    
    Args:
        obj (dict): K8s object to modify.
        value (str): value to set the CPU limit to.
    """

    # If resources is not set, Set it
    if "resources" not in obj or \
        obj["resources"] is None or \
            not obj["resources"]:
        obj["resources"] = {
            "limits": {
                "cpu": value
            }
        }
        set_cpu_request(obj, value)
        set_memory_limit(obj)
        set_memory_request(obj)

    if "requests" in obj["resources"] and \
        obj["resources"]["requests"] is not None and \
            obj["resources"]["requests"]:
        if "cpu" in obj["resources"]["requests"]:
            value = obj["resources"]["requests"]["cpu"]

    # If resources is set, but limits is not, Set it
    if "limits" not in obj["resources"] or \
        obj["resources"]["limits"] is None:
        obj["resources"]["limits"] = {
            "cpu": value
        }

    else:
        obj["resources"]["limits"]["cpu"] = value


def set_cpu_request(obj: dict, value="250m"):
    """Set the CPU request to each K8s object.

    Policy: CPU request should be set
    
    Args:
        obj (dict): K8s object to modify.
        value (str): value to set the CPU request to.
    """

    # If resources is not set, Set it
    if "resources" not in obj or \
        obj["resources"] is None or \
            not obj["resources"]:
        obj["resources"] = {
            "requests": {
                "cpu": value
            }
        }
        set_cpu_limit(obj, value)
        set_memory_limit(obj)
        set_memory_request(obj)

    if "limits" in obj["resources"] and \
        obj["resources"]["limits"] is not None and \
            obj["resources"]["limits"]:
        if "cpu" in obj["resources"]["limits"]:
            value = obj["resources"]["limits"]["cpu"]

    # If resources is set, but requests is not, Set it
    if "requests" not in obj["resources"] or \
        obj["resources"]["requests"] is None or \
            not obj["resources"]["requests"]:
        obj["resources"]["requests"] = {
            "cpu": value
        }

    else:
        obj["resources"]["requests"]["cpu"] = value


def set_memory_limit(obj: dict, value="128Mi"):
    """Set the memory limit to each K8s object.

    Policy: Memory limits should be set
    
    Args:
        obj (dict): K8s object to modify.
        value (str): value to set the memory limit to.
    """

    # If resources is not set, Set it
    if "resources" not in obj or \
        obj["resources"] is None or \
            not obj["resources"]:
        obj["resources"] = {
            "limits": {
                "memory": value
            }
        }
        set_memory_request(obj, value)
        set_cpu_limit(obj)
        set_cpu_request(obj)

    if "requests" in obj["resources"] and \
        obj["resources"]["requests"] is not None and \
            obj["resources"]["requests"]:
        if "memory" in obj["resources"]["requests"]:
            value = obj["resources"]["requests"]["memory"]

    # If resources is set, but limits is not, Set it
    if "limits" not in obj["resources"] or \
        obj["resources"]["limits"] is None or \
            not obj["resources"]["limits"]:
        obj["resources"]["limits"] = {
            "memory": value
        }

    else:
        obj["resources"]["limits"]["memory"] = value


def set_memory_request(obj: dict, value="128Mi"):
    """Set the memory request to each K8s object.

    Policy: Memory request should be set
    
    Args:
        obj (dict): K8s object to modify.
        value (str): The value to set the memory request to.
    """

    # If resources is not set, Set it
    if "resources" not in obj or \
        obj["resources"] is None or \
        not obj["resources"]:
        obj["resources"] = {
            "requests": {
                "memory": value
            }
        }
        set_memory_limit(obj, value)
        set_cpu_limit(obj)
        set_cpu_request(obj)

    if "limits" in obj["resources"] and \
        obj["resources"]["limits"] is not None and \
            obj["resources"]["limits"]:
        if "memory" in obj["resources"]["limits"]:
            value = obj["resources"]["limits"]["memory"]

    # If resources is set, but requests is not, Set it
    if "requests" not in obj["resources"] or \
        obj["resources"]["requests"] is None or \
            not obj["resources"]["requests"]:
        obj["resources"]["requests"] = {
            "memory": value
        }

    else:
        obj["resources"]["requests"]["memory"] = value


def set_equal_requests(obj: dict):
    """Set memory requests equal to memory limits.
    
    Args:
        obj (dict): K8s object to modify.
    """

    cpu_requests = "250m"
    memory_requests = "128Mi"

    if "cpu" in obj["resources"]["requests"]:
        cpu_requests = obj["resources"]["requests"]["cpu"]

    if "memory" in obj["resources"]["requests"]:
        memory_requests = obj["resources"]["requests"]["memory"]

    obj["resources"]["limits"]["cpu"] = cpu_requests
    obj["resources"]["limits"]["memory"] = memory_requests


def remove_host_path(obj: dict, value=""):
    """Remove host path from K8s object.
    
    Args:
        obj (dict): K8s object to modify.
        value (str): The host path value to add, eventually.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    if "volumes" in obj and obj["volumes"] is not None and obj["volumes"]:
        obj["volumes"] = [volume for volume in obj["volumes"] if "hostPath" not in volume]
        if not obj["volumes"]:
            del obj["volumes"]

    if value:
        volume_name = value.split("/")[-1]
        if "volumes" not in obj or obj["volumes"] is None:
            obj["volumes"] = [{
                "name": volume_name,
                "hostPath": {
                    "path": value
                }
            }]
        else:
            volume = {
                "name": volume_name,
                "hostPath": {
                    "path": value
                }
            }
            obj["volumes"].append(volume)


def set_limit_range(obj: dict) -> dict:
    """Set cpu and memory limits to each K8s object.

    Policy: CPU and Memory limits should be set
    
    Args:
        obj (dict): K8s object to modify.

    Returns:
        dict: LimitRange object
    """

    namespace = "test-ns"
    if "namespace" in obj["metadata"]:
        if obj["metadata"]["namespace"] != "default":
            namespace = obj["metadata"]["namespace"]

    limit_range1 = {
        "apiVersion": "v1",
        "kind": "LimitRange",
        "metadata": {
            "name": "cpu-min-max-demo-lr",
            "namespace": namespace
        },
        "spec": {
            "limits": [
                {
                    "max": {
                        "cpu": "800m"
                    },
                    "min": {
                        "cpu": "250m"
                    },
                    "type": "Container"
                }
            ]
        }
    }
    limit_range2 = {
        "apiVersion": "v1",
        "kind": "LimitRange",
        "metadata": {
            "name": "cpu-min-max-demo-lr",
            "namespace": "default"
        },
        "spec": {
            "limits": [
                {
                    "max": {
                        "cpu": "800m"
                    },
                    "min": {
                        "cpu": "250m"
                    },
                    "type": "Container"
                }
            ]
        }
    }
    return limit_range1, limit_range2


def set_resource_quota(obj: dict) -> dict:
    """Set priorityClassName to each K8s object.

    Policy: Each namespace should have a ResourceQuota policy associated to limit the total amount
    of resources Pods, Containers and PersistentVolumeClaims can consume
    
    Args:
        obj (dict): K8s object to modify.

    Returns:
        dict: ResourceQuota object
    """

    namespace = "test-ns"
    if "namespace" in obj["metadata"]:
        if obj["metadata"]["namespace"] != "default":
            namespace = obj["metadata"]["namespace"]

    resource_quota1 = {
        "apiVersion": "v1",
        "kind": "ResourceQuota",
        "metadata": {
            "name": "pods-high",
            "namespace": namespace
        },
        "spec": {
            "hard": {
                "cpu": "1000",
                "memory": "200Gi",
                "pods": "10"
            },
            "scopeSelector": {
                "matchExpressions": [
                    {
                        "operator": "In",
                        "scopeName": "PriorityClass",
                        "values": ["high"]
                    }
                ]
            }
        }
    }
    resource_quota2 = {
        "apiVersion": "v1",
        "kind": "ResourceQuota",
        "metadata": {
            "name": "pods-high",
            "namespace": "default"
        },
        "spec": {
            "hard": {
                "cpu": "1000",
                "memory": "200Gi",
                "pods": "10"
            },
            "scopeSelector": {
                "matchExpressions": [
                    {
                        "operator": "In",
                        "scopeName": "PriorityClass",
                        "values": ["high"]
                    }
                ]
            }
        }
    }

    return resource_quota1, resource_quota2


def set_uid(obj: dict, uid=25000):
    """Set the uid for a K8s object.

    Args:
        obj (dict): K8s object to modify.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    # If securityContext is not set, Set it
    if "securityContext" not in obj or \
        obj["securityContext"] is None or \
            not obj["securityContext"]:
        obj["securityContext"] = {
            "runAsUser": uid
        }
    # If securityContext is set, but runAsUser is not, Set it
    elif "runAsUser" not in obj["securityContext"] or \
        obj["securityContext"]["runAsUser"] is None or \
            not obj["securityContext"]["runAsUser"]:
        obj["securityContext"]["runAsUser"] = uid

    else:
        obj["securityContext"]["runAsUser"] = uid

    if "containers" in obj and obj["containers"] is not None and obj["containers"]:
        # Set runAsUser for each container
        for container in obj["containers"]:
            if "securityContext" not in container or \
                container["securityContext"] is None or \
                    not container["securityContext"]:
                container["securityContext"] = {
                    "runAsUser": uid
                }
            elif "runAsUser" not in container["securityContext"] or \
                container["securityContext"]["runAsUser"] is None or \
                    not container["securityContext"]["runAsUser"]:
                container["securityContext"]["runAsUser"] = uid
            else:
                container["securityContext"]["runAsUser"] = uid

    if "initContainers" in obj and obj["initContainers"] is not None and obj["initContainers"]:
        # Set runAsUser for each container
        for container in obj["initContainers"]:
            if "securityContext" not in container or \
                container["securityContext"] is None or \
                    not container["securityContext"]:
                container["securityContext"] = {
                    "runAsUser": uid
                }
            elif "runAsUser" not in container["securityContext"] or \
                container["securityContext"]["runAsUser"] is None or \
                    not container["securityContext"]["runAsUser"]:
                container["securityContext"]["runAsUser"] = uid
            else:
                container["securityContext"]["runAsUser"] = uid


def remove_docker_socket(obj: dict):
    """Remove docker socket from K8s object.
    
    Args:
        obj (dict): K8s object to modify.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    for volume in obj["volumes"]:
        if "hostPath" in volume and volume["hostPath"] is not None:
            if "path" in volume["hostPath"] and volume["hostPath"]["path"] is not None:
                if "docker.sock" in volume["hostPath"]["path"]:
                    obj["volumes"].remove(volume)


def set_root(obj: dict, value=True, uid=25000, gid=25000):
    """Set the root user to each K8s object.

    Policy: Minimize the admission of root containers
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the root user to.
        uid (int): The value to set the runAsUser to.
        gid (int): The value to set the runAsGroup to.
        fsg (int): The value to set the fsGroup to.
    """

    if not value:
        uid = 1000
        gid = 1000

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    # If securityContext is not set in containers, Set it
    if "securityContext" not in obj or \
        obj["securityContext"] is None or \
            not obj["securityContext"]:
        obj["securityContext"] = {
            "runAsNonRoot": value,
            "runAsUser": uid
        }
    # If runAsNonRoot is not set in securityContext, Set it
    else:
        obj["securityContext"]["runAsNonRoot"] = value

    # If runAsUser is not set in securityContext, Set it
    if "runAsUser" not in obj["securityContext"] or \
        obj["securityContext"]["runAsUser"] is None or \
            not obj["securityContext"]["runAsUser"]:
        obj["securityContext"]["runAsUser"] = uid

    # If runAsGroup is not set in securityContext, Set it
    if "runAsGroup" not in obj["securityContext"] or \
        obj["securityContext"]["runAsGroup"] is None or \
            not obj["securityContext"]["runAsGroup"]:
        obj["securityContext"]["runAsGroup"] = gid


def set_priv_esc(obj: dict, value=False):
    """Set allowPrivilegeEscalation to false for each K8s object.

    Policy: Containers should not run with allowPrivilegeEscalation
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the allowPrivilegeEscalation to.
    """

    # Only set this property at the container level
    if "image" not in obj:
        return

    # If securityContext is not set, Set it
    if "securityContext" not in obj or \
        obj["securityContext"] is None or \
            not obj["securityContext"]:
        obj["securityContext"] = {
            "allowPrivilegeEscalation": value
        }
    # If allowPrivilegeEscalation is not set, Set it
    elif "allowPrivilegeEscalation" not in obj["securityContext"] or \
        obj["securityContext"]["allowPrivilegeEscalation"] is None or \
            not obj["securityContext"]["allowPrivilegeEscalation"]:
        obj["securityContext"]["allowPrivilegeEscalation"] = value
    # else, set allowPrivilegeEscalation to value
    else:
        obj["securityContext"]["allowPrivilegeEscalation"] = value


def set_host_port(obj: dict):
    """ Set hostPort

    Policy: Prevent containers from insecurely exposing workload.

    Args:
        obj (dict): K8s object to modify.
    """

    if "template" in obj["spec"]:
        obj = obj["spec"]["template"]
    if "spec" in obj:
        obj = obj["spec"]

    if "initContainers" in obj:
        del obj['initContainers']

    # TODO
    # - hostPort


def set_seccomp(obj: dict):
    """Set the runtime SecComp default profile to each K8s object.

    Policy: Ensure seccomp profile is set to docker/default or runtime/default
    Policy: Prevent containers from having unnecessary system call privileges
    
    Args:
        obj (dict): K8s object to modify.
        profile (str): The name to set the SecComp profile to.
    """

    ###############################################
    # For Datree CIS Benchmark check
    # If annotations not in metadata, add it

    # "seccomp.security.alpha.kubernetes.io/defaultProfileName"
    # "seccomp.security.alpha.kubernetes.io/pod"

    # profile_name = "seccomp.security.alpha.kubernetes.io/defaultProfileName"
    profile_name = "seccomp.security.alpha.kubernetes.io/pod"
    profile = "runtime/default"

    if "metadata" not in obj or \
        obj["metadata"] is None or not obj["metadata"]:
        obj["metadata"] = {
            "annotations": {
                profile_name: profile
            }
        }
    elif "annotations" not in obj["metadata"] or \
        obj["metadata"]["annotations"] is None or \
            not obj["metadata"]["annotations"]:
        obj["metadata"]["annotations"] = {
            profile_name: profile
        }
    else:
        obj["metadata"]["annotations"][profile_name] = profile

    ###############################################

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    profile = "RuntimeDefault"

    if "securityContext" not in obj or \
        obj["securityContext"] is None or \
            not obj["securityContext"]:
        obj["securityContext"] = {
            "seccompProfile": {
                "type": profile
            }
        }
    else:
        obj["securityContext"]["seccompProfile"] = {
            "type": profile
        }

    # for container in obj["containers"]:
    #     if "securityContext" not in container or \
    #         container["securityContext"] is None or \
    #             not container["securityContext"]:
    #         container["securityContext"] = {
    #             "seccompProfile": {
    #                 "type": profile
    #             }
    #         }
    #     else:
    #         container["securityContext"]["seccompProfile"] = {
    #             "type": profile
    #         }

    # if "initContainers" in obj and obj["initContainers"] is not None and obj["initContainers"]:
    #     for container in obj["initContainers"]:
    #         if "securityContext" not in container or \
    #             container["securityContext"] is None or \
    #                 not container["securityContext"]:
    #             container["securityContext"] = {
    #                 "seccompProfile": {
    #                     "type": profile
    #                 }
    #             }
    #         else:
    #             container["securityContext"]["seccompProfile"] = {
    #                 "type": profile
    #             }


def get_container_names(obj: dict) -> list:
    """Get the names of all containers in the object.
    
    Args:
        obj (dict): K8s object to parse.
    
    Returns:
        list: A list of container names.
    """

    container_list = []

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    for container in obj["containers"]:
        container_list.append(container["name"])

    if "initContainers" in obj and obj["initContainers"] is not None and obj["initContainers"]:
        for container in obj["initContainers"]:
            container_list.append(container["name"])

    return container_list


def set_apparmor(obj: dict, cont_name="", profile="runtime/default"):
    """Set the runtime AppArmor default profile to each K8s object.

    Policy: Containers should be configured with an AppArmor profile to 
    enforce fine-grained access control over low-level system resources
    
    Args:
        obj (dict): K8s object to modify.
        cont_name (str): The name of the container to set the apparmorProfile to.
        profile (str): The name to set the apparmorProfile to.
    """

    if not cont_name:
        container_list = get_container_names(obj)
    else:
        container_list = [cont_name]

    for cont_name in container_list:
        aux = "container.apparmor.security.beta.kubernetes.io/" + cont_name

        if "template" in obj["spec"]:
            obj = obj["spec"]["template"]

        # If metadata not in obj, add it
        if "metadata" not in obj or obj["metadata"] is None or \
                not obj["metadata"]:
            obj["metadata"] = {
                "annotations": {
                    aux: profile
                }
            }

        # If annotations not in metadata, add it
        elif "annotations" not in obj["metadata"] or \
            obj["metadata"]["annotations"] is None or \
                not obj["metadata"]["annotations"]:
            obj["metadata"]["annotations"] = {
                aux: profile
            }
        # If annotations in metadata, add the apparmor annotation
        else:
            obj["metadata"]["annotations"][aux] = profile


def remove_storage(obj: dict):
    """Remove storage request from StatefulSet and Deployment objects.
    
    Args:
        obj (dict): K8s object to modify.
    """

    del obj["requests"]


def set_pod_deployment(obj: dict):
    """Convert Pod to Deployment object.
    
    Args:
        obj (dict): K8s object to modify.
    """

    obj["kind"] = "Deployment"


def remove_cluster_admin(obj: dict):
    """Remove cluster-admin role from ClusterRoleBinding objects.
    
    Args:
        obj (dict): K8s object to modify.
    """

    obj["roleRef"]["name"] = "view"


def set_ingress_host(obj: dict, host="*.example.com"):
    """Set the host to each Ingress object.
    
    Args:
        obj (dict): K8s object to modify.
        host (str): The name to set the host to.
    """

    for host in obj["spec"]["rules"]:
        if host["host"] == "*":
            host["host"] = "*.example.com"


def set_statefulset_service_name(obj: dict, service_name: str):
    """Set the serviceName to each StatefulSet object.
    
    Args:
        obj (dict): K8s object to modify.
        service_name (str): The name to set the serviceName to.
    """

    if service_name and service_name is not None and service_name != "":
        obj["spec"]["serviceName"] = service_name


def set_security_context(obj: dict):
    """Set the securityContext to each K8s object.

    Policy: Apply security context to your containers
    
    Args:
        obj (dict): K8s object to modify.
    """

    # Run as not-root
    set_root(obj)


def set_pid_ns(obj: dict, value=False):
    """Deny sharing the host process ID namespace to each K8s object.

    Policy: Prevent containers from sharing the host's PID namespace
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the hostPID to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    # Set "hostPID" to False
    obj["hostPID"] = value


def set_ipc_ns(obj: dict, value=False):
    """Deny sharing the host process IPC namespace to each K8s object.

    Policy: Prevent containers from sharing the host's IPC namespace
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the hostIPC to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    # Set "hostIPC" to False
    obj["hostIPC"] = value


def set_net_ns(obj: dict, value=False):
    """Deny sharing the host network namespace to each K8s object.

    Policy: Prevent containers from sharing the host's network namespace
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the hostNetwork to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    # Set "hostNetwork" to False
    obj["hostNetwork"] = value


def set_read_only(obj: dict, value=True):
    """Set readOnlyRootFilesystem to value for each K8s object.

    Policy: Ensure each container has a read-only root filesystem
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the readOnlyRootFilesystem to.
    """

    # Only set this property at the container level
    if "image" not in obj:
        return

    # If securityContext is not set, Set it
    if "securityContext" not in obj or \
        obj["securityContext"] is None or \
            not obj["securityContext"]:
        obj["securityContext"] = {
            "readOnlyRootFilesystem": value
        }
    # elIf readOnlyRootFilesystem is not set, Set it
    elif "readOnlyRootFilesystem" not in obj["securityContext"] or \
        obj["securityContext"]["readOnlyRootFilesystem"] is None or \
            not obj["securityContext"]["readOnlyRootFilesystem"]:
        obj["securityContext"]["readOnlyRootFilesystem"] = value
    # elIf readOnlyRootFilesystem is set to false, set it to true
    else:
        obj["securityContext"]["readOnlyRootFilesystem"] = value


def set_subpath(obj: dict):
    """ Remove container volume mounts with subPath
    
    Policy: Prevent container security vulnerability (CVE-2021-25741)

    Args:
        obj (dict): K8s object to modify.
    """

    if "volumeMounts" in obj and obj["volumeMounts"] is not None and obj["volumeMounts"]:
        obj["volumeMounts"] = [volume for volume in obj["volumeMounts"] if "subPath" not in volume]
        if not obj["volumeMounts"]:
            del obj["volumeMounts"]


def set_secrets_as_files(obj: dict, secret_name="my-secret", volume_name="secret-volume"):
    """
    
    Policy: Prefer using secrets as files over secrets as environment variables
    
    Args:
        obj (dict): K8s object to modify.
        volume_name (str): The name of the volume to add to the object.
    """

    # Create a secret file called volume_name
    # with open(volume_name, "w", encoding="utf-8") as file:
    #     content = secret["valueFrom"]["secretKeyRef"]["name"] + \
    #         ": " + secret["valueFrom"]["secretKeyRef"]["key"]
    #     file.write(content)

    if "volumes" not in obj or obj["volumes"] is None or not obj["volumes"]:
        obj["volumes"] = [{
            'name': volume_name,
            'secret': {
                'secretName': secret_name
            }
        }]
    # If volumes in obj, add secret volume
    else:
        obj["volumes"].append({
            'name': volume_name,
            'secret': {
                'secretName': secret_name
            }
        })

    # Remove container env secret variable
    for container in obj["containers"]:

        if "envFrom" in container:
            del container["envFrom"]

        if "env" in container and container["env"] is not None and \
                container["env"]:
            # Delete all container["env"] with valueFrom and secretKeyRef
            container["env"] = [env_var for env_var in container["env"] if 'valueFrom' not in env_var]

        # Bind secret volume to container
        # If volumeMounts not in container, add secret volume
        if "volumeMounts" not in container or container["volumeMounts"] is None or \
                not container["volumeMounts"]:
            container["volumeMounts"] = [{
                'name': volume_name,
                'readOnly': True,
                'mountPath': '/etc/' + volume_name
            }]
        else:
            container["volumeMounts"].append({
                'name': volume_name,
                'readOnly': True,
                'mountPath': '/etc/' + volume_name
            })

        # If env: null, delete env
        if "env" in container and container["env"] is None and \
            not container["env"]:
            del container["env"]


def remove_nodeport(obj: dict):
    """Remove the nodePort from each K8s Service object.
    
    Policy: Do not expose Kubernetes services on NodePort

    Args:
        obj (dict): K8s object to modify.
    """

    # Append to metadata annotations: networking.gke.io/load-balancer-type: 'Internal'
    if "annotations" in obj["metadata"] and \
            obj["metadata"]["annotations"] is not None and \
                obj["metadata"]["annotations"]:
        obj["metadata"]["annotations"]["networking.gke.io/load-balancer-type"] = "Internal"
    else:
        obj["metadata"]["annotations"] = {
            "networking.gke.io/load-balancer-type": "Internal"
        }

    # obj["spec"]["ports"] = [{
    #     "protocol": "TCP",
    #     "port": 80,
    #     "targetPort": 9376
    # }]

    # obj["spec"]["clusterIP"] = "10.0.171.239"
    obj["spec"]["type"] = "LoadBalancer"

    # obj["status"] = {
    #     "loadBalancer": {
    #         "ingress": [{
    #                 "ip": "192.0.2.127"
    #         }]
    #     }
    # }


def set_volume_mounts(obj: dict, value=True):
    """Set a container volumeMounts readOnly to value for each K8s object.
    
    Policy: Volume Mount With OS Directory Write Permissions

    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the readOnly to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    if "volumeMounts" in obj:
        for volume in obj["volumeMounts"]:
            if "readOnly" in volume:
                volume["readOnly"] = value
            else:
                volume["readOnly"] = value

    # Otherwise, iterate containers
    elif "containers" in obj:
        for container in obj["containers"]:
            for volume in container["volumeMounts"]:
                if "readOnly" in volume:
                    volume["readOnly"] = value
                else:
                    volume["readOnly"] = value


def set_cluster_roles(obj: dict):
    """Remove dangerous verbs from ClusterRoles for each K8s object.

    Policy: Kubernetes ClusterRoles that grant control over validating or 
    mutating admission webhook configurations are not minimized.

    Args:
        obj (dict): K8s object to modify.
    """

    if "rules" not in obj or obj["rules"] is None or not obj["rules"]:
        obj["rules"] = [{
            "apiGroups": [
                "v1"
            ],
            "resources": [
                "pods"
            ],
            "verbs": [
                "get"
            ]
        }]

    else:
        delete_idx = []
        for idx, rule in enumerate(obj["rules"]):

            if "apiGroups" in rule:
                if rule["apiGroups"] is None:
                    rule["apiGroups"] = ["v1"]
                elif rule["apiGroups"] == ["*"]:
                    rule["apiGroups"] = ["v1"]
                elif rule["apiGroups"] == [""]:
                    rule["apiGroups"] = ["v1"]

            if "resources" in rule:
                if rule["resources"] is None:
                    rule["resources"] = ["pods"]

                elif rule["resources"] == ["*"]:
                    rule["resources"] = ["pods"]

                if "pods/exec" in rule["resources"]:
                    delete_idx.append(idx)

                if "secrets" in rule["resources"]:
                    delete_idx.append(idx)

                if "events" in rule["resources"]:
                    delete_idx.append(idx)

            if "nonResourceURLs" in rule:
                delete_idx.append(idx)

            if "verbs" in rule:
                if rule["verbs"] == ["*"]:
                    rule["verbs"] = ["get"]
                else:
                    unsafe_verbs = ["create", "update", "patch", "escalate", "approve", \
                                    "list", "watch", "delete", "impersonate"]
                    rule["verbs"] = [verb for verb in rule["verbs"] if verb not in unsafe_verbs]
                if rule["verbs"] is None:
                    rule["verbs"] = ["get"]
                elif rule["verbs"] == [""] or rule["verbs"] == []:
                    rule["verbs"] = ["get"]

        delete_idx = list(set(delete_idx))
        for idx in sorted(delete_idx, reverse=True):
            obj["rules"].pop(idx)


def set_deadline_seconds(obj: dict, value=100):
    """Set the deadlineSeconds for CronJob objects.
    
    Policy: CronJob should have a deadlineSeconds set
    
    Args:
        obj (dict): K8s object to modify.
        value (int): The value to set the deadlineSeconds to.
    """

    obj["spec"]["startingDeadlineSeconds"] = value


def set_service_account(obj: dict, value=False):
    """Set ServiceAccount from each K8s object.

    Policy: Prevent service account token auto-mounting on pods
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the automountServiceAccountToken to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]
    obj["automountServiceAccountToken"] = value


def set_service_account_name(obj: dict, value="SAtest"):
    """Set ServiceAccount for each K8s object.

    Policy: The attribute 'serviceAccountName' should be defined and not empty.
    
    Args:
        obj (dict): K8s object to modify.
        value (str): The value to set the serviceAccountName to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]["spec"]

    global service_account_idx
    obj["serviceAccountName"] = value + str(service_account_idx)
    obj["automountServiceAccountToken"] = False
    service_account_idx += 1


def set_k8s_ns(obj: dict, value="test-ns"):
    """Set the test namespace for each K8s object.

    Policy: Prevent workload from using the default namespace
    
    Args:
        obj (dict): K8s object to modify.
        value (str): The value to set the namespace to.
    """

    obj["metadata"]["namespace"] = value


def set_img_pull_policy(obj: dict, value="Always"):
    """Set Image Pull Policy to Always for each K8s object.

    Policy: Ensure image pull policy is set to Always
    
    Args:
        obj (dict): K8s object to modify.
        value (str): The value to set the pullPolicy to.
    """

    obj["imagePullPolicy"] = value


def set_label_values(obj: dict):
    """Set Label Values for a K8s resource.
    
    Policy: Ensure workload has valid label values

    Args:
        obj (dict): K8s object to modify.
    """

    if "metadata" not in obj or obj["metadata"] is None:
        obj["metadata"] = {}

    if "labels" in obj["metadata"] and obj["metadata"]["labels"] is not None:
        obj["metadata"]["labels"]["app.kubernetes.io/name"] = "MyApp"
        obj["metadata"]["labels"]["app"] = "MyApp"
    else:
        obj["metadata"]["labels"] = {"app.kubernetes.io/name": "MyApp"}
        obj["metadata"]["labels"] = {"app": "MyApp"}

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]
        elif "jobTemplate" in obj:
            obj = obj["jobTemplate"]["spec"]["template"]

    if "metadata" not in obj or obj["metadata"] is None:
        obj["metadata"] = {}

    if "labels" in obj["metadata"] and obj["metadata"]["labels"] is not None:
        obj["metadata"]["labels"]["app.kubernetes.io/name"] = "MyApp"
        obj["metadata"]["labels"]["app"] = "MyApp"
    else:
        obj["metadata"]["labels"] = {"app.kubernetes.io/name": "MyApp"}
        obj["metadata"]["labels"] = {"app": "MyApp"}


def set_replicas(obj: dict, value=2):
    """Set the replicas key for a K8s Deployment
    
    Policy: Ensure Deployment has more than one replica configured.

    Args:
        obj (dict): K8s object to modify.
        value (int): The value to set the replicas to.    
    """

    obj["spec"]["replicas"] = value


def set_pod_disruption_budget(obj: dict, app_name="test-pdb"):
    """Set PodDisruptionBudget for a K8s StatefulSet.
    
    Policy: StatefulSets should be assigned with a PodDisruptionBudget to ensure high availability.
    
    Args:
        obj (dict): K8s object to modify.
    """

    # Set StatefulSet matchLabels to app_name
    # Add app matchLabel and set it to app_name
    obj["app"] = app_name
    pdb = {
        "apiVersion": "policy/v1",
        "kind": "PodDisruptionBudget",
        "metadata": {
            "name": "myapp-pdb"
        },
        "spec": {
            "maxUnavailable": 1,
            "selector": {
                "matchLabels": {
                    "app": app_name
                }
            }
        }
    }
    return pdb


def assign_service(obj: dict):
    """Assign a Service to a K8s DeploymentLike object.
    
    Policy: no pods found matching service labels.
    
    Args:
        obj (dict): K8s object to modify.
    """

    # Example: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
    # Service: ["selector"]["app"] = "my-app"
    # Deployment:
    #  - .spec.template.metadata.labels = "my-app"
    #  - .spec.selector.matchLabels = "my-app"
    # Service["namespace"] == Deployment["namespace"]

    # IMPORTANT. Usually, this check fails when a tool only fix the default
    # namespace of the DeploymentLike, but not the Service namespace.

    return


def remove_ssh_port(obj: dict):
    """Remove the SSH port from each K8s container object.
    
    Policy: Do not expose SSH ports
    
    Args:
        obj (dict): K8s container object to modify.
    """

    delete_idx = []
    for idx, port in enumerate(obj["ports"]):
        if "containerPort" in port and port["containerPort"] is not None:
            if port["containerPort"] == 22:
                delete_idx.append(idx)

    delete_idx = list(set(delete_idx))
    for idx in sorted(delete_idx, reverse=True):
        obj["ports"].pop(idx)


def set_pdb_max_unavailable(obj: dict, value=1):
    """Set maxUnavailable for a K8s PodDisruptionBudget.
    
    Policy: Ensure PodDisruptionBudget has maxUnavailable greater than 0.
    
    Args:
        obj (dict): K8s object to modify.
        value (int): The value to set the maxUnavailable to.
    """

    obj["spec"]["maxUnavailable"] = value


def assign_service_account(obj: dict):
    """Assign a ServiceAccount to a K8s DeploymentLike object.
    
    Policy: no pods found matching service account labels.
    
    Args:
        obj (dict): K8s object to modify.
    """

    # Similar as for assign_service, also this check usually fails when a tool
    # only fix the default namespace of the DeploymentLike, but not the
    # ServiceAccount namespace.

    return


def remove_sa_subjects(obj: dict):
    """Remove ServiceAccount Subjects from a K8s RoleBinding.
    
    Policy: Ensure that ServiceAccount subjects are not used
    
    Args:
        obj (dict): K8s object to modify.
    """

    if "subjects" in obj:
        # Delete subjects
        del obj["subjects"]


def set_img_tag(obj: dict):
    """Set Image Tag for each K8s object.

    Policy: Ensure each container image has a pinned (tag) version
    
    Args:
        obj (dict): K8s object to modify.
    """

    if ":" in obj["image"]:
        return obj

    # Get the latest image tag which is not "latest"
    image_tag = get_docker_img_tag(obj["image"])
    # Set Image Tag
    if image_tag:
        obj["image"] = obj["image"] + ":" + image_tag


def set_img_digest(obj: dict):
    """Set Image Digest for each K8s object.

    Policy: Ensure each container image has a digest tag

    Args:
        obj (dict): K8s object to modify.
    """

    if "image" in obj:
        if "@" in obj["image"]:
            return obj

        image_name, image_tag = "", ""

        if ":" in obj["image"]:
            image_name, image_tag = obj["image"].split(":")
        else:
            image_name = obj["image"]

        container = image_name.split("/")
        image_tag = get_docker_img_tag(container[-1])

        if image_tag:
            # Get the image digest
            image_digest = get_docker_img_digest(container[-1], image_tag)
            obj["image"] = image_name + ":" + image_tag + "@" + image_digest


def set_net_policy(name="test-network-policy") -> dict:
    """Returns a network policy for each K8s object.

    Policy: Minimize the admission of pods which lack an associated NetworkPolicy

    Args:
        name (str): The name to set the networkPolicy to.
    """

    # Checkov Network Policy
    net_policy1 = {
        'apiVersion': 'networking.k8s.io/v1',
        'kind': 'NetworkPolicy',
        'metadata': {
            'name': name
        },
        'spec': {
            'podSelector': {},
            'ingress': [{}],
            'policyTypes': ['Ingress']
        }
    }

    # Kubescape Network Policy
    net_policy2 = {
        'apiVersion': 'networking.k8s.io/v1',
        'kind': 'NetworkPolicy',
        'metadata': {
            'name': name,
            'namespace': 'test-ns'
        },
        'spec': {
            'podSelector': {},
            'policyTypes': ['Ingress', 'Egress'],
            'ingress': [{
                'from': [{
                    'ipBlock': {
                        'cidr': '172.17.0.0/16',
                        'except': ['172.17.1.0/24']
                    }
                }, {
                    'namespaceSelector': {
                        'matchLabels': {
                            'project': 'myproject'
                        }
                    }
                }, {
                    'podSelector': {
                        'matchLabels': {
                            'role': 'frontend'
                        }
                    }
                }],
                'ports': [{
                    'protocol': 'TCP',
                    'port': 6379
                }]
            }],
            'egress': [{
                'to': [{
                    'ipBlock': {
                        'cidr': '10.0.0.0/24'
                    }
                }],
                'ports': [{
                    'protocol': 'TCP',
                    'port': 5978
                }]
            }]
        }
    }

    return net_policy1, net_policy2


def todo(arg1="", arg2="", arg3=""):
    """TODO"""


class FuncLookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
    "check_0": set_img_tag, 
    "check_1": set_memory_request,
    "check_2": set_memory_limit,
    "check_3": set_equal_requests,
    "check_4": set_cpu_request,
    "check_5": set_cpu_limit,
    "check_6": set_equal_requests, 
    "check_7": set_liveness_probe,
    "check_8": set_readiness_probe,
    "check_9": set_img_digest,
    "check_10": set_pid_ns,
    "check_11": set_ipc_ns,
    "check_12": set_net_ns,
    "check_13": set_uid,
    "check_14": set_root,
    "check_15": remove_docker_socket, 
    "check_16": todo,
    "check_17": todo,
    "check_18": todo,
    "check_19": todo,
    "check_20": todo,
    "check_21": set_privileged,
    "check_22": set_priv_esc,
    "check_23": set_capabilities,
    "check_24": set_capabilities,
    "check_25": set_img_pull_policy,
    "check_26": set_k8s_ns,
    "check_27": set_read_only,
    "check_28": set_root,
    "check_29": set_host_port, # hostPort
    "check_30": set_security_context,
    "check_31": set_seccomp,
    "check_32": set_apparmor,
    "check_33": set_secrets_as_files, 
    "check_34": set_capabilities,
    "check_35": set_service_account,
    "check_36": set_service_account,
    "check_37": set_service_account_name,
    "check_38": todo, # K8s dashboard
    "check_39": todo, # wildcard RBAC
    "check_40": set_net_policy, 
    "check_41": todo, # sysctls
    "check_42": todo, # container pre-stop hook
    "check_43": set_label_values, # valid label values
    "check_44": todo, # valid restart policy
    "check_45": set_replicas, # deployment >1 replicas
    "check_46": todo, # owner label
    "check_47": remove_host_path, # access underlying host
    "check_48": set_limit_range, # limit range
    "check_49": set_resource_quota, # resource quota
    "check_50": set_subpath,
    "check_52": remove_storage,
    "check_53": set_statefulset_service_name,
    "check_54": set_cluster_roles,
    "check_55": set_volume_mounts,
    "check_56": remove_nodeport,
    "check_57": assign_service,
    "check_58": assign_service_account,
    "check_59": remove_sa_subjects,
    "check_60": set_pod_disruption_budget,
    "check_62": todo,
    "check_63": set_deadline_seconds,
    "check_64": set_pod_deployment,
    "check_65": remove_cluster_admin, 
    "check_66": set_ingress_host,
    "check_67": set_pdb_max_unavailable,
    "check_68": remove_ssh_port,
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
