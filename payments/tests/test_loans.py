from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from rest_framework import status
from django.utils import timezone

from payments.models import Account, Loan
from payments.utils import UserUtils


def get_loan_data(receiver_pk):
    return {
        "receiver": receiver_pk,
        "lend_amount": 10,
        "interest_rate": 10,
        "due_date": timezone.now() + timezone.timedelta(days=10)
    }


class TestLoan(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.createloan_uri = "/createloan/"
        self.getloanstatus_uri = "/loanstatus/"
        self.payloan_uri = "/payloan/"
        self.transfer_uri = "/transferfunds/"
        self.superuser = UserUtils.setup_superuser('admin')
        self.user = UserUtils.setup_user('client')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    def test_create_loan(self):
        self.client.login(username="admin", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        loan_data = get_loan_data(receiver_pk=self.user_account.pk)
        response = self.client.post(self.createloan_uri, loan_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         "Expected status code 200 but got {} instead".format(response.status_code))

    def test_loan_status(self):
        self.client.login(username="admin", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        create_loan_data = get_loan_data(receiver_pk=self.user_account.pk)
        self.client.post(self.createloan_uri, create_loan_data)

        loan_pk = Loan.objects.all()[0].pk
        get_status_response = self.client.get(self.getloanstatus_uri + "{}/".format(loan_pk))
        self.assertEqual(get_status_response.status_code, status.HTTP_200_OK,
                         get_status_response)

    def test_pay_loan(self):
        self.client.login(username="admin", password="test")
        creation_data = {'amount': 50}
        self.client.put(self.create_uri, creation_data)

        create_loan_data = get_loan_data(receiver_pk=self.user_account.pk)
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


class TestLoanIntegral(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        self.create_uri = "/createfunds/"
        self.createloan_uri = "/createloan/"
        self.getloanstatus_uri = "/loanstatus/"
        self.payloan_uri = "/payloan/"
        self.transfer_uri = "/transferfunds/"
        self.superuser = UserUtils.setup_superuser('A')
        self.user = UserUtils.setup_user('B')
        self.superuser_account = Account.objects.get(user=self.superuser)
        self.user_account = Account.objects.get(user=self.user)

    def test_integral(self):
        self.client.login(username='A', password="test")

        # create funds for admin
        creation_data = {'amount': 100}
        self.client.put(self.create_uri, creation_data)

        # transfer funds to client to be able to return loan amount
        transfer_data = {'amount': 20}
        self.client.put(self.transfer_uri + "{}/".format(self.user_account.pk), transfer_data)

        # create loan from admin to client
        create_loan_data = get_loan_data(receiver_pk=self.user_account.pk)
        create_loan_response = self.client.post(self.createloan_uri, create_loan_data)
        self.assertEqual(create_loan_response.status_code, status.HTTP_201_CREATED,
                         "Loan creation failed. Expected 201 but got {} instead".format(
                             create_loan_response.status_code))

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
        self.client.login(username="B", password="test")
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

        pay_loan_response = self.client.put(self.payloan_uri, pay_loan_data)
        self.assertEqual(pay_loan_response.status_code, status.HTTP_200_OK,
                         "Second loan payment failed. Expected code 200 but got {} instead".format(
                             pay_loan_response.status_code))

        # get loan status -> paid
        loan_pk = Loan.objects.all()[0].pk
        get_status_response = self.client.get(self.getloanstatus_uri + "{}/".format(loan_pk))
        self.assertTrue(get_status_response.data['return_date'] is not None, "Third loan status failed")
