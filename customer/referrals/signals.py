from django.db.models.signals import post_save

from django.dispatch import receiver

from customer.accounts.models import User

from .utils import generate_referral_code


@receiver(post_save, sender=User)

def create_referral_code(sender, instance, created, **kwargs):

    if created:

        if not instance.referral_code:

            instance.referral_code = generate_referral_code()

            instance.save(update_fields=["referral_code"])