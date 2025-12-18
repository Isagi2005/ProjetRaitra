from rest_framework import routers
from ..views import UserViewSet, ProfileViewSet, ConversationViewSet, MessageViewSet, NotificationViewSet

router = routers.DefaultRouter()
router.register(r'role', UserViewSet, basename='users')
router.register(r'profile', ProfileViewSet, basename='userprofile')
router.register(r'chats', ConversationViewSet, basename='conversations')
router.register(r'messages', MessageViewSet, basename='messages')
router.register(r'notifications', NotificationViewSet, basename='notification')