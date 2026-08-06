"""
URL configuration for pocket_store project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('admin/', include('admin_panel.admin_accounts.urls')),
    path('admin/', include('admin_panel.catalog.urls')),
    path('admin/', include('admin_panel.admin_order.urls')),
    path('admin/', include('admin_panel.dashboard.urls')),
    path('admin/coupon/', include('admin_panel.coupons.urls')),
    path('admin/', include('admin_panel.reports.urls')),
    path('admin/offer/', include('admin_panel.offers.urls')),
    path('admin/', include('admin_panel.review.urls')),
    path("accounts/", include("allauth.urls")), 






    path('reviews/', include('customer.reviews.urls')),
    path('',include('customer.accounts.urls')),
    path('store/',include('customer.store.urls')),
    path('orders/',include('customer.orders.urls')),
    path("wallet/",include("customer.wallet.urls")),
    path('accounts/', include('allauth.urls')),
    path("referrals/",include("customer.referrals.urls")),

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)