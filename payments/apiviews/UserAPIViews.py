from rest_framework import generics, viewsets, status
from rest_framework.views import APIView, Response
from django.contrib.auth import authenticate

from payments.serializers import UserSerializer, AccountSerializer
from payments.models import Account


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
