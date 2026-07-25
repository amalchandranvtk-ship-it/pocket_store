from django import forms

from admin_panel.review.models import Review


class ReviewForm(forms.ModelForm):

    class Meta:
        model = Review

        fields = [
            "rating",
            "review_title",
            "review_description",
        ]

        widgets = {

            "rating": forms.HiddenInput(),

            "review_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Summarize your experience"
                }
            ),

            "review_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Write your detailed review..."
                }
            ),

        }