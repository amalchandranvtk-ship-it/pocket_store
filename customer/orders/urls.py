from django.urls import path
from . import views

urlpatterns = [

    path("checkout/", views.checkout_view, name="checkout"),
  
    path("payment/",views.payment_view,name="payment"),
  
    path("place-order/", views.place_order, name="place_order"),
    path("order-success/<str:order_number>/",views.order_success,name="order_success"),
    path("order-failed/",views.order_failed,name="order_failed"),
    path("orders/",views.order_list,name="order_list"),
    path("orders/search/",views.search_orders,name="search_orders"),
    path("orders/<str:order_number>/",views.order_detail,name="order_detail"),
    path("orders/<str:order_number>/cancel/",views.cancel_order,name="cancel_order",),
    path("order-item/<int:item_id>/cancel/",views.cancel_order_item,name="cancel_order_item",),
    path("address/delete/<int:id>/",views.delete_address,name="delete_address",),
    path("orders/<str:order_number>/invoice/",views.download_invoice,name="download_invoice",),
    path("create-razorpay-order/",views.create_razorpay_order,name="create_razorpay_order",),
    path("verify-razorpay-payment/",views.verify_razorpay_payment,name="verify_razorpay_payment",),
    path("order-item/<int:item_id>/return/",views.return_request,name="return_request",),
    path("apply-coupon/",views.apply_coupon,name="apply_coupon",),
    path("remove-coupon/",views.remove_coupon,name="remove_coupon",),

]