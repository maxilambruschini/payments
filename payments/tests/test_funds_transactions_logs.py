from rest_framework.test import APITestCase, APIClient, APIRequestFactory
import decimal

from payments.utils import UserUtils
from payments.models import Account


class TestTransferLogs(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.transfer_uri = "/transferfunds/"
        self.burn_uri = "/burnfunds/"
        self.transaction_uri = "/transferlogs/"
        self.superuser = UserUtils.setup_superuser('admin')
        self.user = UserUtils.setup_user('prueba')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    def test_fund_creation_transaction(self):
        self.client.login(username="admin", password="test")

        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        response = self.client.get(self.transaction_uri)

        transaction_amount = decimal.Decimal(response.data[-1]['amount'])
        source_account_pk = response.data[-1]['source_account']
        destination_account_pk = response.data[-1]['destination_account']
        self.assertEqual(transaction_amount, 50,
                         'Transfer log amount does not match. Expected 50 but got {} instead'.format(
                             transaction_amount))
        self.assertEqual(source_account_pk, None,
                         "Transfer log source_account should be none")
        self.assertEqual(destination_account_pk, self.superuser_account.pk,
                         "Transfer log destination_account does not match")

    def test_fund_destruction_transaction(self):
        self.client.login(username="admin", password="test")

        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        destruction_data = {'amount': 20}
        self.client.put(self.burn_uri + "{}/".format(self.superuser_account.pk), destruction_data)

        response = self.client.get(self.transaction_uri)
        transaction_amount = decimal.Decimal(response.data[-1]['amount'])
        source_account_pk = response.data[-1]['source_account']
        destination_account_pk = response.data[-1]['destination_account']
        self.assertEqual(transaction_amount, 20,
                         'Transfer log amount does not match. Expected 20 but got {} instead'.format(
                             transaction_amount))
        self.assertEqual(source_account_pk, self.superuser_account.pk,
                         "Transfer log source_account does not match")
        self.assertEqual(destination_account_pk, None,
                         "Transfer log destination_account should be None")

    def test_transaction(self):
        self.client.login(username="admin", password="test")

        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        transfer_data = {'amount': 30}
        self.client.put(self.transfer_uri + "{}/".format(self.user_account.pk), transfer_data)

        response = self.client.get(self.transaction_uri)
        transaction_amount = decimal.Decimal(response.data[-1]['amount'])
        source_account_pk = response.data[-1]['source_account']
        destination_account_pk = response.data[-1]['destination_account']
        self.assertEqual(transaction_amount, 30,
                         'Transfer log amount does not match. Expected 20 but got {} instead'.format(
                             transaction_amount))
        self.assertEqual(source_account_pk, self.superuser_account.pk,
                         "Transfer log source_account does not match")
        self.assertEqual(destination_account_pk, self.user_account.pk,
                         "Transfer log destination_account should be None")