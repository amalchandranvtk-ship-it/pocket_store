from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    path('forgot_password/', views.forgot_pass, name='admin_forgot_password'),
    path('otp_verify/', views.verify_otp, name='admin_otp_verification'),
    path('resend_otp/', views.resend_otp, name='admin_resend_otp'),
    path('reset_password/', views.reset_password, name='admin_reset_password'),

    path('customers/', views.customer_list, name='admin_customers'),
    path('block/<int:user_id>/', views.block_customer, name='block_customer'),
    path('unblock/<int:user_id>/', views.unblock_customer, name='unblock_customer'),
    path('logout/', views.admin_logout, name='admin_logout'),

    path("edit-profile/",views.edit_profile,name="admin_edit_profile"),
    path("change-password/",views.change_password,name="admin_change_password"),
    
]