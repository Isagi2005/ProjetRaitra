from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation

def get_aes_key():
    key = getattr(settings, 'AES_KEY', None)
    if not key:
        raise Exception('AES_KEY is not set in Django settings!')
    if isinstance(key, str):
        key = key.encode()
    if len(key) not in (16, 24, 32):
        raise ValueError(f"AES_KEY must be 16, 24, or 32 bytes long, got {len(key)} bytes.")
    return key

def aes_encrypt(message: str, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(message.encode())
    return base64.b64encode(cipher.nonce + tag + ciphertext)

def aes_decrypt(token: bytes, key: bytes) -> str:
    data = base64.b64decode(token)
    nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode()

class UserProfile(models.Model):
    DIRECTION = 'direction'
    FINANCE = 'finance'
    PARENT = 'parent'
    ENSEIGNANT = 'enseignant'

    MASCULIN = "H"
    FEMININ = "F"

    SEXE = [
        (MASCULIN, 'Masculin'),
        (FEMININ, 'Féminin')
    ]

    ROLE_CHOICES = [
        (DIRECTION, 'Direction'),
        (FINANCE, 'Finance'),
        (PARENT, 'Parent'),
        (ENSEIGNANT, 'Enseignant')
    ]

    account = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    sexe = models.CharField(max_length=1, blank=True, null=True, choices=SEXE, default=FEMININ)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    image = models.ImageField(blank=True, null=True, upload_to="images/utilisateur/")
    historique = models.ImageField(blank=True, null=True, upload_to="images/historique/")
    birthDate = models.DateField(blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    religion = models.CharField(max_length=30, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=DIRECTION)

    def __str__(self):
        return f"{self.account.first_name} - {self.get_role_display()}"

    def generate_username(self):
        prefix_map = {
            self.DIRECTION: 'RKDir',
            self.PARENT: 'RKPar',
            self.ENSEIGNANT: 'RKEn',
            self.FINANCE: 'RKFi'
        }
        prefix = prefix_map.get(self.role, 'RKUser')
        
        # Trouve le numéro le plus élevé existant
        last_user = User.objects.filter(
            username__startswith=prefix
        ).order_by('username').last()
        
        last_num = int(last_user.username[len(prefix):]) if last_user else 0
        return f"{prefix}{last_num + 1}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Seulement à la création
            if not self.account_id:
                username = self.generate_username()
                user = User(username=username)
                user.save()
                
            elif self.account.username == "temp":
                # Met à jour le username temporaire
                self.account.username = self.generate_username()
                self.account.save()
                
        
        super().save(*args, **kwargs)

class Conversation(models.Model):
    """Base abstraite pour les conversations (groupes ou privées)"""
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True

class PrivateChat(Conversation):
    participant1 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='private_chats1'
    )
    participant2 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='private_chats2'
    )
    
    class Meta:
        unique_together = ('participant1', 'participant2')
    
    def __str__(self):
        return f"Chat privé {self.participant1} - {self.participant2}"

class ChatGroup(Conversation):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_groups'
    )
    members = models.ManyToManyField(
        User, 
        related_name='group_chats'
    )

    def __str__(self):
        return f"{self.name} (Groupe)"

class Message(models.Model):
    # Relations directes sans GenericForeignKey
    private_chat = models.ForeignKey(
        PrivateChat, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True, 
        blank=True
    )
    group_chat = models.ForeignKey(
        ChatGroup, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True, 
        blank=True
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    # Le contenu est stocké crypté
    encrypted_content = models.BinaryField(blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    @property
    def content(self):
        if self.encrypted_content:
            try:
                return aes_decrypt(self.encrypted_content, get_aes_key())
            except Exception:
                return ''
        return ''

    @content.setter
    def content(self, value):
        if value:
            self.encrypted_content = aes_encrypt(value, get_aes_key())
        else:
            self.encrypted_content = b''
    
    @property
    def conversation_id(self):
        """Retourne l'ID de la conversation, quel que soit son type"""
        return self.private_chat_id or self.group_chat_id
    
    @property
    def conversation_type(self):
        """Retourne le type de conversation (private ou group)"""
        return 'private' if self.private_chat_id else 'group'

    def __str__(self):
        conv = self.private_chat or self.group_chat
        return f"Message de {self.sender} dans {conv} à {self.timestamp}"

class Notification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ("message", "Message"),
        ("bulletin", "Bulletin"),
        ("presence", "Présence"),
        ("groupe", "Groupe de chat"),
        ("info", "Information"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPE_CHOICES)
    title = models.CharField(max_length=120)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)  # Lien vers l'élément concerné (ex: /bulletin/12)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notif({self.notif_type}) to {self.user.username}: {self.title}"