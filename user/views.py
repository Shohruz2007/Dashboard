from django.shortcuts import render
from django.contrib.auth import get_user_model, authenticate, login
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser
from Admin_panel.permissions import IsAdminUserOrStaff
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import LoginSerializer, UserSerializer, UserCreateSerializer



class LoginAPIView(generics.GenericAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        username = data.get("username")
        password = data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return Response(self.get_tokens_for_user(user), status=status.HTTP_202_ACCEPTED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def get_tokens_for_user(self, user):  # getting JWT token and is_staff boolean
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }


class UserCreateView(generics.GenericAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["post"]
    
    def post(self, request, *args, **kwargs):
        new_user_data:dict = request.data
        creator = request.user
        
        permissions = {'is_superuser':[creator.is_superuser], "is_staff":[creator.is_superuser]}

        # print('CREATOR -->', creator.is_staff)
        for data_type,has_access in permissions.items():
            if data_type in new_user_data and (new_user_data[data_type] in [['True'],'True', True]):
                if not True in has_access:
                    return Response({"error": f"You don't have enough permissions to set {data_type}"},status=status.HTTP_406_NOT_ACCEPTABLE)
        
        password = new_user_data.get('password')

        if password is None and new_user_data['is_client'] in [['True'], 'True', True]:
            new_user_data = new_user_data.copy()
            password = new_user_data['password'] = new_user_data['username'] + '_code'
            
            new_user_data['related_staff'] = creator.id


        serializer = self.serializer_class(data=new_user_data)
        # print('SERIALIZER -->', serializer)

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response({'error':"Data is not valid"},status=status.HTTP_406_NOT_ACCEPTABLE)


class UserListPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 30
    page_size_query_param = 'page_size'



class UserGetAPIView(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["get", "put", "delete"]
    pagination_class = UserListPagination



    def list(self, request, *args, **kwargs):

        params = dict(request.GET)

        # print(params.get('user_type')[0])
        user_type = (params.get('user_type')[0] if not params.get('user_type') is None else None)
        if not request.user.is_superuser and (request.user.is_staff and not user_type == 'client'):
            return Response({'error':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        
        
        queryset = self.filter_queryset(self.get_queryset())
        
        queryset_filter = {
                            'client':queryset.filter(is_client=True) if request.user.is_superuser else queryset.filter(related_staff=request.user.id),
                            'staff':queryset.filter(is_staff=True),
                            'admin':queryset.filter(is_superuser=True)
                           }

        try:
            queryset = queryset_filter[user_type]
        except:pass
        
        print('QUERYSET -->', queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
    def retrieve(self, request, *args, **kwargs):
        request_pk = request.parser_context['kwargs']['pk']
        print('PK -->', request_pk)
        if request_pk.lower() == 'self':
            request_pk = request.user.id
        
        instance = self.queryset.filter(pk=request_pk).first()
        print('user_data -->', instance)
        
        if instance is None:
            return Response({'err':"user no found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = self.get_serializer(instance)
        
        user_data = serializer.data
        staff = request.user
        
        if staff.is_superuser or user_data['related_staff'] == staff.id or request_pk==request.user.id:
            return Response(user_data)
        else:
            return Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)
    
    
    def update(self, request, *args, **kwargs):
        
        
        partial = kwargs.pop('partial', True)
        
        request_pk = request.parser_context['kwargs']['pk']
        # print('PK -->', request_pk)
        if request_pk.lower() == 'self':
            request_pk = request.user.id
        
        instance = self.queryset.filter(pk=request_pk).first()
        
        if instance is None:
            return Response({'err':"user no found"}, status=status.HTTP_404_NOT_FOUND)
        # print('USER OBJ -->', instance.__dict__)
        
        staff = request.user
        if not staff.is_superuser and not instance.related_staff_id == staff.id and not request_pk==request.user.id:
            return Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)

        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    
    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()
        staff = request.user
        
        if not staff.is_superuser and not instance.related_staff_id == staff.id:
            return Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
