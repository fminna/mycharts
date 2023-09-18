# Helm Charts Repository

[![Workflow](https://github.com/fminna/mycharts/actions/workflows/worflow.yaml/badge.svg)](https://github.com/fminna/mycharts/actions/workflows/worflow.yaml)

This repository contains a list of Helm Charts publicly available. Each folder (e.g., busybox-pod) represents a Chart.

This is a real-world example of storing Helm Charts in Github Pages, as described in the [Learning Helm](https://www.oreilly.com/library/view/learning-helm/9781492083641/) book.


## Helm Chart Templates
In the templates/ folder, you can find all Helm Charts templates generated with the `helm template` command.


## Helm Chart Fixed Templates
In the fixed_templates/ folder, you can find all Helm Charts fixed according to the output of each tool, specified in the file name. For example, `argo-cd_checkov_fixed_template.yaml` represents the argo-cd Helm Chart templated fixed according to all the issues found by Checkov.

## Helm Chart Functionalities Templates
In the functionality_templates/ folder, you can find, for each chart, the corresponding updated templates with all functionalities.

## Helm Chart Functionalities Profiles
In the functionality_profile/ folder, you can find a folder for each chart, containing the corresponding functionality profile JSON file (e.g., falco_functionality.json).

## Analyze Chart
Currently, we only support 7 Helm Chart analyzer tools, namely, Checkov, Datree, KICS, Kubelinter, Kubeaudit, Kubescape, and Terrascan. Also, the assumption to analyze a chart, is that the corresponding functionality profile is already computed and available. For testing purposes, you can use the profiles available in the functionality_profile/ folder.

### Github Actions
To analyze the Helm Charts with a pair of supported tools, you can move to the Actions tab of the repository, select `Main Workflow`, and click Run workflow on the top right by providing the name of a chart and a pair of tool names. The action will automatically scan the chart and generate an updated chart template, that will be committed to the repository at the end. To see the Action status and each step output, you can click on the running Action and further analyze each step (e.g., number of misconfigurations found by the first analyzer).

### Bash 
To compute faster results, you can also analyze all charts with all tool combinations using the bash scripts. For example, to generate all results, you can run the `./generate_all_results output` script. This latter assumes that all tools are locally installed and available. The results can either be printed in the console or saved as output files.
