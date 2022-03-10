"""ATIBAreport URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path, re_path, include

import accounts.urls
import inventories.urls
import AgentRoot.urls
from AgentRoot.views import *

urlpatterns = [
    path('', home_view, name='home'),
    # path('admin/', admin.site.urls, name='django_admin'),
    path('monitor/', include(AgentRoot.urls)),
    path('accounts/', include(accounts.urls)),
    path('inventories/', include(inventories.urls, namespace='inventories')),
    path('license/', check_license, name='check_license'),

    path('system_configurations/', system_configurations, name='system_configurations'),
    path('system_configurations/ai_sensitivity/', ai_sensitivity, name='ai_sensitivity'),
    path('system_configurations/mailing_settings/', mailing_settings, name='mailing_settings'),
    path('system_configurations/mailing_details/', mailing_details, name='mailing_details'),

    path('log_source/', log_sources, name='log_sources'),
    path('help/', help_pages, name='help_pages'),
    path('error/', error_pages, name='error_pages'),

    path('maintenance/', maintenance, name='maintenance'),
    path('maintenance/iamatiba_services/', iamatiba_services, name='iamatiba_services'),
    path('maintenance/cluster/', cluster, name='cluster'),

    path('log_source/add_log_sources/', add_log_sources, name='add_log_sources'),
    path('log_source/add_log_sources/add_networkdevice', add_networkdevice, name='add_networkdevice'),
    path('log_source/add_log_sources/add_nginx', add_nginx, name='add_nginx'),
    path('log_source/add_log_sources/add_postgresql', add_postgresql, name='add_postgresql'),
    path('log_source/add_log_sources/add_microsoftserver', add_microsoftserver, name='add_microsoftserver'),
    path('log_source/add_log_sources/add_linuxserver', add_linuxserver, name='add_linuxserver'),
    path('log_source/add_log_sources/add_elastic', add_elastic, name='add_elastic'),

    path('profiles/', profiles, name='profiles'),
    path('profiles/add_monitor_profile', add_monitor_profile, name='add_monitor_profile'),
    path('profiles/add_location_profile', add_location_profile, name='add_location_profile'),
    path('profiles/add_ingestion_profile', add_ingestion_profile, name='add_ingestion_profile'),
    path('profiles/add_parser_profile', add_parser_profile, name='add_parser_profile'),

    path('logdefinitions/', logdefinitions_analysis, name='logdefinitions_analysis'),
    path('logdefinitions/parameters', parameter_variables, name='parameter_variables'),
    path('logdefinitions/parameters/new', add_parameter_variable, name='add_parameter_variable'),

    re_path(r'^log_source/(?P<id>[\w-]+)/$', edit_log_source, name='edit_log_source'),
    re_path(r'^profiles/edit_monitor_profile/(?P<id>[\w-]+)/$', edit_monitor_profile, name='edit_monitor_profile'),
    re_path(r'profiles/delete/(?P<type>[\w-]+)/(?P<id>[\w-]+)/$', delete_profile, name='delete_profile'),
    re_path(r'^log_source/component/(?P<id>[\w-]+)/$', edit_component, name='edit_component'),
    re_path(r'^log_source/application/(?P<id>[\w-]+)/$', edit_application, name='edit_application'),
    re_path(r'^logdefinitions/(?P<id>[\w-]+)/$', logdefdetails_analysis, name='logdefdetails_analysis'),
    re_path(r'^logdefinitions/parameters/(?P<id>[\w-]+)/$', edit_parameter_variable, name='edit_parameter_variable'),
    re_path(r'^logdefinitions/defdetails/(?P<id>[\w-]+)/$', logdefdetails_configure, name='logdefdetails_configure'),
    # re_path(r'^logdefinitions/defdetails/edit/(?P<id>[\w-]+)/$', logdefdetails_edit, name='logdefdetails_edit'),
    re_path(r'^logdefinitions/defdetails/edit/(?P<id>[\w-]+)/$', logdefdetails_edit2, name='logdefdetails_edit'),

    re_path(r'^maintenance/cluster/add_slave/(?P<id>[\w-]+)/$', cluster_add_slave, name='cluster_add_slave'),
    re_path(r'^maintenance/cluster/make_slave/(?P<id>[\w-]+)/$', cluster_make_it_slave, name='cluster_make_it_slave'),
    re_path(r'^maintenance/cluster/node_settings/(?P<id>[\w-]+)/$', cluster_node_settings, name='cluster_node_settings'),
    re_path(r'^maintenance/cluster/remove_slave/(?P<id>[\w-]+)/$', cluster_remove_slave, name='cluster_remove_slave'),

    re_path(r'^system_configurations/mailing_settings/(?P<id>[\w-]+)/$', mailing_settings, name='mailing_settings_edit'),
    re_path(r'^system_configurations/mailing_details/(?P<id>[\w-]+)/$', mailing_details, name='mailing_details_edit'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
