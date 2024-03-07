from django.urls import path, include
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'category', PrdCategoryViewset, basename='category')
router.register(r'order', OrderViewset, basename='order')
router.register(r'paymentmethod', PaymentMethodViewset, basename='paymentmethod')
router.register(r'', PrdViewset, basename='')
# router.register(r'full_data', FullDataView, basename='full_data')

urlpatterns = [
    path('full_data/', FullDataView.as_view({'get': 'get'})),
    path('payment/', PaymentPostView.as_view({'post': 'post'})),
    path('', include(router.urls)),
]
