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

""" Downloads Helm Charts from ArtifactHub.
"""

import requests


def download_helm_charts(num_charts: int = 100) -> None:
    """Downloads Helm Charts from ArtifactHub.

    Args:
        num_charts (int, optional): Number of charts to download. Defaults to 100.
    """

    url = "https://artifacthub.io/api/v1/packages/search"
    headers = {"Content-Type": "application/json"}
    params = {"limit": num_charts, "sort": "stars", "filters": {"kind": "helm"}}

    response = requests.get(url, headers=headers, params=params, timeout=10)
    data = response.json()

    for chart in data["packages"]:

        # print(chart["name"])
        # print(chart["stars"])
        print(chart["repository"]["name"])


if __name__ == "__main__":
    download_helm_charts(60)
