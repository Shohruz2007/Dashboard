from django.contrib import admin
from .models import Category, Product, Order, PaymentMethod, PaymentHistory


admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(PaymentMethod)
admin.site.register(PaymentHistory)