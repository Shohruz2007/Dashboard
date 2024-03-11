from django.urls import path, include
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()
router.register(r'user_data', UserGetAPIView, basename='user_data')
router.register(r'notification', NotificationGetAPIView, basename='notification')

urlpatterns = [
    path('login/', LoginAPIView.as_view()),
    path('create/', UserCreateView.as_view()),
    path('location/', LocationAPIView.as_view()),
    path('', include(router.urls)),
]