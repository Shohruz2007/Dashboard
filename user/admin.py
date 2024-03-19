from django.contrib import admin
from .models import CustomUser, Notification

class UserModelAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)
    list_display_links = ('username','email')
    list_display = ('id','username','email','is_staff','is_client')
    list_filter = ('id',)

admin.site.register(CustomUser, UserModelAdmin)
admin.site.register(Notification)
