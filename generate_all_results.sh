#!/bin/bash

# This script takes as input a chart name and runs all security tools on it.

# Take an optional output boolean variable as argument
output=$1

# Take a chart_name variable as argument
# chart_name=$2

# # If not provided, exit
# if [ -z "$chart_name" ]
# then
#     echo "No chart name provided! Exiting..."
#     exit 1
# fi

chart_list=("kube-prometheus-stack" "ingress-nginx" "cert-manager" "argo-cd" "prometheus" "redis" "grafana" "kubernetes-dashboard" "postgresql" "traefik" "gitlab" "jenkins" "elasticsearch" "mysql" "metrics-server" "external-dns" "rabbitmq" "kafka" "loki" "harbor" "keycloak" "mongodb" "nextcloud" "minio" "loki-stack" "longhorn" "datadog" "artifact-hub" "rancher" "fluent-bit" "kibana" "wordpress" "consul " "pihole" "nginx" "thanos" "mariadb" "sonarqube" "argo-workflows" "nginx-ingress" "metallb" "nexus-repository-manager" "kubeview" "external-secrets" "oauth2-proxy" "promtail" "pgadmin4" "gitea" "postgresql-ha" "nfs-server-provisioner" "falco")

# Iterate over all charts
for chart_name in "${chart_list[@]}"; do

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

done