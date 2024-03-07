from django.db import models
from django.utils.translation import gettext_lazy as _

from user.models import CustomUser



class PaymentMethod(models.Model):
    name = models.CharField(max_length=150)
    payment_period = models.IntegerField(_("Length of payment period in months"))
    deposit = models.FloatField()

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=150, unique=True)
    price = models.FloatField()
    rate_percentage = models.FloatField(null=True, blank=True)
    source = models.FileField(upload_to='static/course_videos')
    description = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=50, null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)


    def __str__(self):
        return self.name


class Order(models.Model):
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    balance = models.FloatField()
    payment_progress = models.IntegerField(default=-1)
    contract_data = models.FileField(null=True, blank=True)

    extra_data = models.JSONField(null=True, blank=True)

    time_update = models.DateTimeField(auto_now=True)  # time when car order updated
    time_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # time when order has created


    def __str__(self):
        return f"{self.product}  ---  {self.client}"


class PaymentHistory(models.Model):
    payment_amount = models.FloatField()
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    time_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # time when order has created

    def __str__(self):
        return self.payment_amount