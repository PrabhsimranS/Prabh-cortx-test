"""Defect list for Test Execution Callbacks."""
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-
# !/usr/bin/python


from http import HTTPStatus
import dash_table
import pandas as pd
import requests
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import common
from common import app
from jira import JIRA


def get_test_executions_from_test_plan(test_plan: str, username: str, password: str) -> [dict]:
    """
    Summary: Get test executions from test plan.
    Description: Returns dictionary of test executions from test plan.
    Args:
        test_plan (str): Test plan number in JIRA
        username (str): JIRA Username
        password (str): JIRA Password
    :return list of Test execution keys attached to test plan
    """
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/{test_plan}/testexecution'
    response = requests.get(jira_url, auth=(username, password))
    te_ids = []
    if response.status_code == HTTPStatus.OK:
        for each in response.json():
            te_ids.append(each["key"])
    return te_ids


@app.callback(
    [Output('table_test_execution_wise_defect', 'children'),
     Output('test_execution_wise_defect_error', 'children')],
    [Input('test_execution_submit_button', 'n_clicks'),
     Input('test_execution_input', 'value')]
)
def gen_table_execution_wise_defect(n_clicks, ids):
    """
    Callback : Returns the defect details attached to the test execution ids
    :param n_clicks: Event after submit button clicked.
    :param ids: List of test execution id's
    :return: Datatable
    """
    if n_clicks is None or ids is None:
        raise PreventUpdate
    error_string = "Invalid test plan/test execution id "
    invalid_id = []
    ids_list = ids.split(",")
    print("Input id : ", ids_list)
    df_execution_wise_defect = pd.DataFrame(columns=["issue_no", "issue_comp",
                                                     "issue_name", "issue_priority",
                                                     "test_execution"])
    jira_url = "https://jts.seagate.com/"
    auth_jira = JIRA({'server': jira_url}, basic_auth=(common.jira_username, common.jira_password))
    for input_id in ids_list:
        te_ids = []
        try:
            id_details = auth_jira.issue(input_id)
        except Exception as ex:
            print("Exception received while accessing Jira {}".format(ex))
            invalid_id.append(input_id)
        else:
            if id_details.fields.issuetype.name == 'Test Plan':
                tp_id = input_id
                temp_list = get_test_executions_from_test_plan(input_id, common.jira_username,
                                                               common.jira_password)
                if len(temp_list) > 0:
                    te_ids.extend(temp_list)
            elif id_details.fields.issuetype.name == 'Test Execution':
                tp_id = "-"
                te_ids.append(input_id)
            else:
                invalid_id.append(input_id)
                continue

            print("TE ids : ", te_ids)
            for te_id in te_ids:
                issue_list = []
                jira_link = 'https://jts.seagate.com/rest/raven/1.0/api/testexec/' +\
                            str(te_id) + '/test?detailed=true'
                response = requests.get(jira_link, auth=(common.jira_username,
                                                         common.jira_password))
                test_execution_data = response.json()
                for each in test_execution_data:
                    for defect_no in range(len(each['defects'])):
                        issue_list.append(each['defects'][defect_no]['key'])
                print("Issue List:", issue_list)
                te_df = common.get_issue_details(issue_list)

                for _ in te_df:
                    te_df["test_execution"] = te_id
                    te_df["test_plan"] = tp_id
                df_execution_wise_defect = df_execution_wise_defect.append(te_df)

    if common.DEBUG_PRINTS:
        print("gen_table_execution_wise_defect : Dataframe returned ")
        print(df_execution_wise_defect)

    execution_wise_defect = dash_table.DataTable(
        id="execution_wise_defect",
        columns=[{"name": str(i).upper(), "id": i} for i in df_execution_wise_defect.columns],
        data=df_execution_wise_defect.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                ],
        style_cell=common.dict_style_cell
    )
    if len(invalid_id) > 0:
        error_string = error_string + str(invalid_id)
    else:
        error_string = ""
    return execution_wise_defect, error_string