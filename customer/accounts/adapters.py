from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        user.email = data.get("email")
        user.username = data.get("email")
        user.full_name = data.get("name", "")
        user.role = "customer"
        user.is_active = True

        return user

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user

        user.role = "customer"
        user.is_active = True

        if not user.username:
            user.username = user.email

        if not user.full_name:
            user.full_name = user.email.split("@")[0]

        user.save()

        return user

