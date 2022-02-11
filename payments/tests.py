from rest_framework.test import APITestCase, APIRequestFactory, APIClient
from django.contrib.auth import get_user_model
import decimal

from .models import Account


def setup_superuser(username):
    User = get_user_model()
    user = User.objects.create_superuser(
        username=username,
        email=username + '@admin.com',
        password='test'
    )
    Account.objects.create(user=user)
    return user


def setup_user(username):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        email=username + '@client.com',
        password='test'
    )
    Account.objects.create(user=user)
    return user


class TestFundCreation(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.uri = '/createfunds/'
        self.superuser = setup_superuser('admin')
        self.user = setup_user('prueba')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    def test_admin_fund_creation(self):
        self.client.login(username="admin", password="test")

        data = {"amount": 100}
        self.client.put(self.uri, data)
        updated_amount = Account.objects.get(user=self.superuser).amount

        self.assertEqual(updated_amount, data['amount'],
                         "Account funds do not match")

    def test_client_fund_creation(self):
        self.client.login(username="client", password="test")

        data = {'amount': 100}
        response = self.client.put(self.uri, data)

        self.assertEqual(response.status_code, 401,
                         "Expected response Code 401, received {} instead"
                         .format(response.status_code))


class TestFundDestruction(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.burn_uri = '/burnfunds/'
        self.superuser = setup_superuser('admin')
        self.user = setup_user('prueba')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    def test_admin_fund_destruction(self):
        self.client.login(username='admin', password='test')

        data = {"amount": 100}
        self.client.put(self.create_uri, data)
        response = self.client.put(self.burn_uri + "{}/".format(self.superuser_account.pk), data)
        self.assertEqual(decimal.Decimal(response.data['amount']), 0,
                         "amount should be 0 but instead is {}".format(response.data['amount']))

    def test_client_fund_destruction(self):
        self.client.login(username="admin", password="test")

        data = {"amount": 100}
        self.client.put(self.create_uri, data)

        self.client.login(username='client', password='test')
        response = self.client.put(self.burn_uri + "{}/".format(self.user_account.pk), data)
        self.assertEqual(response.status_code, 400,
                         "Expected response Code 400, received {} instead")

    def test_negative_fund_destruction(self):
        self.client.login(username="admin", password="test")

        creation_data = {'amount': 100}
        destruction_data = {'amount': 200}
        self.client.put(self.create_uri, creation_data)
        response = self.client.put(self.burn_uri + "{}/".format(self.superuser_account.pk), destruction_data)
        self.assertEqual(response.status_code, 400,
                         "Expected response Code 400, received {} instead")


class TestTransferFunds(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.transfer_uri = "/transferfunds/"
        self.superuser = setup_superuser('admin')
        self.user = setup_user('prueba')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    def test_source_fund_reduction(self):
        self.client.login(username='admin', password='test')

        creation_data = {'amount': 100}
        self.client.put(self.create_uri, creation_data)

        transfer_data = {'amount': 20}
        self.client.put(self.transfer_uri + "{}/".format(self.user_account.pk), transfer_data)
        updated_source_funds = Account.objects.get(user=self.superuser).amount

        source_data = {'amount': creation_data['amount'] - transfer_data['amount']}
        self.assertEqual(updated_source_funds, source_data['amount'],
                         "Source account funds do not match")

    def test_source_negative_funds(self):
        self.client.login(username='admin', password='test')

        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        transfer_data = {'amount': 100}
        response = self.client.put(self.transfer_uri + "{}/".format(self.user_account.pk), transfer_data)
        self.assertEqual(response.status_code, 400,
                         "Expected response Code 400, received {} instead")

    def test_destination_fund_addition(self):
        self.client.login(username='admin', password='test')

        creation_data = {'amount': 100}
        self.client.put(self.create_uri, creation_data)

        transfer_data = {'amount': 20}
        self.client.put(self.transfer_uri + "{}/".format(self.user_account.pk), transfer_data)
        updated_destination_funds = Account.objects.get(user=self.user).amount

        self.assertEqual(updated_destination_funds, transfer_data['amount'],
                         "Source acount funds do not match")