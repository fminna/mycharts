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

""" Compute each tool performance metrics.
"""


from scipy import stats
from scipy.stats import f_oneway
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import scikit_posthocs as sp
import pandas as pd
import numpy as np
import math
import statistics
import matplotlib.pyplot as plt


def parse_excel_file(file_path) -> pd.DataFrame:
    """ Parse the excel file and return the data as a dictionary."""
    # Read Tools Ranking sheet
    df = pd.read_excel(file_path, sheet_name=2)
    return df


def get_column_values(tool_list: dict, df: pd.DataFrame, column_name: str, value_column: str) -> dict:
    """ Get the values of a specific column based on tool names."""

    tools_dict = {}
    for tool in tool_list:
        tools_dict[tool] = []

    for _, row in df.iterrows():

        if isinstance(row[column_name], str):
            # tools = row[column_name].split("-")
            # first_tool = tool[0]

            # if first_tool == tools[1]:

            first_tool = row[column_name]
            if first_tool in tools_dict.keys():

                value = row[value_column]
                if not math.isnan(value):
                    tools_dict[first_tool].append(value)

    return tools_dict


def print_average(tools_dict: dict, tool_list: list):
    """ Print the average of each tool."""
    for tool_name in tool_list:
        tool = tool_name
        # if "-" not in tool_name:
        #     tool = f"{tool_name}-{tool_name}"
        # print("AVG ", tool_name, ":", np.mean(tools_dict[tool]))
        # print("SD ", tool_name, ":", np.std(tools_dict[tool]))

        print(round(np.mean(tools_dict[tool]), 2), end=" ")
        
        # With the previus, I get this error: ValueError: cannot convert float NaN to integer
        print(round(np.std(tools_dict[tool]), 2), end=" ")

        # max_value = max(tools_dict[tool])
        # min_value = min(tools_dict[tool])
        # print("MaX:", max_value, "Min:", min_value, "Diff:", max_value - min_value)
        # print(round(min_value, 2))
        # print(round(np.mean(tools_dict[tool]), 2), ", ", round(min_value, 2), ", ", round(max_value, 2))


def analyze_results(result_dict, tool_list, msg):
    """ Analyze the results."""
    print(msg)
    print("")

    print_average(result_dict, tool_list)
    print("")
    run_statistical_tests(result_dict)

    print("")


def run_statistical_tests(tools_dict: dict):
    """ Run statistical tests on the data."""

    # Extract the result lists and tool names from the dictionary
    result_lists = list(tools_dict.values())
    tool_names = list(tools_dict.keys())
    aux_tool_names = [x.split("-")[0] for x in tool_names]
    # pd.set_option('display.float_format', lambda x: '%.20f' % x)

    df = pd.DataFrame()
    for idx, result in enumerate(result_lists):
        df[tool_names[idx]] = result
    # print(df.head())

    # # Plot Mean
    # fig, ax = plt.subplots(1, 1)
    # ax.boxplot(result_lists)
    # ax.set_xticklabels(tool_names) 
    # ax.set_ylabel("Mean") 
    # plt.show()

    # Perform Shapiro-Wilk test for normality for result_lists
    shapiro_result = []
    for result in result_lists:
        _, p_value_shapiro = stats.shapiro(result)
        p_value_shapiro = f"{p_value_shapiro:.20f}"
        shapiro_result.append(p_value_shapiro)
    if all(float(x) > 0.05 for x in shapiro_result):
        print("Data is normally distributed")
    else:
        print("Data is not normally distributed")

    # Perform one-way ANOVA using scipy.stats.f_oneway
    # print(stats.f_oneway(*result_lists))
    # _, p_value_anova = stats.f_oneway(*result_lists)
    # p_value_anova = f"{p_value_anova:.20f}"
    # print(p_value_anova)

    # # Perform Tukey's HSD test using statsmodels if ANOVA is statistically significant
    # if float(p_value_anova) < 0.05:
    #     tukey_result = stats.tukey_hsd(*result_lists)
    #     print(tukey_result)

    ############################################
        
    print("Kruskal-Wallis test input")
    
    # List with the score of the pair Checkov-Checkov across all 52 charts
    # print(result_lists[0])

    # Perform non-parametric Kruskal-Wallis test
    print(stats.kruskal(*result_lists))
    _, p_value_kruskal = stats.kruskal(*result_lists)
    p_value_kruskal = f"{p_value_kruskal:.20f}"
    print(p_value_kruskal)

    # if float(p_value_kruskal) < 0.05:
    #     # Perform Dunn's test using Bonferroni correction for multiple comparisons
    #     posthoc_results = sp.posthoc_dunn(result_lists, p_adjust="bonferroni")

    #     print(posthoc_results)
    #     print(posthoc_results > 0.05)


