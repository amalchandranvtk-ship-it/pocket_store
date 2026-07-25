from django.dispatch import receiver
from allauth.account.signals import user_signed_up


@receiver(user_signed_up)
def set_customer_role(request, user, **kwargs):
    user.role = "customer"

    full_name = user.get_full_name()

    if full_name:
        user.full_name = full_name
        user.first_name = full_name

    if not user.username:
        user.username = user.email

    user.save()