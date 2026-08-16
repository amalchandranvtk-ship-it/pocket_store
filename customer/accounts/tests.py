
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class SignupTest(TestCase):

    def test_valid_signup(self):

        response = self.client.post(
            reverse("signup"),
            {
                "username": "amal",
                "email": "itzmeamalchandran@gmail.com",
                "password1": "Bijesh@123",
                "password2": "Bijesh@123",
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(email="itzmeamalchandran@gmail.com").exists()
        )