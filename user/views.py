import datetime
import requests
from dateutil.relativedelta import relativedelta
import certifi
import ssl
from urllib.parse import unquote

from geopy.geocoders import Nominatim, options

from django.shortcuts import render
from django.contrib.auth import get_user_model, authenticate, login, backends
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db.models import Q


from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser
from Admin_panel.permissions import IsAdminUserOrStaff
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, Notification
from product.models import Order, PaymentHistory
from product.serializers import OrderSerializer
from .serializers import LoginSerializer, UserSerializer, UserCreateSerializer, NotificationSerializer



class LoginAPIView(generics.GenericAPIView):

    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)
    http_method_names = ["post"]
    authentication_classes = [backends.ModelBackend]

    def post(self, request, *args, **kwargs):
        data = request.data
        username, password = data.get('username'), data.get('password')
        if None in [username, password]:
            return Response({'err':'Data is not full'},status=status.HTTP_406_NOT_ACCEPTABLE)
            
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            
            user_token = self.get_tokens_for_user(user)

            user_data = UserSerializer(user)
            return Response(user_data.data | user_token, status=status.HTTP_202_ACCEPTED)
        return Response({'err':'Username or password went wrong'},status=status.HTTP_400_BAD_REQUEST)

    def get_tokens_for_user(self, user):  # getting JWT token and is_staff boolean
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class UserCreateView(generics.GenericAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["post"]
    
    def post(self, request, *args, **kwargs):
        new_user_data:dict = dict(request.data.copy())
        
        
        for name, value in dict(new_user_data).items():
            if type(value) is list:
                new_user_data[name] = value[0]
        
        creator = request.user
        
        permissions = {'is_superuser':[creator.is_superuser], "is_staff":[creator.is_superuser], "is_analizer":[creator.is_superuser]}

        # print('CREATOR -->', creator.is_staff)
        for data_type,has_access in permissions.items():
            if data_type in new_user_data and (new_user_data[data_type] in [['True'],'True', True]):
                if not True in has_access:
                    return Response({"error": f"You don't have enough permissions to set {data_type}"},status=status.HTTP_406_NOT_ACCEPTABLE)
        
        password = new_user_data.get('password')

        
        
        
        if new_user_data.get('is_client') in [['True'], 'True', True, 'true', ['true']]:
            if password is None:
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
        user = request.user
        user_type = (params.get('user_type')[0] if not params.get('user_type') is None else 'none')
        related_staff = (params.get('related_staff')[0] if not params.get('related_staff') is None else None)

        # print(not related_staff is None and user.is_superuser, related_staff)
        
        permissions = {
            'client':{'requirements':[user.is_superuser, user.is_staff], 'queryset':(CustomUser.objects.filter(is_client=True) if user.is_superuser or user.is_analizer else CustomUser.objects.filter(is_client=True, related_staff=user))},
            'staff':{'requirements':[user.is_superuser], 'queryset':CustomUser.objects.filter(is_staff=True, is_superuser=False)},
            'admin':{'requirements':[user.is_superuser], 'queryset':CustomUser.objects.filter(is_superuser=True)},
            'none':{'requirements':[True], 'queryset':(CustomUser.objects.all() if user.is_superuser or user.is_analizer else CustomUser.objects.filter(related_staff=user))},
                        }

        if True in permissions[user_type]['requirements']:
            # print('QURYSET DATA')
            queryset = permissions[user_type]['queryset']

        else:

            return Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)

        if not related_staff is None:
            queryset = queryset.filter(related_staff=related_staff)


        search_data = params.get('search')
        
        if not search_data is None:
            search_data:str = unquote(search_data if not type(search_data) is list else search_data[0])
            search_data = search_data.split()
            print("search_data -->", search_data)
            
            
            queryset_collector = []
            for item in search_data:
                queryset_part = queryset.filter(Q(id__icontains=item) | Q(username__icontains=item) | Q(first_name__icontains=item) | Q(phone_number__icontains=item))
                queryset_collector.extend(queryset_part)
            queryset = queryset_collector
            print("queryset -->", queryset_collector)
            

        queryset_filtered = []
        for query_obj in queryset:
            if not query_obj in queryset_filtered:
                queryset_filtered.append(query_obj)
        
        page = self.paginate_queryset(queryset_filtered)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # serializer = self.get_serializer(queryset, many=True)
        return (Response(serializer.data) if not queryset_filtered == [] else Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE))
    
    
    def retrieve(self, request, *args, **kwargs):
        request_pk = request.parser_context['kwargs']['pk']
        print('PK -->', request_pk)
        print('USER -->', request.user)
        
        
        if request_pk.lower() == 'self':
            request_pk = request.user.id
        
        instance = self.queryset.filter(pk=request_pk).first()
        print('user_data -->', instance)
        
        if instance is None:
            return Response({'err':"user no found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = self.get_serializer(instance)
        
        user_data:dict = serializer.data
        staff = request.user
        

        
        if staff.is_superuser or request.user.is_analizer or (not user_data['related_staff'] is None and user_data['related_staff'].get('id') == staff.id) or request_pk==request.user.id:
            if user_data['is_staff'] == True:
                orders = Order.objects.filter(creator=user_data['id']).select_related('product').select_related('payment_method')
                # print('orders -->', orders)
                payments = []

                order_pks = tuple([order.id for order in orders])
                for pk in order_pks:
                    payments.extend(PaymentHistory.objects.filter(order=pk))

                current_time = datetime.datetime.today()
                
                next_month_income = []
                for order in orders:
                    if order.is_finished:
                        continue
                    
                    product = order.product
                    payment_method = order.payment_method
                    payment_progress = order.payment_progress + (1 if not payment_method.payment_period-1 == order.payment_progress else 0)
                    months_passed:datetime.timedelta = (current_time.replace(tzinfo=datetime.timezone.utc)-order.time_create).days//30
                    if months_passed >= payment_method.payment_period:
                        months_passed = payment_method.payment_period
                    else:
                        months_passed += 1
                    # print(months_passed)
                    
                    monthly_payment = (product.price+payment_method.extra_payment-payment_method.deposit)/payment_method.payment_period
                    predicted_income = payment_method.deposit+(months_passed*monthly_payment)-order.balance
                    if predicted_income > 0:
                        next_month_income.append(predicted_income)
                    # print(monthly_payment)
                    
                user_data.update({"current_month":{
                "sale_amount":sum([payment.payment_amount for payment in payments if payment.time_create.month == current_time.month and payment.time_create.year == current_time.year and payment.time_create.day == current_time.day])
                }, 'orders':len(orders), "next_month_income":sum(next_month_income)})
                
            return Response([user_data])
        else:
            return Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)
    
    
    def update(self, request, *args, **kwargs):
        
        
        partial = kwargs.pop('partial', True)
        
        request_pk = request.parser_context['kwargs']['pk']
        data:dict = request.data
        # print('PK -->', request_pk)
        if request_pk.lower() == 'self':
            request_pk = request.user.id
        
        instance = self.queryset.filter(pk=request_pk).first()
        
        if instance is None:
            return Response({'err':"user not found"}, status=status.HTTP_404_NOT_FOUND)
        # print('USER OBJ -->', instance.__dict__)
        
        staff = request.user
        if not staff.is_superuser:
            if not instance.related_staff_id == staff.id and not request_pk==request.user.id:
                return Response({'err':"you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            
            accepted_data = ['image', 'first_name', 'last_name', 'phone_number']
            for key_name in data.keys():
                if not key_name in accepted_data:
                    return Response({'err':f"you don't have enough permissions to update {key_name}"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            


        
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if 'password' in data.keys():
            instance.set_password(data['password'])
            instance.save()
            new_data = data.copy()
            new_data.pop('password')
            serializer = self.get_serializer(instance, data=new_data, partial=partial)
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



class NotificationGetAPIView(viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = (IsAdminUserOrStaff,)
    pagination_class = UserListPagination
    
    # @method_decorator(cache_page(60*60*6))
    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            queryset = Notification.objects.filter(receiver = request.user)
        else:
            queryset = Notification.objects.all()


        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)



def ClientPaymentCheck():
    orders = Order.objects.filter(is_finished=False)
    for order in orders:
        if order.client.related_staff is None:
            continue


        print(order.client.related_staff)
        balance = order.balance
        product_price = order.product.price
        payment_deposit = order.payment_method.deposit
        extra_payment = order.payment_method.extra_payment
        payment_period = order.payment_method.payment_period
        current_time = datetime.datetime.today()
        monthly_payment = float(product_price-payment_deposit+extra_payment)/(payment_period if not payment_period==0 else 1)
        required_payment = balance-payment_deposit
        # print('required_payment -->', required_payment)
        if required_payment<0:
            continue #TODO DON'T Know what to do
        
        # print('CURRENT ORDER AND MONTHLY PAYMENT -->', order, monthly_payment)
        payment_period_progress = required_payment//monthly_payment
        # print('payment_period_progress -->', int(payment_period_progress))
        order_time = order.time_create
        next_payment_days_left =  ((order_time+relativedelta(months=1*payment_period_progress)).date()-current_time.date()).days
        
        # print('\nnext_payment_days_left -->', next_payment_days_left)
        message = None
        if next_payment_days_left == 3:
            message = f"{order.client.username} nomli klientning keyingi to'lovigacha 3 kun qoldi, to'lov summasi {monthly_payment}"
            
        if next_payment_days_left == -1:
            message = f"{order.client.username} nomli klientning to'lovi 1 kunga o'tdi, to'lov summasi {monthly_payment}"
        
        if not message is None:
            serializer = NotificationSerializer(data={'receiver':order.client.related_staff.id, 'message':message})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            print(serializer.data)



def replace_russian_letters(text):

    replacements = {'а': 'a','б': 'b','в': 'v','г': 'g','д': 'd','е': 'e','ё': 'yo','ж': 'j','з': 'z','и': 'i','й': 'y','к': 'k','л': 'l','м': 'm','н': 'n','о': 'o','п': 'p','р': 'r','с': 's','т': 't','у': 'u','ф': 'f','х': 'x','ц': 'ts','ч': 'ch','ш': 'sh','щ': 'sh','ъ': '','ы': 'i','ь': '','э': 'e','ю': 'yu','я': 'ya'} 


    result = ''
    for char in text:
        if char.lower() in replacements:
            replacement = replacements[char.lower()]
            if char.isupper():
                result += replacement.capitalize()
            else:
                result += replacement[0]

        else:
            result += char

    return result


class LocationAPIView(generics.GenericAPIView):

    permission_classes = (AllowAny,)
    http_method_names = ["post"]

    def post(self, request):
        data = request.data
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if None in [latitude, longitude]:
            return Response({'err':"don't have enough info. please check data you giving"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        


        ctx = ssl.create_default_context(cafile=certifi.where())
        options.default_ssl_context = ctx
        
        geolocator = Nominatim(user_agent='my-app')
        
        
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if not location is None:
            location:list = location[0].split(',')


            for obj_id,adress_obj in enumerate(location[:]):
                if type(adress_obj) is str:
                    adress_obj = adress_obj.strip()
                    location[obj_id] = ' '+replace_russian_letters(adress_obj)



            location.reverse()
            
            user = request.user
            instance = CustomUser.objects.filter(pk=user.id).first()
            if instance is None:
                return Response({'err': 'user not found'}, status=status.HTTP_404_NOT_FOUND)


            print('instance.last_location -->',instance.last_location)
            
            instance.last_location = location[2:]
            instance.save()
            
            return Response(instance.last_location,)
        return Response({'err': 'location not found'}, status=status.HTTP_404_NOT_FOUND)