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

""" This script implements the fixes (adding/removing lines) into a Helm Chart YAML template
"""

from typing import Callable, Optional
import yaml
import requests


def parse_yaml_comments(chart_folder: str) -> list:
    """Parses a yaml file and returns lines starting with #.

    Args:
        chart_folder: The name of the Helm Chart to parse.

    Returns:
        A list containing the parsed lines.
    """

    file_path = chart_folder + "/" + chart_folder + "_template.yaml"
    with open(file_path, "r", encoding="utf-8") as file:
        comments = [line for line in file if line.startswith("#")]

        # Remove "# Source: " from each comments's element
        comments = [comment.replace("# Source: ", "") for comment in comments]
        comments = [comment.replace("\n", "") for comment in comments]

    return comments


def parse_yaml_template(chart_folder: str) -> list:
    """Parses a Helm chart template yaml file and returns it as a dictionary.

    Args:
        chart_folder: The name of the Helm Chart to parse.

    Returns:
        A dictionary containing the parsed contents of the template.yaml file.
    """

    # Parse and return the multi-document YAML file while preserving comments
    file_path = "templates/" + chart_folder + "_template.yaml"
    # file_path = "test_files/redis_template.yaml"
    with open(file_path, "r", encoding="utf-8") as file:
        return list(yaml.load_all(file, Loader=yaml.FullLoader))


def save_yaml_template(template: str, chart_folder: str):
    """Save chart template data to a file.

    Args:
        template: A dictionary containing the template data to be saved.
        chart_folder: The name of the Helm Chart to save.

    Raises:
        IOError: If there is an error writing to the file.
    """

    # comments = parse_yaml_comments(chart_folder)

    file_path = "templates/" + chart_folder + "_template.yaml"
    # file_path = "test_files/redis_fixed_template.yaml"
    with open(file_path, 'w', encoding="utf-8") as file:
        yaml.safe_dump_all(template, file, sort_keys=False)
        # yaml.safe_dump_all(json.dumps(template).strip())

    # Write each comment after the string --- in the file
    # with open(file_path, 'r', encoding="utf-8") as file:
    #     lines = file.readlines()

    #     if comments:
    #         aux = "# Source: " + comments.pop(0) + "\n"
    #         lines = ["---\n", aux] + lines

    #     for index, line in enumerate(lines[2:]):
    #         if line.endswith("\n"):
    #             line = line.rstrip("\n")

    #         # If line is ---, add the first comment in comments
    #         if comments and "---" in line:
    #             aux = "# Source: " + comments.pop(0) + "\n"
    #             lines.insert(index+3, aux)

    # # Write contents to file
    # with open(file_path, 'w', encoding="utf-8") as file:
    #     file.writelines(lines)


def get_latest_image_tag(image_name: str) -> Optional[str]:
    """
    Retrieves the latest container image tag that is not "latest" for a given image name
    using the Docker Registry HTTP API.

    Args:
        image_name (str): A string representing the name of the container image to 
        retrieve the tag for.

    Returns:
        A string representing the latest image tag that is not "latest", or None 
        if no such tag exists.
    """

    # Build the API endpoint URL
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


def get_image_digest(image_name: str, image_tag: str) -> str:
    """Retrieves the digest of a Docker image with the given name and tag, using
    the specified Docker Hub access token for authentication.

    Args:
        image_name: A string representing the name of the Docker image.
        image_tag: A string representing the tag of the Docker image.

    Returns:
        A string representing the digest of the Docker image.
    """

    # Build the API endpoint URL
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

    if document["kind"] == path_list[0]:

        if "namespace" in document["metadata"]:

            # Ignore default ns
            if document["metadata"]["namespace"] == "default":
                return document["metadata"]["name"] == path_list[-1]

            # If the namespace was added during fixing, ignore it
            elif document["metadata"]["namespace"] == "test-ns":
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


