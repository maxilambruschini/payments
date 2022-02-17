from rest_framework import generics, status
from rest_framework.response import Response
import decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone

from payments.models import Loan, Account
from payments.serializers import LoanSerializer
from payments.utils import TransferUtils, LoanUtils


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
