# Copyright The IETF Trust 2019, All Rights Reserved
# Copyright 2018 Cisco and its afficiliates
# 
# Authors Joe Clarke jclarke@cisco.com and Tom�s Markovic <Tomas.Markovic@pantheon.tech> for the Python version
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'search'
urlpatterns = [
    path('', views.index, name='index'),
    path(r'show_node/<name><path:path>/<revision>', view= views.show_node, name='show_node'),
    path(r'show_node/', view= views.show_node, name='show_node'),
    path(r'yang_tree/show_node/<name><path:path>', view= views.show_node, name='show_node'),
    path(r'impact_analysis/completions/<type>/<pattern>', view= views.completions, name='completions'),
    path(r'module_details/completions/<type>/<pattern>', view= views.completions, name='completions'),
    path(r'metadata_update', csrf_exempt(views.metadata_update), name='metadata_update'),
    path(r'module_details/<module>', views.module_details, name='module_details'),
    path(r'yang_tree/<module>', views.yang_tree, name='yang_tree'),
    path(r'impact_analysis/<module>', views.impact_analysis, name='impact_analysis'),
    path(r'yangsuite/<module>', views.yangsuite, name='yangsuite'),
    path(r'module_details/', views.module_details, name='module_details'),
    path(r'yang_tree/', views.yang_tree, name='yang_tree'),
    path(r'impact_analysis/', views.impact_analysis, name='impact_analysis'),
    path(r'impact_analysis_php/', views.impact_analysis_php, name='impact_analysis_php') # This one is to maintain URL compatibility from previous links of IETF datatracker
]
