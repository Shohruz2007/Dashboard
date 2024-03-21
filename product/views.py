import datetime
import threading
from multiprocessing.dummy import Pool as ThreadPool
import time
import queue

from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from Admin_panel.permissions import IsAdminUserOrStaff, IsAdminUser, IsAdminUserOrStaffReadOnly
from rest_framework_simplejwt.tokens import RefreshToken


from .serializers import CustomUser, Category, CategorySerializer, Product, ProductSerializer, PaymentMethod, PaymentMethodSerializer, Order, OrderSerializer, OrderCreateSerializer, PaymentHistory, PaymentHistorySerializer


class PrdCategoryViewset(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsAdminUser,)


class PrdViewset(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (IsAdminUserOrStaffReadOnly,)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)



class PaymentMethodViewset(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = (IsAdminUserOrStaffReadOnly,)


    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrderViewset(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('client').select_related('product')
    serializer_class = OrderSerializer
    permission_classes = (IsAdminUserOrStaff,)

    def create(self, request, *args, **kwargs):
        data = dict(request.data.copy())
        is_related = False
        if not request.user.is_superuser:
            if request.user.is_staff:
                client_id = data.get("client")

                if type(client_id) is None:
                    return Response({"err":"No client data"}, status=status.HTTP_404_NOT_FOUND)
                    
                if type(client_id) is list:
                    client_id = client_id[0]
                
                client = CustomUser.objects.filter(id=client_id).first()
                if not client is None:
                    is_related = client.related_staff==request.user
        else:
            is_related = True
        
        if not is_related:
            return Response({"err":"you don't have permissions"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        

        for name, value in dict(data).items():
            if type(value) is list:
                data[name] = value[0]
        
        print('data --->',data)
        
        payment = PaymentMethod.objects.filter(id=data.get('payment_method')).first()
        product = Product.objects.filter(id=data.get('product')).first()
        
        if None in [payment,product]:
            return Response({'err': "detail not found"}, status=status.HTTP_404_NOT_FOUND)
            
        def payment_check():
            if float(payment.deposit) > float(product.price):
                return (False, {"err":"Payment deposit amount cann't be bigger than product price"})
            return (True, None)
        
        payment_status, err = payment_check()
        if not payment_status:
            return Response(err, status=status.HTTP_406_NOT_ACCEPTABLE)
        
        
        print('BEFORE SERIALIZER')
        serializer = OrderCreateSerializer(data=dict(data))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        instance = Order.objects.get(id=serializer.data['id'])
        get_serializer = self.get_serializer(instance)
        return Response(get_serializer.data, status=status.HTTP_201_CREATED)
    
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        is_related = False
        if not request.user.is_superuser and not request.user.is_analizer:
            if request.user.is_staff:
                is_related = instance.client.related_staff==request.user
        else:
            is_related = True
        
        if not is_related:
            return Response({"err":"you don't have permissions"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    
    def list(self, request, *args, **kwargs):
        
        if not request.user.is_superuser and not request.user.is_analizer:
            if request.user.is_staff:
                queryset = Order.objects.all()
                # print([order.client.related_staff for order in queryset if ])
                queryset = [order for order in queryset if not order.client.related_staff is None and order.client.related_staff.id == request.user.id]

        else:
            queryset = self.filter_queryset(self.get_queryset())
            

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        is_related = False
        if not request.user.is_superuser:
            if request.user.is_staff:
                is_related = instance.client.related_staff==request.user
        else:
            is_related = True
        
        if not is_related:
            return Response({"err":"you don't have permissions"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        is_related = False
        if not request.user.is_superuser:
            if request.user.is_staff:
                is_related = instance.client.related_staff==request.user
        else:
            is_related = True
        
        if not is_related:
            return Response({"err":"you don't have permissions"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class PaymentPostView(viewsets.GenericViewSet):
    queryset = PaymentHistory.objects.all().select_related('order')
    serializer_class = PaymentHistorySerializer
    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["post", "get"]


    def post(self, request, *args, **kwargs):
        print(request.META.get('HTTP_AUTHORIZATION'))
        params = dict(request.GET)
        try:
            data = {'order':int(params.get('order')[0]),'payment_amount':float(str(params.get('amount')[0]).replace(' ',''))}
            print(data)
        except Exception as err:
            print('ERR IN PARAMS -->', err)
            return Response({'err': "data is wrong"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        # print('ORDER INSIDE PAYMENT -->', serializer.data)
        
        payment_amount = data.get('payment_amount')
        order = data.get('order')
        order = Order.objects.get(id=order)
        # print('IS TRUE STAFF --> ',order.client.related_staff)
        # print('IS TRUE STAFF --> ',order.client.related_staff == request.user.id)
        if not request.user.is_superuser and not (order.client.related_staff.id == request.user.id):
            return Response({'err': "you don't have enough permissions"}, status=status.HTTP_406_NOT_ACCEPTABLE)

        
        balance = order.balance + float(payment_amount)
        total_coast = order.product.price + order.payment_method.extra_payment
        
        if balance > total_coast:
            return Response({'err': "Balace cann't be more than product price with extra payment", 'max_payment':total_coast-order.balance}, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            order.balance = balance

        print(order.balance)

        print('ORDER PAYMENT PERIOD -->', order.payment_method.payment_period)

        payment_deposit = order.payment_method.deposit
        extra_payment = order.payment_method.extra_payment
        price = order.product.price
        payment_period = order.payment_method.payment_period

        if balance == total_coast:
            order.is_finished = True



        # print('FULL DATA -->', price,payment_deposit,extra_payment, payment_period)
        per_month_payment = (price-payment_deposit+extra_payment)/(payment_period if not payment_period==0 else 1)
        
        # print('ORDER MONTHLY PAYMENT PERIOD -->', per_month_payment)

        required_payment = balance-payment_deposit
        payment_period_progress = required_payment//per_month_payment
        # print('PAYMENT PROGRESS -->', order, payment_period_progress)
        
        order.payment_progress = payment_period_progress
        order.save()
        
        
        serializer.save()
        ord_serializer = OrderSerializer(order)
        return Response(ord_serializer.data)
    


    def list(self, request, *args, **kwargs):
        
        if not request.user.is_superuser and not request.user.is_analizer:
            return Response({'err':"You don't have permissions to do it"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            queryset = PaymentHistory.objects.all()
            

        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)
        

class DashboardBaseDataView(viewsets.GenericViewSet):

    permission_classes = (IsAdminUser,)
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        params = request.query_params
        
        
        users = CustomUser.objects.all()
        products = Product.objects.all()
        orders = Order.objects.all().select_related('product')
        payments = PaymentHistory.objects.all()
        current_time = datetime.datetime.today()
        
        clients = users.filter(is_client=True)
        
        # top_courses_amount = params.get('top_courses')
        
        # ordered_courses = [order.product for order in orders]
        # sorted_ordered_courses = list(set(sorted(ordered_courses, key=lambda obj: ordered_courses.count(obj), reverse=True)))
        # if top_courses_amount is None or not top_courses_amount.isnumeric():
        #     top_courses_amount = 10
            
        # sorted_ordered_courses = sorted_ordered_courses[:int(top_courses_amount)]
        # sorted_ordered_courses = [{"id":ordered_course.id, "name":ordered_course.name, 'price':ordered_course.price, 'amount':ordered_courses.count(ordered_course)} for ordered_course in sorted_ordered_courses]
        
        # for order in orders:
            
        
        months = [0, 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr']
        
        current_year_orders = [order for order in orders if order.time_create.year == current_time.year]
        yearly_data = []
        for month_number in range(1,13):
            products_data = []
            for order in current_year_orders:
                # print('current_time --> ', current_time.month)
                if order.time_create.month == month_number:
                    products_data.append(order.product)
            
            def find_most_repeated_object(collection):
                counts = {}
                most_repeated_obj = None
                max_count = 0

                # Count the occurrences of each object in the collection
                for obj in collection:
                    if obj in counts:
                        counts[obj] += 1
                    else:
                        counts[obj] = 1

                    # Update the most repeated object if necessary
                    if counts[obj] > max_count:
                        max_count = counts[obj]
                        most_repeated_obj = obj

                return most_repeated_obj, max_count
            
            
            most_saled_product,sales_amount = find_most_repeated_object(products_data)
            yearly_data.append({
                'Oy': months[month_number],
                'Mahsulot':most_saled_product.name if not most_saled_product is None else None, 
                'Sotuvlar soni': sales_amount,
            })
        
        
        response_data = {
            "product_len":len(products),
            "order_len":len(orders),
            "current_day":{
                "sale_amount":sum([payment.payment_amount for payment in payments if payment.time_create.month == current_time.month and payment.time_create.year == current_time.year and payment.time_create.day == current_time.day])
                },
            "current_month":
                {
                    "new_clients":len([client for client in clients if client.time_create.month == current_time.month and client.time_create.year == current_time.year]),
                    "new_orders":len([order for order in orders if order.time_create.month == current_time.month and order.time_create.year == current_time.year]),
                    "sale_amount":sum([payment.payment_amount for payment in payments if payment.time_create.month == current_time.month and payment.time_create.year == current_time.year])
                 },
            "current_year":{
                    "sale_amount":sum([payment.payment_amount for payment in payments if payment.time_create.year == current_time.year])
                },
            # "most_seller_courses":sorted_ordered_courses,
            "yearly_course_data":yearly_data,

        }
        
        return Response(response_data)

class FullDataView(viewsets.GenericViewSet):

    permission_classes = (IsAdminUser,)
    http_method_names = ["get"]

    @method_decorator(cache_page(60))
    def get(self, request, *args, **kwargs):
        params = request.query_params
        start_time = time.time()

        payments = PaymentHistory.objects.all().select_related('order')
        
        end_time = time.time()
        execution_time = end_time - start_time
        print(execution_time)
        
        current_time = datetime.datetime.today()
        # print('\n\n',current_time, '\n')
        
        
        last_payments_amount = params.get('last_pays')
        if last_payments_amount is None or not last_payments_amount.isnumeric():
            last_payments_amount = 5
            
        start_time = time.time()    

        last_payments = [{'payment_amount':payment.payment_amount, 'client':(payment.order.client.first_name if not payment.order is None else None), 'product':(payment.order.product.name if not payment.order is None else None), 'time_create':payment.time_create} for payment in payments.order_by('-time_create')]

        end_time = time.time()
        execution_time = end_time - start_time
        print(execution_time)
        
        last_payments = last_payments[:int(last_payments_amount)]
            
        
        months = [0, 'Yanv', 'Fevr', 'Mart', 'Apre', 'May', 'Iyun', 'Iyul', 'Avgu', 'Sent', 'Okty', 'Noya', 'Deka']
        
        current_year_payments = [payment for payment in payments if payment.time_create.year == current_time.year]
        yearly_data = []
        for month_number in range(1,13):
            month_sales = 0
            for payment in current_year_payments:
                # print('current_time --> ', current_time.month)
                if payment.time_create.month == month_number:
                    try:
                        month_sales += payment.payment_amount
                    except:pass
            
            yearly_data.append({
                'Oy': months[month_number],
                'Sotuvlar soni': month_sales
            })
            
        response_data = {
            "last_payments":last_payments,
            "yearly_data":yearly_data,
        }

        
        return Response(response_data)


