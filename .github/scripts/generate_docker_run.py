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

""" This script converts a chart YAML template container definition to a docker run command.
"""

import fix_template


def yaml_to_docker_run(container: dict) -> str:
    """Converts a chart YAML template container definition to a docker run command.
    
    Args:
        container (dict): The dictionary container definition.

    Returns:
        str: The docker run command.
    """

    # Extract container name and image
    name = container['name']
    image = container['image']

    # Extract security context details
    security_context = container.get('securityContext', {})

    privileged = security_context.get('privileged', '')
    if privileged and privileged is True:
        privileged = "--privileged"
    cap_add = "--cap-add"
    cap_add += " ".join(security_context.get('capabilities', {}).get('add', []))
    cap_drop = "--cap-drop"
    cap_drop += " ".join(security_context.get('capabilities', {}).get('drop', []))
    allow_priv_esc = f"--security-opt='no-new-privileges={security_context.get('allowPrivilegeEscalation', '')}'"
    seccomp = f"--security-opt='seccomp={security_context.get('seccompProfile', '')}'"
    # apparmor = f"--security-opt='seccomp={security_context.get('apparmorProfile', '')}'"
    read_only = security_context.get('readOnlyRootFilesystem', '')
    if read_only and read_only is True:
        read_only = "--read-only"

    # Extract user
    run_as_user = security_context.get('runAsUser')
    run_as_group = security_context.get('runAsGroup')
    user = f"--user={run_as_user}"
    if run_as_group:
        user += ":{run_as_group}"

    # Namespaces (network, PID, IPC, UTS)
    # TODO

    # Extract environment variables
    env_variables = container.get('env', [])
    env_command = ""

    for env in env_variables:
        if env.get('value', ''):
            env_command += f"--env {env['name']}={env.get('value', '')} "
        else:
            env_command += f"--env {env['name']}="
            env_command += str(env['valueFrom']['secretKeyRef']['key']) + " "

    # Extract port mappings
    ports = container.get('ports', [])
    port_mappings = [f"{port['containerPort']}:{port['containerPort']}" for port in ports]

    # Extract resources
    limits_memory = container.get('limits', {}).get('memory', '')
    # requests_memory = container.get('requests', {}).get('memory', '')

    # Extract volume details
    volumes = container.get('volumes', [])
    volume_mappings = [f"{volume['name']}:/path/to/{volume['name']}" for volume in volumes]
    # TODO



    # Build the docker run command string
    docker_run_cmd = "docker run -d " + (f"--name {name} " if name else "") + " " + \
                    (cap_add if cap_add != "--cap-add" else "" ) + " " + \
                    (cap_drop if cap_drop != "--cap-drop" else "") + " " + \
                    (privileged if privileged else "") + " " + \
                    (allow_priv_esc if allow_priv_esc != "--security-opt='no-new-privileges'" else "") + " " + \
                    (seccomp if seccomp != "--security-opt='seccomp='" else "") + " " + \
                    (read_only if read_only else "") + " " + \
                    (user if user else "") + " " + \
                    (env_command if env_command else "") + " " + \
                    " ".join([f"-p {mapping}" for mapping in port_mappings]) + " " + \
                    " ".join([f"--volume {mapping}" for mapping in volume_mappings]) + " " + \
                    (f"--memory {limits_memory} " if limits_memory else "") + " " + \
                    image

    return docker_run_cmd


def get_docker_run_cmd(chart_folder: str, resource_path: str, obj_path: str) -> str:
    """Gets the docker run command for the chart.

    Args:
        chart_folder (str): The name of the chart to fix.
        resource_path (str): The path to the resource file.
        obj_path (str): The path to the object in the resource file.

    Returns:
        str: The docker run command.
    """

    template = fix_template.parse_yaml_template(chart_folder)

    # Iterate through the YAML documents
    for document in template:

        if fix_template.check_resource_path(resource_path.split("/"), document):

            # Find the object
            keys = obj_path.split("/")
            cont_dict = document

            for key in keys:
                if key:
                    if key.isdigit():
                        key = int(key)
                    cont_dict = cont_dict[key]

            docker_run_cmd = yaml_to_docker_run(cont_dict)
            print(docker_run_cmd)
