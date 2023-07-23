#!/bin/bash

# This script takes as input a chart name and runs all security tools on it.

# Take an optional output boolean variable as argument
output=$1

# Take a chart_name variable as argument
chart_name=$2

# If not provided, exit
if [ -z "$chart_name" ]
then
    echo "No chart name provided! Exiting..."
    exit 1
fi

# Step 1 - checkov
./checkov_generate_results.sh $chart_name $output

# Step 2 - datree
./datree_generate_results.sh $chart_name $output

# Step 3 - kics
./kics_generate_results.sh $chart_name $output

# Step 4 - kubelinter
./kubelinter_generate_results.sh $chart_name $output

# Step 5 - kubeaudit
./kubeaudit_generate_results.sh $chart_name $output    

# Step 6 - kubesec
./kubescape_generate_results.sh $chart_name $output

# Step 7 - terrascan
./terrascan_generate_results.sh $chart_name $output
