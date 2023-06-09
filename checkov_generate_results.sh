#!/bin/bash

# This script takes as input a chart name and runs all security tools on it, starting always with checkov.

# Take a chart_name variable as argument
chart_name=$1

# If not provided, exit
if [ -z "$chart_name" ]
then
    echo "No chart name provided! Exiting..."
    exit 1
fi

# Set up environment variables
export chart_folder="${chart_name}"
export tool="checkov"

# Remove previous results by deleting all files in test_files
rm -rf test_files/*

# Run Analyzers
echo "Running analyzers on $chart_name ..."

# Step 1 - Checkov
echo -e "\n -------------------------- \n"
echo "Step 1 - Run Checkov"
checkov -f templates/${chart_folder}_template.yaml --quiet --compact --framework kubernetes -o json > test_files/checkov_results.json
# python .github/scripts/main.py --count-checks

# Step 2 - Fix Checkov output
echo -e "\n -------------------------- \n"
echo "Step 2 - Fix issues"
export chart_folder="templates/${chart_folder}"
export tool="checkov"
python .github/scripts/main.py --check

# Step 3 - Debug
echo -e "\n -------------------------- \n"
echo "Step 3 - Debug"
export chart_folder="fixed_templates/${chart_folder}"
checkov -f fixed_templates/${chart_name}_checkov_fixed_template.yaml --skip-check CKV_K8S_14 --skip-check CKV_K8S_43 --skip-framework secrets --quiet --compact --framework kubernetes
# python .github/scripts/main.py --count-checks

# Step 4 - Add functionalities
echo -e "\n -------------------------- \n"
echo "Step 4 - Add functionalities"
export chart_folder="${chart_name}"
export tool="checkov"
python .github/scripts/main.py --add-func

# Step 5 - Run all tools on functional template
echo -e "\n -------------------------- \n"
echo -e "\n Step 5 - Checkov"
checkov -f functionality_templates/${chart_name}_func_template.yaml --quiet --compact --framework kubernetes -o json > test_files/checkov_results.json
export tool="checkov"
python .github/scripts/main.py --count-checks

# Datree
echo -e "\n Step 5 - Datree"
helm datree test functionality_templates/${chart_name}_func_template.yaml --only-k8s-files --quiet --output json > test_files/datree_results.json 
export tool="datree"
python .github/scripts/main.py --count-checks

# KICS
echo -e "\n Step 5 - KICS"
kics scan -p functionality_templates/${chart_name}_func_template.yaml --exclude-severities info -o test_files/ > /dev/null 2>&1
mv test_files/results.json test_files/kics_results.json
export tool="kics"
python .github/scripts/main.py --count-checks

# Kubelinter
echo -e "\n Step 5 - Kube-linter"
kube-linter lint functionality_templates/${chart_name}_func_template.yaml --format=json > test_files/kubelinter_results.json
export tool="kubelinter"
python .github/scripts/main.py --count-checks

# Kubeaudit
echo -e "\n Step 5 - Kubeaudit"
kubeaudit all -f functionality_templates/${chart_name}_func_template.yaml --format json > test_files/kubeaudit_results.json
export tool="kubeaudit"
python .github/scripts/main.py --count-checks

# Kubescape
echo -e "\n Step 5 - Kubescape"
kubescape scan functionality_templates/${chart_name}_func_template.yaml --format json --output test_files/kubescape_results.json > /dev/null 2>&1
export tool="kubescape"
python .github/scripts/main.py --count-checks

# Terrascan
echo -e "\n Step 5 - Terrascan"
terrascan scan -i k8s -f functionality_templates/${chart_name}_func_template.yaml -o sarif > test_files/terrascan_results.json
export tool="terrascan"
python .github/scripts/main.py --count-checks

echo -e "\n -------------------------- \n"
echo "Done running analyzers on $chart_name"
