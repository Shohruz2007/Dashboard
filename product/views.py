import datetime
import threading
from multiprocessing.dummy import Pool as ThreadPool
import time
from urllib.parse import unquote

from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db.models import Q

from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from Admin_panel.permissions import IsAdminUserOrStaff, IsAdminUser, IsAdminUserOrStaffReadOnly
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import PageNumberPagination


from .serializers import CustomUser, Category, CategorySerializer, Product, ProductSerializer, PaymentMethod, PaymentMethodSerializer, Order, OrderSerializer, OrderCreateSerializer, PaymentHistory, PaymentHistorySerializer, PaymentCreateHistorySerializer


class ListPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 30
    page_size_query_param = 'page_size'


class PrdCategoryViewset(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsAdminUser,)
    pagination_class = ListPagination


class PrdViewset(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (IsAdminUserOrStaffReadOnly,)
    pagination_class = ListPagination
    
    
    def list(self, request, *args, **kwargs):
        params = dict(request.GET)
        search_data = params.get('search')
        if search_data is None:
            queryset = self.filter_queryset(self.get_queryset())
        else:
            search_data:str = unquote(search_data if not type(search_data) is list else search_data[0])
            search_data = search_data.split()
            print("search_data -->", search_data)
            queryset_collector = []
            for item in search_data:
                queryset = Product.objects.filter(Q(id__icontains=item) | Q(name__icontains=item) | Q(author__icontains=item))
                queryset_collector.extend(queryset)
            
            queryset = []
            for query_obj in queryset_collector:
                if not query_obj in queryset:
                    queryset.append(query_obj)

        print(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    
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
    



class PaymentMethodViewset(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = (IsAdminUserOrStaffReadOnly,)


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        
        params = dict(request.GET)
        search_data = params.get('search')
        
        if not search_data is None:
            search_data:str = unquote(search_data if not type(search_data) is list else search_data[0])
            search_data = search_data.split()
            print("search_data -->", search_data)
            queryset_collector = []
            for item in search_data:
                queryset = PaymentMethod.objects.filter(Q(id__icontains=item) | Q(name__icontains=item))
                queryset_collector.extend(queryset)
            queryset = []
            for query_obj in queryset_collector:
                if not query_obj in queryset:
                    queryset.append(query_obj)
        else:
            queryset = PaymentMethod.objects.select_related()
        


        
        
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
    pagination_class = ListPagination

    
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
        
        data['creator'] = request.user.id
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
    
        params = dict(request.GET)
        is_active = params.get('is_active')
        print('IS ACTIVE -->', is_active)
        
        if type(is_active) is list:
            is_active = is_active[0]
            
        if type(is_active) is str and is_active.lower() == 'false':
            is_active = False
        else:
            is_active = True 

        staff_queryset = False
        if not request.user.is_superuser and request.user.is_staff:
            # queryset = [order for order in queryset if not order.client.related_staff is None and order.client.related_staff.id == request.user.id]
            staff_queryset = True
            
        print('IS ACTIVE -->', is_active)
        search_data = params.get('search')

        if not search_data is None:
            search_data:str = unquote(search_data if not type(search_data) is list else search_data[0])
            search_data = search_data.split()
            print("search_data -->", search_data)
            queryset_collector = []
            for item in search_data:
                if staff_queryset:
                    queryset = Order.objects.select_related('client', 'product').filter(Q(id__icontains=item) | Q(client__username__icontains=item) | Q(client__first_name__icontains=item) | Q(product__name__icontains=item)).filter(is_active=is_active).filter(creator=request.user.id)
                else:
                    queryset = Order.objects.select_related('client', 'product').filter(Q(id__icontains=item) | Q(client__username__icontains=item) | Q(client__first_name__icontains=item) | Q(product__name__icontains=item)).filter(is_active=is_active)
                queryset_collector.extend(queryset)

            queryset = []
            for query_obj in queryset_collector:
                if not query_obj in queryset:
                    queryset.append(query_obj)
        else:
            if staff_queryset:
                queryset = Order.objects.filter(is_active=is_active).select_related('client', 'product').filter(creator=request.user.id)
            else:
                queryset = Order.objects.filter(is_active=is_active).select_related('client', 'product')





        
        
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
    # pagination_class = ListPagination   


    def post(self, request, *args, **kwargs):
        # print(request.META.get('HTTP_AUTHORIZATION'))
        params = dict(request.GET)
        try:
            data = {'order':int(params.get('order')[0]),'payment_amount':float(str(params.get('amount')[0]).replace(' ',''))}
            print(data)
        except Exception as err:
            print('ERR IN PARAMS -->', err)
            return Response({'err': "data is wrong"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            

        serializer = PaymentCreateHistorySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        # print('ORDER INSIDE PAYMENT -->', serializer.data)
        
        payment_amount = data.get('payment_amount')
        order = data.get('order')
        order = Order.objects.filter(id=order).first()
        if order is None:
            return Response({'err': "order data is wrong"}, status=status.HTTP_406_NOT_ACCEPTABLE)
            
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
        
        # print(serializer.data)

        serializer.save()
        ord_serializer = OrderSerializer(order)
        return Response(ord_serializer.data | {"payment_data":serializer.data})
    


    def list(self, request, *args, **kwargs):
        
        if not request.user.is_superuser and not request.user.is_analizer:
            return Response({'err':"You don't have permissions to do it"}, status=status.HTTP_406_NOT_ACCEPTABLE)
        else:
            queryset = PaymentHistory.objects.all()
            
        serializer = self.get_serializer(queryset, many=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)


        return Response(serializer.data)
        

class DashboardBaseDataView(viewsets.GenericViewSet):

    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        params = request.query_params
        is_superuser = request.user.is_superuser
        users = None
        orders = None
        payments = None
        
        if is_superuser:
            orders = Order.objects.all().select_related('product')
            payments = PaymentHistory.objects.all()
            users = CustomUser.objects.all()

        else:
            users = CustomUser.objects.filter(related_staff=request.user)

            print('All USERS -->', [[user.username, user.first_name, user.related_staff] for user in users])
            # print('STAFF USERS -->', users)
            

            orders = Order.objects.filter(creator=request.user.id).select_related('product')
                
                # user_pks = tuple([user.id for user in users])
                # orders = Order.objects.filter(user=user_pks).select_related('product')

            # print('All ORDERS -->', [[order, order.client.related_staff, order.creator] for order in orders])
                
            # print('STAFF Orders -->', orders)
            payments = []

            order_pks = tuple([order.id for order in orders])
            for pk in order_pks:
                payments.extend(PaymentHistory.objects.filter(order=pk))


            
            
            print('STAFF payments -->', payments)
            
            
        
        
        # users = CustomUser.objects.filter(related_staff=request.user.id)
        # orders = Order.objects.all().select_related('product')
        # payments = PaymentHistory.objects.all()
        
        products = Product.objects.all()
        
        current_time = datetime.datetime.today()
        
        clients = users.filter(is_client=True)
        current_year_orders = [order for order in orders if order.time_create.year == current_time.year]
        
            
        #TODO: months best sells  ============
        # months = [0, 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr']
        
        # yearly_data = []
        # for month_number in range(1,13):
        #     products_data = []
        #     for order in current_year_orders:
        #         # print('current_time --> ', current_time.month)
        #         if order.time_create.month == month_number:
        #             products_data.append(order.product)
            
        #     def find_most_repeated_object(collection):
        #         counts = {}
        #         most_repeated_obj = None
        #         max_count = 0

        #         # Count the occurrences of each object in the collection
        #         for obj in collection:
        #             if obj in counts:
        #                 counts[obj] += 1
        #             else:
        #                 counts[obj] = 1

        #             # Update the most repeated object if necessary
        #             if counts[obj] > max_count:
        #                 max_count = counts[obj]
        #                 most_repeated_obj = obj

        #         return most_repeated_obj, max_count
            
            
        #     most_saled_product,sales_amount = find_most_repeated_object(products_data)
        #     yearly_data.append({
        #         'Oy': months[month_number],
        #         'Mahsulot':most_saled_product.name if not most_saled_product is None else None, 
        #         'Sotuvlar soni': sales_amount,
        #     })
        # ============
        
        yearly_data = []
        
        ordered_produts = [order.product for order in current_year_orders]

            
            

        
        for prd in products:
            yearly_data.append({'Mahsulot':prd.name, 'Sotuvlar soni':ordered_produts.count(prd)})
        
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

    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["get"]

    # @method_decorator(cache_page(60))
    def get(self, request, *args, **kwargs):
        params = request.query_params
        # start_time = time.time()
        is_superuser = request.user.is_superuser

        
        if is_superuser:
            payments = PaymentHistory.objects.all().select_related('order')
            # last_payments = all_payments[:10]
        else:
            # users = CustomUser.objects.filter(related_staff=request.user.id)
            # print('STAFF USERS -->', users)
            
            # user_pks = tuple([user.id for user in users])
            orders = Order.objects.filter(creator=request.user.id)
            # print('STAFF Orders -->', orders)
            order_pks = tuple([order.id for order in orders])
            print('STAFF Orders -->', order_pks)
            # payments = PaymentHistory.objects.all().select_related('order').order_by('-time_create')
            # all_payments = PaymentHistory.objects.filter(order=pk)
            
            payments = []
            for pk in order_pks:
                order_payments = PaymentHistory.objects.filter(order=pk).select_related('order',).order_by('-time_create')
                
                if not order_payments == []:
                    payments.extend(order_payments)
            
            # payments = []
            # for payment in all_payments[0:2]:
            payments = sorted(payments, key=lambda x: x.time_create, reverse=True)
            # print(payments[0].time_create>payments[11].time_create)
            print('STAFF payments -->', payments)

        
        last_payments_amount = params.get('last_pays')
        if last_payments_amount is None or not last_payments_amount.isnumeric():
            last_payments_amount = 5
        
        last_payments = payments[:10]
        
        current_time = datetime.datetime.today()
        # print('\n\n',current_time, '\n')
        
        
            

        last_payments = [{'payment_amount':payment.payment_amount, 'client':(payment.order.client.first_name if not payment.order is None else None), 'product':(payment.order.product.name if not payment.order is None else None), 'time_create':payment.time_create} for payment in last_payments]

            
        
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
                'Sotuvlar summasi': month_sales
            })
            
        response_data = {
            "last_payments":last_payments,
            "yearly_data":yearly_data,
        }

        
        return Response(response_data)


