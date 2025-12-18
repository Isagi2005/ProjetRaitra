from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from rest_framework.permissions import AllowAny,IsAuthenticated
from django.contrib.auth.models import User
from .models import *
from .api.serializers import *
from django.contrib.auth import logout as django_logout
from rest_framework.decorators import action
from django.db.models import Q
from django.contrib.auth.models import User

@api_view(['POST'])
def create_superuser(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    if User.objects.filter(username=username).exists():
        return Response({'error': 'User already exists'}, status=400)
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    return Response({'success': True, 'user_id': user.id})

class ProfileViewSet(ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        if query_params:
            param_name, param_value = list(query_params.items())[0]  # Récupère le premier paramètre et sa valeur
            
            # Essayer de filtrer avec User directement
            try:
                filtered_queryset = User.objects.filter(**{param_name: param_value})
                if not filtered_queryset.exists():  # Si aucun résultat, essayer userprofile__
                    filtered_queryset = User.objects.filter(**{f"userprofile__{param_name}": param_value})
            except Exception as e:
                filtered_queryset = User.objects.filter(**{f"userprofile__{param_name}": param_value})

            serializer = self.get_serializer(filtered_queryset, many=True)
            return Response(serializer.data)

        return super().list(request, *args, **kwargs)



class UserRetrieve(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        user = request.user  
        serializer = self.get_serializer(user)
        return Response(serializer.data)

        
class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = LoginSerializer(data=request.data)
           
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.validated_data["user"]

            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # 🔹 Créer la réponse et ajouter les cookies
            res = Response({
                'success': True,
            })
        
            res.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite='None',
                path='/'
            )
            res.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite='None',
                path='/'
            )
            
            return res
        except status.HTTP_400_BAD_REQUEST:
            return Response(status.HTTP_400_BAD_REQUEST, status=status.HTTP_400_BAD_REQUEST)


class CustomRefreshTokenView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token=request.COOKIES.get('refresh_token')
            request.data['refresh']=refresh_token
            response=super().post(request,*args,**kwargs)

            tokens=response.data
            access_token=tokens['access']
            res=Response()

            res.data={'refreshed':True}
            res.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite='None',
                path='/'
               
            )
            
            return res
        except:
            return Response({'refreshed':False})
        
@api_view(['POST'])
def logout(request):
    try:
        django_logout(request)  # Utiliser la vraie fonction logout de Django

        res = Response({'success': True})
        res.delete_cookie("access_token", path='/', samesite='None')
        res.delete_cookie("refresh_token", path='/', samesite='None')
        res.delete_cookie("csrftoken", path='/')  # Supprime le CSRF token si utilisé
        res.delete_cookie("sessionid", path='/')  # Supprime la session si Django utilise les sessions

        return res
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def is_authenticated(request):
    return Response({'authenticated': True})

class ConversationViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='leave_group')
    def leave_group(self, request, pk=None):
        from rest_framework import status
        from rest_framework.response import Response
        user = request.user
        try:
            group = ChatGroup.objects.get(pk=pk)
            group.members.remove(user)
            if group.members.count() == 0:
                group.delete()
                return Response({'success': True, 'deleted': True}, status=status.HTTP_200_OK)
            return Response({'success': True, 'deleted': False}, status=status.HTTP_200_OK)
        except ChatGroup.DoesNotExist:
            return Response({'success': False, 'error': 'Groupe introuvable'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        user = request.user
        # Récupérer toutes les conversations privées et groupes où l'utilisateur est membre
        private_chats = PrivateChat.objects.filter(
            (Q(participant1=user) | Q(participant2=user)) & Q(is_active=True)
        )
        group_chats = ChatGroup.objects.filter(members=user, is_active=True)

        # Sérialiser les conversations privées
        private_data = PrivateChatSerializer(private_chats, many=True, context={'request': request}).data
        for conv in private_data:
            conv['type'] = 'private'
        # Sérialiser les groupes
        group_data = ChatGroupSerializer(group_chats, many=True, context={'request': request}).data
        for conv in group_data:
            conv['type'] = 'group'
        # Fusionner
        all_convs = private_data + group_data
        return Response(all_convs)

    def create(self, request):
        from django.db import transaction
        from rest_framework.response import Response
        from rest_framework import status
        user = request.user
        data = request.data
        participant_ids = data.get('participantIds') or data.get('participant_ids')
        name = data.get('name', '').strip()
        try:
            if not participant_ids or not isinstance(participant_ids, list):
                return Response({'error': 'participantIds requis (array d\'ids)'}, status=status.HTTP_400_BAD_REQUEST)
            # Ajoute toujours l'utilisateur courant si absent
            if user.id not in participant_ids:
                participant_ids.append(user.id)
            participants = User.objects.filter(id__in=participant_ids)
            if participants.count() != len(set(participant_ids)):
                return Response({'error': 'Certains utilisateurs sont invalides'}, status=status.HTTP_400_BAD_REQUEST)
            if len(participant_ids) == 2:
                # Conversation privée
                u1, u2 = sorted(participant_ids)  # ordre stable
                private = PrivateChat.objects.filter(
                    (Q(participant1_id=u1) & Q(participant2_id=u2)) |
                    (Q(participant1_id=u2) & Q(participant2_id=u1))
                ).first()
                if private:
                    serializer = PrivateChatSerializer(private, context={'request': request})
                    data = serializer.data
                    data['type'] = 'private'
                    return Response(data, status=status.HTTP_200_OK)
                # Sinon, crée la conversation
                with transaction.atomic():
                    private = PrivateChat.objects.create(participant1_id=u1, participant2_id=u2)
                serializer = PrivateChatSerializer(private, context={'request': request})
                data = serializer.data
                data['type'] = 'private'
                return Response(data, status=status.HTTP_201_CREATED)
            elif len(participant_ids) > 2:
                # Groupe
                if not name:
                    return Response({'error': 'Le nom du groupe est requis'}, status=status.HTTP_400_BAD_REQUEST)
                # Vérifier si un groupe identique existe déjà (optionnel)
                group = ChatGroup.objects.filter(name=name, is_active=True, members__in=participant_ids).distinct().first()
                if group:
                    serializer = ChatGroupSerializer(group, context={'request': request})
                    data = serializer.data
                    data['type'] = 'group'
                    return Response(data, status=status.HTTP_200_OK)
                with transaction.atomic():
                    group = ChatGroup.objects.create(name=name, created_by=user)
                    group.members.set(participants)
                serializer = ChatGroupSerializer(group, context={'request': request})
                data = serializer.data
                data['type'] = 'group'
                return Response(data, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': 'Au moins 2 participants requis'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MessageViewSet(ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        conversation_type = self.request.query_params.get('conversation_type', 'private')
        conversation_id = self.request.query_params.get('conversation_id')
        
        # Si on n'a pas d'ID de conversation, on retourne les messages de l'utilisateur
        if not conversation_id:
            return Message.objects.filter(sender=user).order_by('-timestamp')
        
        # Filtrer selon le type de conversation
        if conversation_type == 'private':
            # Vérifier que l'utilisateur a accès à cette conversation privée
            private_chat = PrivateChat.objects.filter(
                Q(id=conversation_id),
                Q(participant1=user) | Q(participant2=user)
            ).first()
            if not private_chat:
                return Message.objects.none()
            return Message.objects.filter(private_chat=private_chat).order_by('timestamp')
        else:
            # Vérifier que l'utilisateur a accès à ce groupe
            group = ChatGroup.objects.filter(
                id=conversation_id,
                is_active=True,
                members=user
            ).first()
            if not group:
                return Message.objects.none()
            return Message.objects.filter(group_chat=group).order_by('timestamp')

    def perform_create(self, serializer):
        # L'utilisateur connecté est toujours l'envoyeur
        serializer.save(sender=self.request.user)

class NotificationViewSet(ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # L'utilisateur ne voit que ses propres notifications
        return Notification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # On force la notification à être créée pour l'utilisateur courant
        serializer.save(user=self.request.user)
