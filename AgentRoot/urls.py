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
from .views import *

app_name = 'AgentRoot'

urlpatterns = [
    path('', general_monitor, name='general_monitor'),
    path('loading/', loading_view, name='loading_view'),
    path('not_found/', not_found_view, name='not_found_view'),
    path('flowing/', rc_flowing, name='rc_flowing'),
    path('interval_tables/', check_interval_tables, name='check_interval_tables'),
    path('search/', search_from_nav, name='search_from_nav'),
    path('incidents_home/', incidents_home, name='incidents_home'),
    path('incidents/', incidents_monitor, name='incidents_monitor'),
    path('incidents/diagnosis', diagnosis_monitor, name='diagnosis_monitor'),
    path('log_monitoring/', log_monitoring, name='log_monitoring'),
    path('log_monitoring/all_logs/', log_monitoring_all, name='log_monitoring_all'),
    path('all_logs/', all_logs, name='all_logs'),
    path('atiba/', monitoring_atiba, name='monitoring_atiba'),
    path('atiba/logs', monitoring_atiba_uilogs, name='monitoring_atiba_uilogs'),

    re_path(r'^anomalies/(?P<id>[\w-]+)/$', anomalies_detail_monitor, name='anomalies_detail_monitor'),
    re_path(r'^incidents/(?P<id>[\w-]+)/$', diagnoses_for_incidentset, name='diagnoses_for_incidentset'),
    re_path(r'^incidents/diagnosis/analyse/(?P<id>[\w-]+)/$', diagnosis_analyse, name='diagnosis_analyse'),
]

