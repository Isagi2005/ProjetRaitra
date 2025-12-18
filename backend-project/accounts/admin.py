from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0  # Pas de formulaires vides supplémentaires

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    
    def save_model(self, request, obj, form, change):
        # Laisser Django gérer la sauvegarde normale
        super().save_model(request, obj, form, change)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(ChatGroup)
admin.site.register(Message)
admin.site.register(Notification)
admin.site.register(PrivateChat)
