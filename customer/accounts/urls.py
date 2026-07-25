from django.urls import path
from . import views

urlpatterns = [
    path("", views.public_home, name="public_home"),

    path("login/", views.login, name="customer_login"),
    path("signup/", views.signup, name="customer_signup"),
    path("verify_otp/", views.verify_otp, name="customer_verify_otp"),
    path("resend_otp/", views.resend_otp, name="customer_resend_otp"),

    path("forgot_password/", views.forgot_password, name="customer_forgot_password"),
    path("reset_password/", views.reset_password, name="customer_reset_password"),

    path("home/", views.customer_home, name="customer_home"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("change_password/", views.change_password, name="change_password"),

    path("addresses/", views.address_list, name="address_list"),
    path("addresses/add/", views.add_address, name="add_address"),
    path("addresses/edit/<int:address_id>/", views.edit_address, name="edit_address"),
    path("addresses/delete/<int:address_id>/", views.delete_address, name="delete_address"),
    path("addresses/default/<int:address_id>/", views.set_default_address, name="set_default_address"),

    path("logout/", views.customer_logout, name="customer_logout"),
    path("delete_account/", views.delete_account, name="delete_account"),
]