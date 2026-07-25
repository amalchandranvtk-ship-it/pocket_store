from django.urls import path

from . import views

urlpatterns = [

    path("",views.wallet_view,name="wallet"),
    path("history/",views.wallet_history,name="wallet_history"),
    path("add-money/",views.add_money_wallet,name="add_money_wallet"),
    path("payment-success/",views.wallet_payment_success,name="wallet_payment_success"),
    path("payment-failed/",views.wallet_payment_failed,name="wallet_payment_failed"),
    path("create-order/",views.create_wallet_order,name="create_wallet_order"),
    path("verify-payment/",views.verify_wallet_payment,name="verify_wallet_payment"),

]