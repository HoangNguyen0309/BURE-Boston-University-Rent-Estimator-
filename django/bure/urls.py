# bure/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('', HomeView, name="home"),      # default home page for web app
    path('/home', HomeView, name="home"), # url path either '' or '/home' - iwc
    path('/about', AboutView, name='about_us'), # url path for about us page - iwc
    path('/data', DataView, name='data'), # url path for data page - iwc

]