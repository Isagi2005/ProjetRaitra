# Imports mis à jour
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import PrivateChat, ChatGroup, Message, Notification

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_type = self.scope['url_route']['kwargs'].get('conversation_type', 'private')
        self.room_group_name = f'chat_{self.conversation_type}_{self.conversation_id}'

        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return
        has_access = await self.user_has_access(user, self.conversation_id, self.conversation_type)
        if not has_access:
            await self.close()
            return
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    # Autres méthodes (disconnect, receive, chat_message) restent similaires
    
    @database_sync_to_async
    def user_has_access(self, user, conversation_id, conversation_type):
        try:
            if conversation_type == 'private':
                chat = PrivateChat.objects.filter(
                    Q(participant1=user) | Q(participant2=user),
                    id=conversation_id,
                    is_active=True
                ).first()
                return chat is not None
            else:
                group = ChatGroup.objects.filter(
                    id=conversation_id,
                    members=user,
                    is_active=True
                ).first()
                return group is not None
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, user, content):
        msg = Message(sender=user)
        if self.conversation_type == 'private':
            msg.private_chat_id = self.conversation_id
        else:
            msg.group_chat_id = self.conversation_id
        msg.content = content  # crypté automatiquement
        msg.save()
        return {
            'content': msg.content,
            'sender': user.username,
            'timestamp': msg.timestamp.isoformat(),
            'id': msg.id
        }