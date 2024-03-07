import datetime
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from Admin_panel.permissions import IsAdminUserOrStaff, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken


from .serializers import CustomUser, Category, CategorySerializer, Product, ProductSerializer, PaymentMethod, PaymentMethodSerializer, Order, OrderSerializer, PaymentHistory, PaymentHistorySerializer


class PrdCategoryViewset(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsAdminUser,)


class PrdViewset(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (IsAdminUser,)


class PaymentMethodViewset(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = (IsAdminUser,)


class OrderViewset(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (IsAdminUserOrStaff,)

    def create(self, request, *args, **kwargs):
        
        is_related = False
        if not request.user.is_superuser:
            if request.user.is_staff:
                data = request.data
                client_id = data.get("client")
                client = CustomUser.objects.filter(id=client_id).first()
                if not client is None:
                    is_related = client.related_staff==request.user
        else:
            is_related = True
        
        if not is_related:
            return Response({"err":"you don't have permissions"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        is_related = False
        if not request.user.is_superuser:
            if request.user.is_staff:
                is_related = instance.client.related_staff==request.user
        else:
            is_related = True
        
        if not is_related:
            return Response({"err":"you don't have permissions"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    
    def list(self, request, *args, **kwargs):
        
        if not request.user.is_superuser:
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
    serializer_class = PaymentHistorySerializer
    permission_classes = (IsAdminUserOrStaff,)
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        request_data = request.data 
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment_amount = request_data.get('payment_amount')
        order = request_data.get('order')
        order = Order.objects.get(id=order)
        print(order.balance)
        order.balance = order.balance + float(payment_amount)
        print(order.balance)
        order.save()
        
        serializer.save()
        
        return Response({'msg':'post'})
        

class FullDataView(viewsets.GenericViewSet):
    # queryset = Order.objects.all()


    permission_classes = (IsAdminUser,)
    http_method_names = ["get"]
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        
        users = CustomUser.objects.all()
        products = Product.objects.all()
        orders = Order.objects.all()
        payments = PaymentHistory.objects.all()
        clients = users.filter(is_client=True)
        staffs = users.filter(is_staff=True)
        
        current_time = datetime.datetime.today()
        # print('\n\n',current_time, '\n')
        
        top_courses_amount = params.get('top_courses')
        
        ordered_courses = [order.product for order in orders]
        sorted_ordered_courses = list(set(sorted(ordered_courses, key=lambda obj: ordered_courses.count(obj), reverse=True)))
        if top_courses_amount is None or not top_courses_amount.isnumeric():
            top_courses_amount = 10
            
        sorted_ordered_courses = sorted_ordered_courses[:int(top_courses_amount)]
        sorted_ordered_courses = [{"id":ordered_course.id, "name":ordered_course.name, 'price':ordered_course.price, 'amount':ordered_courses.count(ordered_course)} for ordered_course in sorted_ordered_courses]

        last_courses_amount = params.get('last_orders')
        last_courses = [OrderSerializer(order).data for order in orders.order_by('-time_create')]
        if last_courses_amount is None or not last_courses_amount.isnumeric():
            last_courses_amount = 10

        last_courses = last_courses[:int(last_courses_amount)]
            
        
        
        current_year_payments = [payment for payment in payments if payment.time_create.year == current_time.year]
        yearly_data = {}
        for order in current_year_payments:
            try:
                yearly_data.update({order.time_create.strftime('%B'):order.payment_amount+yearly_data[order.time_create.strftime('%B')]})
            except:
                yearly_data.update({order.time_create.strftime('%B'):order.payment_amount})
        
        # print("\n EXTRA Data -->", (current_time.date() - users[0].time_create.date()).days)
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
            "most_seller_courses":sorted_ordered_courses,
            "last_orders":last_courses,
            "yearly_data":yearly_data,
                
        }


        # print("\n staffs Data -->", staffs[1].__dict__)
        # print("\n clients Data -->", clients[1])
        # print("\n Product Data -->", products[0].__dict__)
        # print("\n order Data -->", orders[1].__dict__)
        
        
        return Response(response_data)