def set_template(template: dict, check_id: str, check: dict) -> None:
    """Change the chart template for the Helm Chart.
    
    Args:
        template: The template to change.
        check_id: The ID of the check to change.
        check: The dictionary container resource_path, object_path and value.
    
    Returns: None
    """

    # If Network Policy missing issue, create and append one
    if check_id == "check_40":
        if check:
        # Find resource name
            for document in template:
                if check_resource_path(check["resource_path"].split("/"), document):
                    if "labels" in document["metadata"] and \
                        "app" in document["metadata"]["labels"]:
                        app = document["metadata"]["labels"]["app"]
                        break

        # Append Network Policy to the template
        net_policy1, net_policy2 = set_net_policy()
        template.append(net_policy1)
        template.append(net_policy2)

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

                    no_path_checks = ["check_31", "check_29", "check_26"]
                    if check_id in no_path_checks:
                        process_func(obj)
                        break

                    if check_id == "check_32":
                        process_func(obj, check["obj_path"])
                        break

                    if check_id == "check_35":
                        process_func(obj)
                        break

                    if check_id == "check_33":
                        if "template" in obj["spec"]:
                            process_func(obj["spec"]["template"]["spec"])
                        else:
                            process_func(obj["spec"])
                        break

                    # For KICS, do not iterate keys
                    if check_id == "check_36":
                        if "automountServiceAccountToken" in obj:
                            keys = []

                    for key in keys:
                        if key:
                            if key.isdigit():
                                key = int(key)
                            obj = obj[key]

                    if check_id in ("check_23", "check_24", "check_34"):
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
                        limit_range = process_func(obj)
                        template.append(limit_range)

                    elif check_id == "check_49":
                        # Append namespace ResourceQuota to the template
                        resource_quota = process_func(obj)
                        template.append(resource_quota)

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

    insecure_caps = ["ALL", "All", "all", "BPF", "MAC_ADMIN", "MAC_OVERRIDE", "NET_ADMIN",
                     "NET_RAW", "SETPCAP", "PERFMON", "SYS_ADMIN", "SYS_BOOT", "SYS_MODULE", 
                     "SYS_PTRACE", "SYS_RAWIO"]

    if "securityContext" not in obj:
        obj["securityContext"] = {
            "capabilities": {
                "drop": drop
            }
        }

    # If no "capabilities" in securityContext, add "capabilities" and set drop to all
    elif "capabilities" not in obj["securityContext"]:
        obj["securityContext"]["capabilities"] = {
            "drop": drop
        }

    # If "capabilities" in securityContext, but insecure capabilities are granted,
    # drop only insecure ones
    if "add" in obj["securityContext"]["capabilities"] and \
        set(obj["securityContext"]["capabilities"]["add"]).intersection(insecure_caps):

        # Remove insecure capabilities from "add"
        obj["securityContext"]["capabilities"]["add"] = [cap \
            for cap in obj["securityContext"]["capabilities"]["add"]
                if cap not in insecure_caps
        ]

        # If add is not empty, add capabilities from argument
        if add:
            obj["securityContext"]["capabilities"]["add"] += add

        # If "add" is empty, delete it
        if not obj["securityContext"]["capabilities"]["add"]:
            del obj["securityContext"]["capabilities"]["add"]

    # If add not in "capabilities", but the add argument is set, add it
    elif add:
        obj["securityContext"]["capabilities"]= {
                "add": add
        }

    if "add" not in obj["securityContext"]["capabilities"]:
        if "drop" in obj["securityContext"]["capabilities"]:
            obj["securityContext"]["capabilities"]["drop"] = drop
        else:
            obj["securityContext"]["capabilities"]= {
                "drop": drop
            }

    elif obj["securityContext"]["capabilities"]["add"] != "all":

        insecure_caps.remove("ALL")
        insecure_caps.remove("All")
        insecure_caps.remove("all")

        drop = [cap for cap in drop \
                if cap not in obj["securityContext"]["capabilities"]["add"]]

        obj["securityContext"]["capabilities"]["drop"] = drop


def set_cpu_limit(obj: dict, value="250m"):
    """Set the CPU limit to each K8s object.

    Policy: CPU limits should be set
    
    Args:
        obj (dict): K8s object to modify.
        value (str): value to set the CPU limit to.
    """

    # If resources is not set, Set it
    if "resources" not in obj:
        obj["resources"] = {
            "limits": {
                "cpu": value
            }
        }
    # If resources is set, but limits is not, Set it
    elif "limits" not in obj["resources"]:
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
    if "resources" not in obj:
        obj["resources"] = {
            "requests": {
                "cpu": value
            }
        }
    # If resources is set, but requests is not, Set it
    elif "requests" not in obj["resources"]:
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
    if "resources" not in obj:
        obj["resources"] = {
            "limits": {
                "memory": value
            }
        }
    # If resources is set, but limits is not, Set it
    elif "limits" not in obj["resources"]:
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
    if "resources" not in obj:
        obj["resources"] = {
            "requests": {
                "memory": value
            }
        }
    # If resources is set, but requests is not, Set it
    elif "requests" not in obj["resources"]:
        obj["resources"]["requests"] = {
            "memory": value
        }

    else:
        obj["resources"]["requests"]["memory"] = value


