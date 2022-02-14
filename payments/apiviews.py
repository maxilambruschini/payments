from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import authenticate
import decimal

from .models import Account, Transaction
from .serializers import UserSerializer, AccountSerializer, TransactionSerializer


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


class TransactionView(generics.ListCreateAPIView):
    def get_queryset(self):
        #print(Transaction.objects.all()[0])
        return Transaction.objects.all()

    def post(self, transaction_data):
        serializer = TransactionSerializer(data=transaction_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer_class = TransactionSerializer


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
            TransactionView.post(None, transaction_data)
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
            TransactionView.post(None, transaction_data)
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class TransferFunds(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request, destination_account_pk):
        user = request.user

        source_account = Account.objects.get(user=user)
        source_amount = source_account.amount - decimal.Decimal(request.data['amount'])
        source_data = {'amount': source_amount}
        source_serializer = self.get_serializer(source_account, data=source_data, partial=True)

        if not source_serializer.is_valid():
            return Response({'message': 'failed', 'details': source_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        destination_account = Account.objects.get(pk=destination_account_pk)
        destination_amount = destination_account.amount + decimal.Decimal(request.data['amount'])
        destination_data = {'amount': destination_amount}
        destination_serializer = self.get_serializer(destination_account, data=destination_data, partial=True)

        transaction_data = {
            'destination_account': destination_account_pk,
            'source_account': source_account.pk,
            'amount': request.data['amount']
        }

        if not destination_serializer.is_valid():
            return Response({'message': 'failed', 'details': destination_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            source_serializer.save()
            destination_serializer.save()
            TransactionView.post(None, transaction_data)
            return Response({'message': 'Transfer successfull'},
                            status=status.HTTP_200_OK)