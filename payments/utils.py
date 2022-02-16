import decimal
from rest_framework.response import Response
from rest_framework import status
from .models import Account
from .serializers import AccountSerializer, TransferLogSerializer


class TransferLogUtils:
    @staticmethod
    def exec_transaction(transfer_log_data):
        serializer = TransferLogSerializer(data=transfer_log_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return


class TransferUtils:
    @staticmethod
    def exec_transfer(source_account_pk, destination_account_pk, transfer_data):
        source_account = Account.objects.get(pk=source_account_pk)
        source_amount = source_account.amount - decimal.Decimal(transfer_data['amount'])
        source_data = {'amount': source_amount}
        source_serializer = AccountSerializer(source_account, data=source_data, partial=True)

        if not source_serializer.is_valid():
            return Response({'message': 'failed', 'details': source_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        destination_account = Account.objects.get(pk=destination_account_pk)
        destination_amount = destination_account.amount + decimal.Decimal(transfer_data['amount'])
        destination_data = {'amount': destination_amount}
        destination_serializer = AccountSerializer(destination_account, data=destination_data, partial=True)

        if not destination_serializer.is_valid():
            return Response({'message': 'failed', 'details': destination_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        source_serializer.save()
        destination_serializer.save()

        # Transaction generation
        transfer_log_data = {
            'destination_account': destination_account_pk,
            'source_account': source_account_pk,
            'amount': transfer_data['amount']
        }
        transfer_log_response = TransferLogUtils.exec_transaction(transfer_log_data)

        if transfer_log_response.status_code != status.HTTP_201_CREATED:
            return Response({'message': "Transfer log generation failed"},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Transfer successfull'},
                        status=status.HTTP_200_OK)


class LoanUtils:
    @staticmethod
    def get_total_return_amount(lend_amount, interest_rate):
        return decimal.Decimal(round(lend_amount * decimal.Decimal(1 + interest_rate / 100), 2))
