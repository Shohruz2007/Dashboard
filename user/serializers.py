from rest_framework import serializers
from .models import CustomUser, Notification, Comment
from django.core import exceptions
import django.contrib.auth.password_validation as validators


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=50)



class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'password', 'is_staff', 'is_superuser','is_analizer', 'is_client', 'email', 'address', 'phone_number', 'first_name', 'last_name', 'related_staff', 'image', 'first_name', 'last_name']

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

class UserShortDataSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150,)
    
    class Meta:
        model = CustomUser
        fields = ['id',"username", "first_name"]

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=50)
    related_staff = UserShortDataSerializer()
    
    class Meta:
        model = CustomUser
        fields = ['id',"password","username","image","email","phone_number","birthday","is_staff","is_superuser","is_analizer","is_client","related_staff","address","last_location","time_create","time_update", 'first_name', 'last_name', 'last_login', 'is_active']
        


class NotificationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Notification
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Comment
        fields = ['id', 'comment_owner','receiver','message','time_create','time_update',]

class CommentGETSerializer(serializers.ModelSerializer):
    is_owner_superuser = serializers.BooleanField(default=False)
    class Meta:
        model = Comment
        fields = ['id', 'comment_owner','receiver','message','time_create','time_update', 'is_owner_superuser']
