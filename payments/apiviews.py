from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import authenticate
import decimal

from .models import Account
from .serializers import UserSerializer, AccountSerializer


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


class AccountView(generics.ListCreateAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class FundCreation(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request):
        user = request.user
        if not user.is_staff:
            raise PermissionDenied

        account = Account.objects.get(user=user)
        serializer = self.get_serializer(account, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
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
        updated_amount = account.amount - decimal.Decimal(request.data['amount'])
        updated_data = {'amount': updated_amount}
        serializer = self.get_serializer(account, data=updated_data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response({"message": "failed", "details": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


class TransferFunds(generics.UpdateAPIView):
    serializer_class = AccountSerializer

    def update(self, request, destination_account_pk):
        user = request.user

        source_account = Account.objects.get(user=user)
        source_data = {'amount': source_account.amount - decimal.Decimal(request.data['amount'])}
        source_serializer = self.get_serializer(source_account, data=source_data, partial=True)

        if not source_serializer.is_valid():
            return Response({'message': 'failed', 'details': source_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        destination_account = Account.objects.get(pk=destination_account_pk)
        destination_data = {'amount': request.data['amount']}
        destination_serializer = self.get_serializer(destination_account, data=destination_data, partial=True)

        if not destination_serializer.is_valid():
            return Response({'message': 'failed', 'details': destination_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        else:
            source_serializer.save()
            destination_serializer.save()
            return Response({'message': 'Transfer successfull'},
                            status=status.HTTP_200_OK)