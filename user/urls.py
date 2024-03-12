from django.views.decorators.csrf import csrf_exempt
from django.urls import path, include
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'user_data', UserGetAPIView, basename='user_data')
# router.register(r'notification', NotificationGetAPIView, basename='notification')

urlpatterns = [
    path('login/', csrf_exempt(LoginAPIView.as_view())),
    path('create/', UserCreateView.as_view()),
    path('location/', LocationAPIView.as_view()),
    path('notification/', NotificationGetAPIView.as_view({'get': 'get'})),
    path('', include(router.urls)),
]