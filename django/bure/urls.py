# bure/urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('', RentEstimateSearch.as_view(), name="estimate"), # url path for webapp defaults to estimate page - iwc

    path('estimate', RentEstimateSearch.as_view(), name="estimate"), # url path for estimate page - iwc
    path("estimate/amenities/", get_location_amenities, name="estimate_amenities"),

    path('about', AboutView.as_view(), name='about_us'), # url path for about us page - iwc
    path('data', DataView.as_view(), name='data'), # url path for data page - iwc

]