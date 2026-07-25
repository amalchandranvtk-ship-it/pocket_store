from django.urls import path
from . import views

urlpatterns = [

    path("dashboard/",views.dashboard,name="admin_dashboard"),
    path("dashboard/edit-profile/",views.edit_profile,name="admin_edit_profile"),
    path("dashboard/change-password/",views.change_password,name="admin_change_password"),

]