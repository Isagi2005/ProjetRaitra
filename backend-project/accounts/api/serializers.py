from django.contrib.auth.models import User
from ..models import UserProfile
from rest_framework import serializers
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import check_password
from accounts.models import Notification, ChatGroup, PrivateChat, Message

class UserProfileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = UserProfile
        fields = ["id", "account", 'image', 'historique', 'sexe', 'telephone', 'birthDate', 'adresse', 'religion', 'role']
        
    

    def create(self, validated_data):
        account = validated_data.get('account')
        if(account):
            profile = UserProfile.objects.create(**validated_data)    
            

        return profile

    def update(self, instance, validated_data):
        if 'role' in validated_data and instance.role != validated_data['role']:
            # Générer le nouveau username basé sur le nouveau rôle
            role = validated_data['role']
            prefix_map = {
                UserProfile.DIRECTION: 'RKDir',
                UserProfile.PARENT: 'RKPar',
                UserProfile.ENSEIGNANT: 'RKEn',
                UserProfile.FINANCE: 'RKFi'
            }
            prefix = prefix_map.get(role, 'RKUser')
            
            # Trouver le dernier numéro existant pour ce préfixe
            last_user = User.objects.filter(
                username__startswith=prefix
            ).order_by('username').last()
            
            last_num = int(last_user.username[len(prefix):]) if last_user else 0
            new_username = f"{prefix}{last_num + 1}"
            
            user = instance.account
            user.username = new_username
            user.save()
            validated_data['role'] = role
        
        return super().update(instance, validated_data)

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(source='userprofile', required=False)
    dateArrivee = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "first_name", "last_name", "date_joined",
            "dateArrivee", "password", "is_active", "status", "email", "profile"
        ]
        extra_kwargs = {
            'date_joined': {'read_only': True}
        }

    def get_dateArrivee(self, obj):
        return obj.date_joined.strftime('%d %B %Y')

    def get_status(self, obj):
        return "active" if obj.is_active else "inactive"    


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")
        role = data.get("role")
        role = role.strip().lower()
        
        user = User.objects.filter(username=username).first()
        if not user:
            raise AuthenticationFailed("L'utilisateur n'existe pas")

        if not check_password(password, user.password):
            raise AuthenticationFailed("Mot de passe incorrect")

        user_profile = UserProfile.objects.filter(
            account=user,
            role=role
        ).first()
        
        if not user_profile:
            raise AuthenticationFailed("Rôle incorrect")

        if not user.is_active:
            raise AuthenticationFailed("Non autorisé")

        return {
            'user': user,
            'role': user_profile.role
        }


class ChatGroupSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    class Meta:
        model = ChatGroup
        fields = ['id', 'last_message','name', 'created_by', 'created_at', 'members', 'is_active']
    
    def get_last_message(self, obj):
        last_message = Message.objects.filter(group_chat=obj).order_by('-timestamp').first()
        return MessageSerializer(last_message).data if last_message else None
        
class PrivateChatSerializer(serializers.ModelSerializer):
    participant1 = UserSerializer(read_only=True)
    participant2 = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = PrivateChat
        fields = ['id', 'last_message','participant1', 'participant2', 'created_at', 'is_active', 'members']

    def get_members(self, obj):
        return [UserSerializer(obj.participant1).data, UserSerializer(obj.participant2).data]
    def get_last_message(self, obj):
        last_message = Message.objects.filter(private_chat=obj).order_by('-timestamp').first()
        return MessageSerializer(last_message).data if last_message else None
class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    conversation_id = serializers.SerializerMethodField()
    conversation_type = serializers.SerializerMethodField()
    content = serializers.CharField(required=False)
    
    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation_id',
            'conversation_type',
            'sender', 
            'content',
            'file',
            'image', 
            'timestamp', 
            'is_read'
        ]
        read_only_fields = ['sender', 'timestamp']
    
    def get_conversation_id(self, obj):
        return obj.conversation_id
    
    def get_conversation_type(self, obj):
        return obj.conversation_type
    
    def create(self, validated_data):
        # Récupérer l'utilisateur courant et le type de conversation
        request = self.context.get('request')
        user = request.user if request else None
        
        # Récupérer les données de conversation
        conversation_type = request.data.get('conversation_type', 'private')
        conversation_id = request.data.get('conversation_id')
        
        # Créer un nouveau message avec le bon lien
        message = Message()
        message.sender = user
        
        if conversation_type == 'private':
            message.private_chat_id = conversation_id
        else:
            message.group_chat_id = conversation_id
        
        # Gestion du contenu et autres champs
        if 'content' in validated_data:
            message.content = validated_data['content']
        if 'file' in validated_data:
            message.file = validated_data['file']
        if 'image' in validated_data:
            message.image = validated_data['image']
        
        message.save()
        return message
        
class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notif_type', 'title', 'message', 'link', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']