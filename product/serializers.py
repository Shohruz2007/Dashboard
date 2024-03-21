from rest_framework import serializers
from django.core import exceptions
import django.contrib.auth.password_validation as validators

from .models import CustomUser, Category, Product, Order, PaymentMethod, PaymentHistory
from user.serializers import UserSerializer, RelatedUserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
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
        fields = ["id", "payment_method", "product", "client", "balance", "payment_progress", "contract_data", "extra_data", "is_finished", "time_update", "time_create"]

class OrderCreateSerializer(serializers.ModelSerializer):
    time_update = serializers.DateTimeField(read_only=True)
    time_create = serializers.DateTimeField(read_only=True)
    class Meta:
        model = Order
        fields = ["id", "payment_method", "product", "client", "balance", "payment_progress", "contract_data", "extra_data", "is_finished", "time_update", "time_create"]


class OrderShortdataSerializer(serializers.ModelSerializer):
    client = RelatedUserSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ["id", "client"]

class PaymentHistorySerializer(serializers.ModelSerializer):
    order = OrderShortdataSerializer(read_only=True)
    class Meta:
        model = PaymentHistory
        fields = ['id', 'payment_amount', 'order', 'time_create']

class DashboardSerializer(serializers.Serializer):
    payment = PaymentHistorySerializer()
    order = OrderSerializer()
    product = ProductSerializer()