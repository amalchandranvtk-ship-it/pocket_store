from django.urls import path

from . import views

urlpatterns = [

    path("",views.referral_home,name="referral_home"),

]