from rest_framework import serializers
from .models import Account, Transaction, Loan
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'is_superuser')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        Token.objects.create(user=user)
        return user


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'

    def validate(self, validated_data):
        if validated_data['amount'] < 0:
            raise serializers.ValidationError('amount cannot be negative')
        return validated_data


class TransferLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"

    def validate(self, validated_data):
        if validated_data['amount'] < 0:
            raise serializers.ValidationError('amount cannot be negative')
        return validated_data



class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = "__all__"

    def validate(self, validated_data):
        if 'lend_amount' in validated_data and validated_data['lend_amount'] < 0:
            raise serializers.ValidationError('lend amount cannot be negative')

        if 'due_date' in validated_data and validated_data['due_date'] < timezone.now():
            raise serializers.ValidationError('due date must be in the future')

        return validated_data
