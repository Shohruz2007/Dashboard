from django.db import models
from django.contrib.auth.models import AbstractUser

from django.utils.translation import gettext_lazy as _



class CustomUser(AbstractUser):
    username = models.CharField(max_length=150,
                                unique=True,
                                error_messages={
                                    "unique": _("A user with that username already exists."),
                                },) 
    image = models.ImageField(upload_to='Users', null=True, blank=True)  
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=13, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    is_staff = models.BooleanField(_("stuff status"), default=False)
    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_(
            "Designates that this user has all permissions without "
            "explicitly assigning them."
        ),
    )
    is_client = models.BooleanField(_("client status"), default=False)
    related_staff = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)


    time_create = models.DateTimeField(auto_now_add=True, null=True)  # time when user has created
    time_update = models.DateTimeField(auto_now=True)  # time when user has updated
    
    
    ordering = ('username',)


    USERNAME_FIELD = "username"

    class Meta:
        ordering = ['id']
        verbose_name = "Пользовател"
        verbose_name_plural = "Пользователи"
        # index_together = ["username", "email"]

    def __str__(self):
        return self.username



class Notification(models.Model):
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()



    def __str__(self):
        return self.username