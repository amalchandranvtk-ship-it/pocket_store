from django import forms

from admin_panel.catalog.models import Category, Product

from .models import Offer


class OfferForm(forms.ModelForm):
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.filter(is_deleted=False),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_deleted=False),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Offer
        fields = [
            "offer_name",
            "offer_type",
            "apply_to",
            "discount_value",
            "valid_from",
            "valid_to",
            "is_active",
        ]

        widgets = {
            "offer_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "offer_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "apply_to": forms.Select(
                attrs={"class": "form-select"}
            ),
            "discount_value": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
            "valid_from": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "valid_to": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("valid_from")
        end = cleaned.get("valid_to")

        if start and end and end < start:
            raise forms.ValidationError(
                "End date should be after start date."
            )

        discount = cleaned.get("discount_value")

        if discount and discount <= 0:
            raise forms.ValidationError(
                "Discount should be greater than zero."
            )

        apply_to = cleaned.get("apply_to")

        products = cleaned.get("products")
        categories = cleaned.get("categories")

        if apply_to == "product" and not products:
            raise forms.ValidationError(
                "Select at least one product."
            )

        if apply_to == "category" and not categories:
            raise forms.ValidationError(
                "Select at least one category."
            )

        return cleaned