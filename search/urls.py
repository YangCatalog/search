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
    path(r'impact_analysis/', views.impact_analysis, name='impact_analysis')
]