def main():
    """ Main function."""
    file_path = "/Users/francescominna/Desktop/Chart_Evaluation.xlsx"
    excel_df = parse_excel_file(file_path)

    # Drop rows with empty values
    excel_df["Chart"].replace('', np.nan, inplace=True)
    excel_df["Chart"].dropna(inplace=True)

    # Get the list of chart names
    charts_list = list(excel_df["Chart"].unique())
    charts_list = [x for x in charts_list if str(x) != 'NaN' and str(x) != 'nan']

    # Get the list of tool pairs (e.g., "Checkov-Checkov, Checkov-Datree, etc.")
    pair_tools_list = list(excel_df["Tool Pairs"].unique())
    pair_tools_list = [x for x in pair_tools_list if str(x) != 'nan']

    # Get the list of same tool pairs (e.g., "Checkov-Checkov, Datree-Datree, KICS-KICS, etc.")
    # single_pair_tool_list = ["Checkov-Checkov", "Datree-Datree", "KICS-KICS", "Kubelinter-Kubelinter", \
                        #    "Kubeaudit-Kubeaudit", "Kubescape-Kubescape", "Terrascan-Terrascan"]

    # Get the list of tools (e.g., "Checkov, Datree, etc.")
    single_tool_list = list(set([aux.split("-")[0] for aux in pair_tools_list]))
    single_tool_list.sort()

    # Step 2 --- # Issues on original chart template
    # step_2_dict = get_column_values(single_tool_list, excel_df, "Tool Pairs", "Step 2")
    # msg = "Analysing # of issues found on the original template --- Step 2"
    # analyze_results(step_2_dict, single_tool_list, msg)

    # # Step 4 --- # of broken functionalities
    # step_4_dict = get_column_values(single_tool_list, excel_df, "Tool Pairs", "Step 4")
    # msg = "Analysing # of broken functionalities --- Step 4"
    # analyze_results(step_4_dict, single_tool_list, msg)

    # # # Step 5 --- # of issues on updated template
    # step_5_dict = get_column_values(single_tool_list, excel_df, "Tool Pairs", "Step 5")
    # msg = "Analysing # of issues on updated template --- Step 5"
    # analyze_results(step_5_dict, single_tool_list, msg)


    ###########################################################################

    # SAW --- Step_2 - Step_4 + Step_5
    saw_dict = get_column_values(pair_tools_list, excel_df, "Tool Pairs", "SAW")
    msg = "Analysing of SAW values --- Step_2 + Step_4 + Step_5"
    analyze_results(saw_dict, pair_tools_list, msg)

    exit(0)



    # Tool 1 dict
    saw_dict_1 = get_column_values(single_tool_list, excel_df, "Tool 1", "SAW")

    # Tool 2 dict
    saw_dict_2 = get_column_values(single_tool_list, excel_df, "Tool 2", "SAW")


    all_sums = []
    for first_tool in single_tool_list:
        for second_tool in single_tool_list:

            tools_sum = saw_dict_1[first_tool] + saw_dict_2[second_tool]
            round_sum = round(statistics.mean(tools_sum), 2)
            print(round_sum, end=" ")
            all_sums.append(round_sum)
        print("\n")

    all_sums.sort(reverse=True)
    print(all_sums[:3])


if __name__ == "__main__":
    main()
