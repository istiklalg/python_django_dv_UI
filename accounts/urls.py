"""accounts URL Configuration

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
from accounts.views import *

app_name = 'accounts'

urlpatterns = [
    # path('', ),
    # path('register/', accounts_register, name='accounts_register'),
    path('login/', accounts_login, name='accounts_login'),
    path('logout/', accounts_logout, name='accounts_logout'),
    path('change/', accounts_change_password, name='accounts_change_password'),
    path('license/', add_license, name='add_license'),

]
