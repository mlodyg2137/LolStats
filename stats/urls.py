# stats/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('summoners/', views.summoner_list, name='summoner_list'), 
    path('summoner/<str:gameName>/<str:tagLine>/', views.summoner_detail, name='summoner_detail'),
]
