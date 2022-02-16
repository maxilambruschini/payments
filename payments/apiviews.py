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
from .utils import TransferUtils, TransferLogUtils, LoanUtils


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

        loan_data = {
            'loaner': loaner_account_pk,
            'receiver': request.data['receiver'],
            'lend_amount': request.data['lend_amount'],
            'due_date': request.data['due_date'],
            'interest_rate': request.data['interest_rate']
        }
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

    @staticmethod
    def validate_amount(loan, payed_amount, total_return_amount):
        # validate loan receiver does not return in excess
        remaining_return_amount = total_return_amount - loan.returned_amount

        if decimal.Decimal(payed_amount) > remaining_return_amount:
            return False
        else:
            return True

    @staticmethod
    def validate_user(loan, receiver_user_pk):
        # validate logged user is the loan receiver
        if loan.receiver.user.pk != receiver_user_pk:
            return False
        else:
            return True

    def update(self, request):
        loan = get_object_or_404(Loan, pk=request.data['loan_id'])

        # payed loan validation
        if loan.return_date is not None:
            return Response({
                'message': 'failed',
                'details': 'loan is already returned'
            }, status=status.HTTP_400_BAD_REQUEST)

        # excess payment validation
        total_return_amount = LoanUtils.get_total_return_amount(loan.lend_amount, loan.interest_rate)
        if not self.validate_amount(
                loan=loan, payed_amount=request.data['payed_amount'], total_return_amount=total_return_amount):
            return Response({
                'message': 'failed',
                'details': 'payed amount is greater than the amount owed'
            }, status=status.HTTP_403_FORBIDDEN)

        # logged user validation
        if not self.validate_user(loan, request.user.pk):
            return Response({
                'message': 'failed',
                'details': 'logged user is not the loan receiver'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Transfer generation
        transfer_data = {'amount': request.data['payed_amount']}
        transfer_response = TransferUtils.exec_transfer(
            source_account_pk=loan.receiver.pk,
            destination_account_pk=loan.loaner.pk,
            transfer_data=transfer_data
        )

        if transfer_response.status_code != status.HTTP_200_OK:
            return Response({'message': 'failed', 'details': 'Transfer failed'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Update loan
        returned_amount = decimal.Decimal(request.data['payed_amount']) + loan.returned_amount
        updated_loan_data = {'returned_amount': returned_amount}

        if returned_amount == LoanUtils.get_total_return_amount(loan.lend_amount, loan.interest_rate):
            updated_loan_data = {**updated_loan_data, 'return_date': timezone.now()}
        loan_serializer = LoanSerializer(loan, data=updated_loan_data, partial=True)

        if not loan_serializer.is_valid():
            return Response({'message': 'failed', 'details': 'loan update failed'},
                            status=status.HTTP_400_BAD_REQUEST)

        loan_serializer.save()
        return Response(loan_serializer.data, status=status.HTTP_200_OK)


class GetLoanStatus(generics.RetrieveAPIView):
    model = LoanSerializer

    def retrieve(self, request, loan_pk):
        loan = get_object_or_404(Loan, pk=loan_pk)
        loan_serializer = LoanSerializer(loan)
        return Response(loan_serializer.data, status=status.HTTP_200_OK)
