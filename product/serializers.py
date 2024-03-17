from rest_framework import serializers
from django.core import exceptions
import django.contrib.auth.password_validation as validators

from .models import CustomUser, Category, Product, Order, PaymentMethod, PaymentHistory
from user.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)
    name = serializers.CharField(max_length=150)
    price = serializers.FloatField()
    rate_percentage = serializers.IntegerField()
    
    source = serializers.FileField()
    description = serializers.CharField()
    author = serializers.CharField(max_length=50)
    extra_data = serializers.JSONField()
    
    class Meta:
        model = Product
        fields = ["id", "name", "price", "rate_percentage", "source", "description", "author", "extra_data"]



class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'
        

class OrderSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    client = UserSerializer(read_only=True)
    time_update = serializers.DateTimeField(read_only=True)
    time_create = serializers.DateTimeField(read_only=True)
    class Meta:
        model = Order
        fields = ["payment_method", "product", "client", "balance", "payment_progress", "contract_data", "extra_data", "is_finished", "time_update", "time_create"]


class PaymentHistorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PaymentHistory
        fields = '__all__'

