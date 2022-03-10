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
from django.urls import path, re_path, include
from inventories.views import *

app_name = 'inventories'

urlpatterns = [
    path('module/', module_home, name='module_home'),
    path('module/report', module_report, name='module_report'),
    path('module/reports', report_list, name='report_list'),
    path('networks/', networks, name='networks'),
    # path('devices/', network_devices, name='devices'),
    path('monitor/devices/', network_devices, name='devices'),
    path('locations/', locations, name='locations'),
    path('logs/', logs, name='logs'),
    path('anomalies/', anomalies, name='anomalies'),
    # path('anomalies/logs', anomaly_logs, name='anomaly_logs'),
    path('system_users/', system_users, name='system_users'),
    path('root_cause/', rc_graph_list, name='rc_graph_list'),
    path('add_device_driver/', add_device_driver, name='add_device_driver'),

    re_path(r'^networks/(?P<id>[\w-]+)/$', network_detail, name='network_detail'),
    # re_path(r'^devices/(?P<id>[\w-]+)/$', device_detail, name='device_detail'),
    re_path(r'^monitor/devices/(?P<id>[\w-]+)/$', device_detail, name='device_detail'),
    re_path(r'^locations/(?P<id>[\w-]+)/$', location_detail, name='location_detail'),
    re_path(r'^logs/(?P<id>[\w-]+)/$', log_detail, name='log_detail'),
    re_path(r'^logs/log_source/(?P<id>[\w-]+)/$', logs_for_source, name='logs_for_source'),
    re_path(r'^anomalies/(?P<id>[\w-]+)/$', anomaly_detail, name='anomaly_detail'),
    re_path(r'^anomalies/logs/(?P<id>[\w-]+)/$', anomaly_logs, name='anomaly_logs'),
    re_path(r'^root_cause/(?P<id>[\w-]+)/$', rc_graph_detail, name='rc_graph_detail'),
    re_path(r'^module/report/(?P<id>[\w-]+)/$', report_detail, name='report_detail'),
    re_path(r'^module/report/(?P<id>[\w-]+)/delete/', delete_report_type, name='delete_report_type'),

]
