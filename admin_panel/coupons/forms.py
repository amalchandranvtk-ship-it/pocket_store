from django import forms
from .models import Coupon


class CouponForm(forms.ModelForm):

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date","class": "form-control"})
    )

    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date","class": "form-control"})
    )

    class Meta:

        model = Coupon

        fields = [
            "coupon_code",
            "discount_type",
            "discount_value",
            "minimum_order_value",
            "total_usage_limit",
            "limit_per_user",
            "start_date",
            "expiry_date",
            "is_active",
        ]

        widgets = {

            "coupon_code": forms.TextInput(attrs={"class": "form-control"}),

            "discount_type": forms.Select(attrs={"class": "form-select"}),

            "discount_value": forms.NumberInput(attrs={"class": "form-control","step": "0.01"}),

            "minimum_order_value": forms.NumberInput(attrs={"class": "form-control","step": "0.01"}),

            "total_usage_limit": forms.NumberInput(attrs={"class": "form-control"}),

            "limit_per_user": forms.NumberInput(attrs={"class": "form-control"}),

            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"})

        }