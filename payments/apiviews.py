from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import authenticate
from django.utils import timezone
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
import datetime
import decimal

from .models import Account, Transaction, Loan
from .serializers import UserSerializer, AccountSerializer, TransferLogSerializer, LoanSerializer
from .utils import TransferUtils, TransferLogUtils


class UserCreate(generics.CreateAPIView):
    authentication_classes = ()
    permission_classes = ()

    serializer_class = UserSerializer


class UserDestroy(generics.DestroyAPIView):
    serializer_class = UserSerializer


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            return Response({"token": user.auth_token.key})
        else:
            return Response({"error": "Wrong Credentials"}, status=status.HTTP_400_BAD_REQUEST)


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class TransferLogView(generics.ListCreateAPIView):
    serializer_class = TransferLogSerializer

    def get_queryset(self):
        return Transaction.objects.all()

    def post(self, transfer_log_data):
        response = TransferLogUtils.exec_transaction(transfer_log_data=transfer_log_data)
        return response


class FundCreation(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request):
        user = request.user
        if not user.is_staff:
            raise PermissionDenied

        account = Account.objects.get(user=user)
        updated_data = {'amount': account.amount + decimal.Decimal(request.data['amount'])}
        serializer = self.get_serializer(account, data=updated_data, partial=True)

        transaction_data = {'destination_account': user.pk, 'amount': request.data['amount']}

        if serializer.is_valid():
            serializer.save()
            TransferLogView.post(None, transaction_data)
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class FundDestruction(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request, account_pk):
        user = request.user
        if not user.is_staff:
            raise PermissionDenied

        account = Account.objects.get(pk=account_pk)
        updated_data = {'amount': account.amount - decimal.Decimal(request.data['amount'])}
        serializer = self.get_serializer(account, data=updated_data, partial=True)

        transaction_data = {'source_account': account_pk, 'amount': request.data['amount']}

        if serializer.is_valid():
            serializer.save()
            TransferLogView.post(None, transaction_data)
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class TransferFunds(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request, destination_account_pk):
        user = request.user
        source_account_pk = Account.objects.get(user=user).pk

        response = TransferUtils.exec_transfer(
            source_account_pk=source_account_pk,
            destination_account_pk=destination_account_pk,
            transfer_data=request.data
        )
        return response


class CreateLoan(generics.ListCreateAPIView):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    def post(self, request):
        loaner_account_pk = Account.objects.get(user=request.user).pk

        due_date = datetime.datetime.strptime(request.data['due_date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        loan_days = due_date.day - timezone.now().day

        loan_data = {**request.data, 'loaner': loaner_account_pk, 'loan_days': loan_days}
        loan_serializer = LoanSerializer(data=loan_data, partial=True)

        if not loan_serializer.is_valid():
            return Response({'message': 'failed', 'details': loan_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # Transfer generation
        transfer_data = {'amount': request.data['lend_amount']}
        transfer_response = TransferUtils.exec_transfer(
            source_account_pk=loaner_account_pk,
            destination_account_pk=request.data['receiver'],
            transfer_data=transfer_data
        )

        if transfer_response.status_code != status.HTTP_200_OK:
            return Response({'message': 'failed', 'details': 'loan transfer failed'},
                            status=status.HTTP_400_BAD_REQUEST)

        loan_serializer.save()
        return Response(loan_serializer.data, status=status.HTTP_201_CREATED)


class PayLoan(generics.UpdateAPIView):
    model = LoanSerializer

    #def update(self, request, *args, **kwargs):


class GetLoanStatus(generics.RetrieveAPIView):
    model = LoanSerializer

    def retrieve(self, request, loan_pk):
        loan = get_object_or_404(Loan, pk=loan_pk)
        loan_serializer = LoanSerializer(loan)
        return Response(loan_serializer.data, status=status.HTTP_200_OK)