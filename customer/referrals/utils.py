import secrets

from customer.accounts.models import User


def generate_referral_code():

    while True:

        code = "PS" + secrets.token_hex(4).upper()

        if not User.objects.filter(referral_code=code).exists():

            return code