from rest_framework import serializers
from .models import CustomUser
from django.core import exceptions
import django.contrib.auth.password_validation as validators


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=50)



class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, max_length=20, min_length=6)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'is_staff', 'is_superuser', 'is_client', 'email', 'phone_number', 'first_name', 'last_name', 'related_staff']

    def validate(self, data):
        # print('USER DATA -->', data)
        user = CustomUser(**data)
        password = data.get('password')


        errors = dict()
        try:
            validators.validate_password(password=password, user=user)
        except exceptions.ValidationError as e:
            errors['password'] = list(e.messages)
        if errors:
            raise serializers.ValidationError(errors)
        return super(UserCreateSerializer, self).validate(data)

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user



class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomUser
        fields = '__all__'