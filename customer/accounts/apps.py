from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'customer.accounts'
    
    def ready(self):
        import customer.accounts.signals