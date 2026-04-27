from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from api.models import User, Branch

class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="password", role=User.ROLE_OWNER)
        self.manager = User.objects.create_user(username="manager", password="password", role=User.ROLE_MANAGER)
        self.staff = User.objects.create_user(username="staff", password="password", role=User.ROLE_STAFF)
        self.cashier = User.objects.create_user(username="cashier", password="password", role=User.ROLE_CASHIER)

        self.owner_token = Token.objects.create(user=self.owner)
        self.manager_token = Token.objects.create(user=self.manager)
        self.staff_token = Token.objects.create(user=self.staff)
        self.cashier_token = Token.objects.create(user=self.cashier)
        
        self.branch1 = Branch.objects.create(name="Branch 1", code="BR1", address="Addr 1")
        self.branch2 = Branch.objects.create(name="Branch 2", code="BR2", address="Addr 2")

    def authenticate(self, user_role):
        if user_role == "owner":
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.owner_token.key)
        elif user_role == "manager":
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.manager_token.key)
        elif user_role == "staff":
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.staff_token.key)
        elif user_role == "cashier":
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.cashier_token.key)
        else:
            self.client.credentials()
