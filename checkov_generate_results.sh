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

# Take an optional output boolean variable as argument
output=$2

if [ "$output" = "output" ]
then
    # Clear the content of output_final.txt
    > output_fix.txt
    > output_func.txt
    > output_final.txt
fi

# Set up environment variables
export chart_folder="${chart_name}"
export first_tool="checkov"
export iteration="1"

# Run Analyzers
echo "Running analyzers on $chart_name ..."

# Step 1 - Checkov
echo -e "\n -------------------------- \n"
echo "Step 1 - Run Checkov"
checkov -f templates/${chart_folder}_template.yaml --quiet --compact --framework kubernetes -o json > results_${iteration}.json

# Step 2 - Fix Checkov output
echo -e "\n -------------------------- \n"
echo "Step 2 - Fix issues"
python .github/scripts/main.py --check
# If output is provided, append output of --check to output_final.txt
if [ "$output" = "output" ]
then
    python .github/scripts/main.py --check >> output_fix.txt
fi

# Step 3 - Debug
echo -e "\n -------------------------- \n"
echo "Step 3 - Debug"
export iteration="2"
checkov -f fixed_templates/${chart_name}_checkov_fixed_template.yaml --skip-check CKV_K8S_14 --skip-check CKV_K8S_43 --skip-framework secrets --quiet --compact --framework kubernetes

# Step 4 - Add functionalities
echo -e "\n -------------------------- \n"
echo "Step 4 - Add functionalities"
export iteration="3"
python .github/scripts/main.py --add-func
if [ "$output" = "output" ]
then
    python .github/scripts/main.py --add-func >> output_func.txt
fi

# Step 5 - Run all tools on functional template
echo -e "\n -------------------------- \n"
echo -e "\n Step 5 - Checkov"
checkov -f functionality_templates/${chart_name}_func_template.yaml --skip-check CKV_K8S_14 --skip-check CKV_K8S_43 --skip-framework secrets --quiet --compact --framework kubernetes -o json > results_${iteration}.json
export second_tool="checkov"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# Datree
echo -e "\n Step 5 - Datree"
helm datree test functionality_templates/${chart_name}_func_template.yaml --only-k8s-files --quiet --output json > results_${iteration}.json
export second_tool="datree"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    echo -e "" >> output_final.txt
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# KICS
echo -e "\n Step 5 - KICS"
kics scan -p functionality_templates/${chart_name}_func_template.yaml --exclude-severities info --disable-secrets --exclude-queries bb241e61-77c3-4b97-9575-c0f8a1e008d0 --exclude-queries 7c81d34c-8e5a-402b-9798-9f442630e678 -o . > /dev/null 2>&1
mv results.json results_${iteration}.json
export second_tool="kics"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    echo -e "" >> output_final.txt
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# Kubelinter
echo -e "\n Step 5 - Kube-linter"
kube-linter lint functionality_templates/${chart_name}_func_template.yaml --config kubelinter-config.yaml --format=json > results_${iteration}.json
export second_tool="kubelinter"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    echo -e "" >> output_final.txt
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# Kubeaudit
echo -e "\n Step 5 - Kubeaudit"
kubeaudit all -f functionality_templates/${chart_name}_func_template.yaml --minseverity "error" --format json > results_${iteration}.json
export second_tool="kubeaudit"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    echo -e "" >> output_final.txt
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# Kubescape
echo -e "\n Step 5 - Kubescape"
kubescape scan functionality_templates/${chart_name}_func_template.yaml --exceptions kubescape_exceptions.json --format json --output results_${iteration}.json > /dev/null 2>&1
export second_tool="kubescape"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    echo -e "" >> output_final.txt
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# Terrascan
echo -e "\n Step 5 - Terrascan"
terrascan scan -i k8s -f functionality_templates/${chart_name}_func_template.yaml --skip-rules AC_K8S_0080 --skip-rules AC_K8S_0069 --skip-rules AC_K8S_0021 --skip-rules AC_K8S_0002 --skip-rules AC_K8S_0068 -o sarif > results_${iteration}.json
export second_tool="terrascan"
python .github/scripts/main.py --count-checks
if [ "$output" = "output" ]
then
    echo -e "" >> output_final.txt
    python .github/scripts/main.py --count-checks >> output_final.txt
fi

# Delete result files
rm results_1.json
rm results_3.json

# END
echo -e "\n -------------------------- \n"
echo "Done running analyzers on $chart_name"
