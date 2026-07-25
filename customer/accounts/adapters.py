from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        email = data.get("email", "")
        name = data.get("name", "")

        user.email = email
        user.username = email
        user.full_name = name or email.split("@")[0]
        user.role = "customer"
        user.is_active = True

        return user