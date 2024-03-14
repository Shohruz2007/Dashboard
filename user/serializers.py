from rest_framework import serializers
from .models import CustomUser, Notification
from django.core import exceptions
import django.contrib.auth.password_validation as validators


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=50)



class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'is_staff', 'is_superuser','is_analizer', 'is_client', 'email', 'phone_number', 'first_name', 'last_name', 'related_staff', 'image', 'first_name', 'last_name']

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
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=50)
    
    
    class Meta:
        model = CustomUser
        fields = ['id',"password","username","image","email","phone_number","birthday","is_staff","is_superuser","is_analizer","is_client","related_staff","last_location","time_create","time_update", 'first_name', 'last_name', 'last_login']
        


class NotificationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Notification
        fields = '__all__'
