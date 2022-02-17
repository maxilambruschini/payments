from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
import decimal

from payments.serializers import TransferLogSerializer, AccountSerializer
from payments.models import Transaction, Account
from payments.utils import TransferLogUtils, TransferUtils


class FundCreation(generics.UpdateAPIView):
    serializer_class = AccountSerializer
    permission_classes = [IsAdminUser]

    def update(self, request):
        account = get_object_or_404(Account, user=request.user)
        updated_data = {'amount': account.amount + decimal.Decimal(request.data['amount'])}
        serializer = self.get_serializer(account, data=updated_data, partial=True)

        transaction_data = {'destination_account': account.pk, 'amount': request.data['amount']}

        if serializer.is_valid():
            serializer.save()
            TransferLogUtils.exec_transaction(transaction_data)
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class FundDestruction(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request, account_pk):
        account = get_object_or_404(Account, pk=account_pk)
        updated_data = {'amount': account.amount - decimal.Decimal(request.data['amount'])}
        serializer = self.get_serializer(account, data=updated_data, partial=True)

        transaction_data = {'source_account': account_pk, 'amount': request.data['amount']}

        if serializer.is_valid():
            serializer.save()
            TransferLogUtils.exec_transaction(transaction_data)
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


class TransferLogView(generics.ListCreateAPIView):
    serializer_class = TransferLogSerializer

    def get_queryset(self):
        return Transaction.objects.all()

    def post(self, transfer_log_data):
        response = TransferLogUtils.exec_transaction(transfer_log_data=transfer_log_data)
        return response
