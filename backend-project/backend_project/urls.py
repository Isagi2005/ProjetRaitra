"""
URL configuration for backend_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from main_app.app_api.routers import router as main_rooter
from accounts.api.routers import router as user_rooter

app_router = routers.DefaultRouter()
app_router.registry.extend(main_rooter.registry)

account_router = routers.DefaultRouter()
account_router.registry.extend(user_rooter.registry)

urlpatterns = [
    path('admin/', admin.site.urls),    
    path('', include('accounts.urls')),
    path('', include('main_app.urls')),
    path('api/', include(app_router.urls)),
    path('api/users/', include(account_router.urls)),

]
