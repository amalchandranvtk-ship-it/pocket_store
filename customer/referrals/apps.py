from django.apps import AppConfig


class ReferralsConfig(AppConfig):
    name = 'customer.referrals'

    def ready(self):

        import customer.referrals.signals