def set_limit_range(obj: dict) -> dict:
    """Set cpu and memory limits to each K8s object.

    Policy: CPU and Memory limits should be set
    
    Args:
        obj (dict): K8s object to modify.

    Returns:
        dict: LimitRange object
    """

    namespace = obj["metadata"]["namespace"]
    if namespace == "default":
        namespace = "test-ns"
    limit_range = {
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
    return limit_range


def set_resource_quota(obj: dict) -> dict:
    """Set priorityClassName to each K8s object.

    Policy: Each namespace should have a ResourceQuota policy associated to limit the total amount
    of resources Pods, Containers and PersistentVolumeClaims can consume
    
    Args:
        obj (dict): K8s object to modify.

    Returns:
        dict: ResourceQuota object
    """

    namespace = obj["metadata"]["namespace"]
    if namespace == "default":
        namespace = "test-ns"
    resource_quota = {
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
    return resource_quota


def set_uid(obj: dict, uid=25000):
    """Set the uid for a K8s object.
    
    Args:
        obj (dict): K8s object to modify.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]

    # If securityContext is not set, Set it
    if "securityContext" not in obj:
        obj["securityContext"] = {
            "runAsUser": uid
        }
    # If securityContext is set, but runAsUser is not, Set it
    elif "runAsUser" not in obj["securityContext"]:
        obj["securityContext"]["runAsUser"] = uid

    else:
        obj["securityContext"]["runAsUser"] = uid

    if "containers" in obj:
        # Set runAsUser for each container
        for container in obj["containers"]:
            if "securityContext" not in container:
                container["securityContext"] = {
                    "runAsUser": uid
                }
            elif "runAsUser" not in container["securityContext"]:
                container["securityContext"]["runAsUser"] = uid
            else:
                container["securityContext"]["runAsUser"] = uid
    else:
        obj["securityContext"]["runAsUser"] = uid


def set_root(obj: dict, value=True, uid=25000):
    """Set the root user to each K8s object.

    Policy: Minimize the admission of root containers
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the root user to.
        uid (int): The value to set the runAsUser to.
        gid (int): The value to set the runAsGroup to.
        fsg (int): The value to set the fsGroup to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]

    # If securityContext is not set in containers, Set it
    if "securityContext" not in obj:
        obj["securityContext"] = {
            "runAsNonRoot": value,
            "runAsUser": uid
        }
    # If runAsNonRoot is not set in securityContext, Set it
    else:
        obj["securityContext"]["runAsNonRoot"] = value

    # If runAsUser is not set in securityContext, Set it
    if "runAsUser" not in obj["securityContext"]:
        obj["securityContext"]["runAsUser"] = uid


def set_non_root(obj: dict, value=True, uid=25000):
    """Set the root user to each K8s object.

    Policy: Minimize the admission of root containers
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the root user to.
        uid (int): The value to set the runAsUser to.
    """

    if "spec" in obj:
        obj = obj["spec"]
        if "template" in obj:
            obj = obj["template"]["spec"]

    # If securityContext is not set in containers, Set it
    if "securityContext" not in obj:
        obj["securityContext"] = {
            "runAsNonRoot": value,
            "runAsUser": uid,
        }
    # If runAsNonRoot is not set in securityContext, Set it
    else:
        obj["securityContext"]["runAsNonRoot"] = value

    # If runAsUser is not set in securityContext, Set it
    if "runAsUser" not in obj["securityContext"]:
        obj["securityContext"]["runAsUser"] = uid


def set_priv_esc(obj: dict, value=False):
    """Set allowPrivilegeEscalation to false for each K8s object.

    Policy: Containers should not run with allowPrivilegeEscalation
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the allowPrivilegeEscalation to.
    """

    # If securityContext is not set, Set it
    if "securityContext" not in obj:
        obj["securityContext"] = {
            "allowPrivilegeEscalation": value
        }
    # If allowPrivilegeEscalation is not set, Set it
    elif "allowPrivilegeEscalation" not in obj["securityContext"]:
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


def set_seccomp(obj: dict, profile="runtime/default"):
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

    if "template" in obj["spec"]:
        if "annotations" not in obj["spec"]["template"]["metadata"]:
            obj["spec"]["template"]["metadata"]["annotations"] = {
                "seccomp.security.alpha.kubernetes.io/defaultProfileName": profile
            }
        # If annotations is set, but seccomp.security.alpha.kubernetes.io/
        #  defaultProfileName is not, Set it
        else:
            obj["spec"]["template"]["metadata"]["annotations"]["seccomp.security.alpha.kubernetes.io/defaultProfileName"] = profile

    elif "annotations" not in obj["metadata"]:
        obj["metadata"]["annotations"] = {
            "seccomp.security.alpha.kubernetes.io/defaultProfileName": profile
        }
    # If annotations is set, but seccomp.security.alpha.kubernetes.io/ 
    # defaultProfileName is not, Set it
    else:
        obj["metadata"]["annotations"]["seccomp.security.alpha.kubernetes.io/defaultProfileName"] = profile

    ###############################################

    # If template in obj spec, set obj to template
    if "template" in obj["spec"]:
        # If a securityContext already exists, set seccomp profile
        if "securityContext" in obj["spec"]["template"]["spec"]:
            obj["spec"]["template"]["spec"]["securityContext"]["seccompProfile"] = {
                "type": "RuntimeDefault"
            }
        # else, add securityContext and set seccomp profile
        else:
            obj["spec"]["template"]["spec"]["securityContext"] = {
                "seccompProfile": {
                    "type": "RuntimeDefault"
                }
            }
    # If no template, add to obj spec
    else:
        # If a securityContext already exists, set seccomp profile
        if "securityContext" in obj["spec"]:
            obj["spec"]["securityContext"]["seccompProfile"] = {
                "type": "RuntimeDefault"
            }
        # else, add securityContext and set seccomp profile
        else:
            obj["spec"]["securityContext"] = {
                "seccompProfile": {
                    "type": "RuntimeDefault"
                }
            }


def set_apparmor(obj: dict, cont_name: str, profile="runtime/default"):
    """Set the runtime AppArmor default profile to each K8s object.

    Policy: Containers should be configured with an AppArmor profile to 
    enforce fine-grained access control over low-level system resources
    
    Args:
        obj (dict): K8s object to modify.
        cont_name (str): The name of the container to set the apparmorProfile to.
        profile (str): The name to set the apparmorProfile to.
    """

    # if not cont_name, get the name of the first container in containers
    if not cont_name:
        if "template" in obj["spec"]:
            cont_name = obj["spec"]["template"]["spec"]["containers"][0]["name"]
        else:
            cont_name = obj["spec"]["containers"][0]["name"]

    aux = "container.apparmor.security.beta.kubernetes.io/" + cont_name

    if "template" in obj["spec"]:
        obj = obj["spec"]["template"]

    # If metadata not in obj, add it
    if "metadata" not in obj:
        obj["metadata"] = {
            "annotations": {
                aux: profile
            }
        }

    # If annotations not in metadata, add it
    elif "annotations" not in obj["metadata"]:
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


def set_statefulset_service_name(obj: dict, name: str):
    """Set the serviceName to each StatefulSet object.
    
    Args:
        obj (dict): K8s object to modify.
        name (str): The name to set the serviceName to.
    """

    obj["spec"]["serviceName"] = name


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

    # Set "hostPID" to False
    obj["spec"]["hostPID"] = value


def set_ipc_ns(obj: dict, value=False):
    """Deny sharing the host process IPC namespace to each K8s object.

    Policy: Prevent containers from sharing the host's IPC namespace
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the hostIPC to.
    """

    # Set "hostIPC" to False
    obj["spec"]["hostIPC"] = value


def set_net_ns(obj: dict, value=False):
    """Deny sharing the host network namespace to each K8s object.

    Policy: Prevent containers from sharing the host's network namespace
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the hostNetwork to.
    """

    # Set "hostNetwork" to False
    obj["spec"]["hostNetwork"] = value


def set_read_only(obj: dict, value=True):
    """Set readOnlyRootFilesystem to value for each K8s object.

    Policy: Ensure each container has a read-only root filesystem
    
    Args:
        obj (dict): K8s object to modify.
        value (bool): The value to set the readOnlyRootFilesystem to.
    """

    # If securityContext is not set, Set it
    if "securityContext" not in obj:
        obj["securityContext"] = {
            "readOnlyRootFilesystem": value
        }
    # elIf readOnlyRootFilesystem is not set, Set it
    elif "readOnlyRootFilesystem" not in obj["securityContext"]:
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

    for volume in obj["volumeMounts"]:
        if "subPath" in volume:
            del volume["subPath"]


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

    # If volumes not in obj, add secret volume
    if "volumes" not in obj:
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

        if "env" in container:
            # Delete all container["env"] with valueFrom and secretKeyRef
            container["env"] = [env_var for env_var in container["env"] if 'valueFrom' not in env_var]

        # Bind secret volume to container
        # If volumeMounts not in container, add secret volume
        if "volumeMounts" not in container:
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

    # Set "automountServiceAccountToken" to value
    obj["automountServiceAccountToken"] = value


def set_service_account_name(obj: dict, value="SAtest"):
    """Set ServiceAccount for each K8s object.

    Policy: The attribute 'serviceAccountName' should be defined and not empty.
    
    Args:
        obj (dict): K8s object to modify.
        value (str): The value to set the serviceAccountName to.
    """

    # Set "serviceAccountName" to testAT
    obj["serviceAccountName"] = value


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

    # Set Image Pull Policy
    obj["imagePullPolicy"] = value


def set_label_values(obj: dict):
    """Set Label Values for a K8s resource.
    
    Policy: Ensure workload has valid label values

    Args:
        obj (dict): K8s object to modify.
    """

    # Labels: app, tier, phase, version, owner, env

    obj["metadata"]["labels"]["app"] = "my-app"

    if "template" in obj["spec"]:
        obj["spec"]["template"]["metadata"]["labels"]["app"] = "my-app"


def set_img_tag(obj: dict):
    """Set Image Tag for each K8s object.

    Policy: Ensure each container image has a pinned (tag) version
    
    Args:
        obj (dict): K8s object to modify.
    """

    if ":" in obj["image"]:
        return obj

    # Get the latest image tag which is not "latest"
    image_tag = get_latest_image_tag(obj["image"])
    # Set Image Tag
    if image_tag:
        obj["image"] = obj["image"] + ":" + image_tag


def set_img_digest(obj: dict):
    """Set Image Digest for each K8s object.

    Policy: Ensure each container image has a digest tag

    Args:
        obj (dict): K8s object to modify.
    """

    if "@" in obj["image"]:
        return obj

    image_name, image_tag = "", ""

    if ":" in obj["image"]:
        image_name, image_tag = obj["image"].split(":")
    else:
        image_name = obj["image"]

    cont_name = image_name.split("/")[-1]
    image_tag = get_latest_image_tag(cont_name)

    if image_tag:
        # Get the image digest
        image_digest = get_image_digest(cont_name, image_tag)
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


def todo():
    """TODO"""


class FuncLookupClass:
    """This class is used to lookup the function to be called for each check.
    """

    _LOOKUP = {
    "check_0": set_img_tag, 
    "check_1": set_memory_request,
    "check_2": set_memory_limit,
    "check_3": todo, # memory requests not equal to it's limit
    "check_4": set_cpu_request,
    "check_5": set_cpu_limit,
    "check_6": todo, # cpu requests not equal to it's limit
    "check_7": set_liveness_probe,
    "check_8": set_readiness_probe,
    "check_9": set_img_digest,
    "check_10": set_pid_ns,
    "check_11": set_ipc_ns,
    "check_12": set_net_ns,
    "check_13": set_uid,
    "check_14": set_root,
    "check_15": todo, # mounting Docker socket
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
    "check_33": set_secrets_as_files, # secrets as files over env vars
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
    "check_45": todo, # deployment >1 replicas
    "check_46": todo, # owner label
    "check_47": todo, # access underlying host
    "check_48": set_limit_range, # limit range
    "check_49": set_resource_quota, # resource quota
    "check_50": set_subpath,
    "check_52": remove_storage,
    "check_53": set_statefulset_service_name
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
