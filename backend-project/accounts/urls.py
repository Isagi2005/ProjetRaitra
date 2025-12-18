from django.urls import path
from .views import *

urlpatterns = [
    path("api/user/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("api/user/logout/", logout, name="logout"),
    path("api/user/authentified/", UserRetrieve.as_view(), name="authentified"),
    path("api/user/authenticated/", is_authenticated, name="authenticated"),
    path("api/token/refresh/", CustomRefreshTokenView.as_view(), name="token_refresh"),
    
]
# urlpatterns = format_suffix_patterns(urlpatterns)
