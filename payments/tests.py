from rest_framework.test import APITestCase, APIRequestFactory, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone, dateformat
import datetime
import decimal

from .models import Account, Loan
from .utils import LoanUtils


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
                         "Expected response Code 401, received {} instead".format(response.status_code))


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


class TestTransferLogs(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.transfer_uri = "/transferfunds/"
        self.burn_uri = "/burnfunds/"
        self.transaction_uri = "/transferlogs/"
        self.superuser = setup_superuser('admin')
        self.user = setup_user('prueba')
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


class TestIntegralTransfer(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.transfer_uri = "/transferfunds/"
        self.burn_uri = "/burnfunds/"
        self.user_a = setup_superuser('A')
        self.user_b = setup_user('B')
        self.user_c = setup_user('C')
        self.user_a_account = Account.objects.get(user=self.user_a)
        self.user_b_account = Account.objects.get(user=self.user_b)
        self.user_c_account = Account.objects.get(user=self.user_c)

    def test_integral(self):
        self.client.login(username="A", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        transfer_data = {'amount': 25}
        self.client.put(self.transfer_uri + "{}/".format(self.user_b_account.pk), transfer_data)
        self.client.put(self.transfer_uri + "{}/".format(self.user_c_account.pk), transfer_data)

        self.client.login(username="B", password="test")
        transfer_data = {'amount': 10}
        self.client.put(self.transfer_uri + "{}/".format(self.user_c_account.pk), transfer_data)

        self.client.login(username="A", password="test")
        burn_data = {'amount': 10}
        self.client.put(self.burn_uri + "{}/".format(self.user_b_account.pk), burn_data)

        updated_A_funds = Account.objects.get(user=self.user_a).amount
        self.assertEqual(updated_A_funds, 0,
                         "A funds do not match. Expected 0 but got {} instead".format(updated_A_funds))

        updated_B_funds = Account.objects.get(user=self.user_b).amount
        self.assertEqual(updated_B_funds, 5,
                         "B funds do not match. Expected 5 but got {} instead".format(updated_B_funds))

        updated_C_funds = Account.objects.get(user=self.user_c).amount
        self.assertEqual(updated_C_funds, 35,
                         "C funds do not match. Expected 35 but got {} instead".format(updated_C_funds))


class TestLoan(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.createloan_uri = "/createloan/"
        self.getloanstatus_uri = "/loanstatus/"
        self.payloan_uri = "/payloan/"
        self.transfer_uri = "/transferfunds/"
        self.superuser = setup_superuser('admin')
        self.user = setup_user('client')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    @staticmethod
    def create_loan_data(receiver_pk):
        return {
            "receiver": receiver_pk,
            "lend_amount": 10,
            "interest_rate": 10,
            "due_date": timezone.now() + timezone.timedelta(days=10)
        }

    def test_create_loan(self):
        self.client.login(username="admin", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        loan_data = self.create_loan_data(receiver_pk=self.user_account.pk)
        response = self.client.post(self.createloan_uri, loan_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         "Expected status code 200 but got {} instead".format(response.status_code))

    def test_loan_status(self):
        self.client.login(username="admin", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        create_loan_data = self.create_loan_data(receiver_pk=self.user_account.pk)
        self.client.post(self.createloan_uri, create_loan_data)

        loan_pk = Loan.objects.all()[0].pk
        get_status_response = self.client.get(self.getloanstatus_uri + "{}/".format(loan_pk))
        self.assertEqual(get_status_response.status_code, status.HTTP_200_OK,
                         get_status_response)

    def test_pay_loan(self):
        self.client.login(username="admin", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        create_loan_data = self.create_loan_data(receiver_pk=self.user_account.pk)
        self.client.post(self.createloan_uri, create_loan_data)

        loan_pk = Loan.objects.all()[0].pk
        pay_loan_data = {
            'loan_id': loan_pk,
            'payed_amount': create_loan_data['lend_amount']
        }
        self.client.login(username="client", password="test")
        pay_loan_response = self.client.put(self.payloan_uri, pay_loan_data)

        self.assertEqual(pay_loan_response.status_code, status.HTTP_200_OK,
                         "Expected code 200 but got {} instead".format(pay_loan_response.status_code))

    def test_loan_integral(self):
        self.client.login(username='admin', password="test")

        # create funds for admin
        creation_data = {'amount': 100}
        self.client.put(self.create_uri, creation_data)

        # transfer funds to client to be able to return loan amount
        transfer_data = {'amount': 20}
        self.client.put(self.transfer_uri + "{}/".format(self.user_account.pk), transfer_data)

        # create loan from admin to client
        loan_data = self.create_loan_data(receiver_pk=self.user_account.pk)
        createloan_response = self.client.post(self.createloan_uri, loan_data)
        self.assertEqual(createloan_response.status_code, status.HTTP_201_CREATED,
                         "Loan creation failed. Expected 201 but got {} instead".format(
                             createloan_response.status_code))

        # get loan status -> unpaid
        loan_pk = Loan.objects.all()[0].pk
        get_status_response = self.client.get(self.getloanstatus_uri + "{}/".format(loan_pk))
        self.assertEqual(get_status_response.data['return_date'], None,
                         "First loan status failed")

        # pay $5
        loan_pk = Loan.objects.all()[0].pk
        pay_loan_data = {
            'loan_id': loan_pk,
            'payed_amount': 5
        }
        self.client.login(username="client", password="test")
        pay_loan_response = self.client.put(self.payloan_uri, pay_loan_data)
        self.assertEqual(pay_loan_response.status_code, status.HTTP_200_OK,
                         "First loan payment failed. Expected code 200 but got {} instead".format(
                             pay_loan_response.status_code))

        # get loan status -> unpaid
        loan_pk = Loan.objects.all()[0].pk
        get_status_response = self.client.get(self.getloanstatus_uri + "{}/".format(loan_pk))
        self.assertEqual(get_status_response.data['return_date'], None,
                         "Second loan status failed")

        # pay $6
        loan_pk = Loan.objects.all()[0].pk
        pay_loan_data = {
            'loan_id': loan_pk,
            'payed_amount': 6
        }
        self.client.login(username="client", password="test")
        pay_loan_response = self.client.put(self.payloan_uri, pay_loan_data)
        self.assertEqual(pay_loan_response.status_code, status.HTTP_200_OK,
                         "Second loan payment failed. Expected code 200 but got {} instead".format(
                             pay_loan_response.status_code))

        # get loan status -> paid
        loan_pk = Loan.objects.all()[0].pk
        get_status_response = self.client.get(self.getloanstatus_uri + "{}/".format(loan_pk))
        self.assertTrue(get_status_response.data['return_date'] is not None, "Third loan status failed")
