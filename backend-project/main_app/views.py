from accounts.models import UserProfile
from .models import (
     Etudiant,Service,RapportPaiement,Conge,Recrutement, AnneeScolaire,Depense, Paiement,Employee,CotisationSociale,Paie,AssuranceEleve,Notification
    )
from .permissions import  IsFinanceUser, IsDirectionOrFinanceUser,IsDirectionUser,IsEnseignantUser,IsParentUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
# from .models import Rec
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .app_api.serializers import (
    RecrutementSerializer,ServiceSerializer,CertificatTexteSerializer, ExportCertificatSerializer,CongeSerializer,RapportPaiementSerializer, AnneeScolaireSerializer,ClasseSerializer, DepenseSerializer,PaiementSerializer,EtudiantSerializer,EmployeSerializer,CotisationSocialeSerializer,AssuranceEleveSerializer,PaieSerializer
    ) 
from fuzzywuzzy import process
# from services.paiement_service import is_mois_paye
from rest_framework.decorators import action
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
import json
from rest_framework.decorators import api_view
from django.conf import settings
from main_app.encoders import DecimalJSONEncoder
from django.core.exceptions import PermissionDenied
from twilio.rest import Client
import traceback
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from accounts.models import  UserProfile
import re
from django.utils import timezone
from twilio.base.exceptions import TwilioRestException
import logging
import socket
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
from twilio.http.http_client import HttpClient
import uuid
from .utils import envoyer_email_notification
import google.generativeai as genai
from main_app.utils import generer_texte_certificat
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from docx import Document
from .utils import creer_document_certificat
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics

# Create your views here
# Antso

class DepenseViewSet(viewsets.ModelViewSet):
    queryset = Depense.objects.all()
    serializer_class = DepenseSerializer
    permission_classes= [IsFinanceUser]

    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
        

class PaiementViewSet(viewsets.ModelViewSet):
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer

    def get_permissions(self):
        if self.action in ['paiements_enfant', 'statut_paiements']:
            permission_classes = [IsParentUser]
        else:
            permission_classes = [IsDirectionOrFinanceUser]
        return [permission() for permission in permission_classes]

    def get_object(self):
        obj = Paiement.objects.filter(pk=self.kwargs["pk"]).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound("Paiement non trouvé.")
        return obj

    def perform_create(self, serializer):
        result = serializer.save()
        if isinstance(result, list):  # Création multiple
            print(f"{len(result)} paiements créés")
        else:
            print("Paiement créé :", result.id)

    def perform_update(self, serializer):
        paiement = self.get_object()
        if not self.has_permission_to_edit(self.request, paiement):
            raise PermissionDenied("Vous n’avez pas l’autorisation de modifier ce paiement.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.has_permission_to_edit(self.request, instance):
            raise PermissionDenied("Vous n’avez pas l’autorisation de supprimer ce paiement.")
        instance.delete()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def has_permission_to_edit(self, request, paiement: Paiement):
        user = request.user
        role = getattr(user.userprofile, 'role', None)
        print(f"User: {user.username}, Role: {role}, Paiement verrouillé: {paiement.verrouille}")
        return (
            role == "direction" or
            (role == "finance" and not paiement.verrouille)
        )

    @action(detail=False, methods=['get'])
    def historique(self, request):
        classe_id = request.query_params.get("classe_id")
        annee_scolaire = request.query_params.get("annee_scolaire")
        mois = request.query_params.get("mois")

        if not classe_id or not annee_scolaire or not mois:
            return Response({"error": "classe_id, annee_scolaire et mois sont requis."}, status=400)

        try:
            annee_obj = AnneeScolaire.objects.get(anneeScolaire=annee_scolaire)
        except AnneeScolaire.DoesNotExist:
            return Response({"error": "Année scolaire introuvable."}, status=404)

        etudiants = Etudiant.objects.filter(
            classe_id=classe_id,
            classe__anneeScolaire=annee_obj.id
        )

        response_data = []
        for etudiant in etudiants:
            paiement_existe = Paiement.objects.filter(
                etudiant=etudiant,
                mois=mois,
                categorie='Ecolage'
            ).exists()

            response_data.append({
                "etudiant_id": etudiant.id,
                "nom": etudiant.nom,
                "prenom": etudiant.prenom,
                "classe": etudiant.classe.nom,
                "status": "Payé" if paiement_existe else "Non payé"
            })

        return Response(response_data)

    @action(detail=False, methods=['post'], url_path='envoyer-rapport')
    def envoyer_rapport(self, request):
        classe_id = request.data.get("classe_id")
        annee_scolaire = request.data.get("annee_scolaire")
        mois = request.data.get("mois")

        if not classe_id or not annee_scolaire or not mois:
            return Response(
                {"error": "classe_id, annee_scolaire et mois sont requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            annee_obj = AnneeScolaire.objects.get(anneeScolaire=annee_scolaire)
        except AnneeScolaire.DoesNotExist:
            return Response({"error": "Année scolaire introuvable."}, status=status.HTTP_404_NOT_FOUND)

        etudiants = Etudiant.objects.filter(classe_id=classe_id, classe__anneeScolaire=annee_obj.id)

        rapport_data = []

        for etudiant in etudiants:
            paiements = Paiement.objects.filter(
                etudiant=etudiant,
                mois=mois,
                categorie='Ecolage'
            )
            paiements.update(verrouille=True)

            paiement_details = [
                {
                    "id": paiement.id,
                    "mois": paiement.mois,
                    "montant": float(paiement.montant),
                    "modePaiement": paiement.modePaiement,
                    "categorie": paiement.categorie,
                    "description": paiement.description,
                    "datePaiement": paiement.datePaiement.strftime('%Y-%m-%d'),
                    "effectuePar": paiement.effectuePar.username if paiement.effectuePar else None
                }
                for paiement in paiements
            ]

            rapport_data.append({
                "etudiant_id": etudiant.id,
                "nom": etudiant.nom,
                "prenom": etudiant.prenom,
                "classe": etudiant.classe.nom,
                "statut": "Payé" if paiements.exists() else "Non payé",
                "paiements": paiement_details
            })

        rapport = RapportPaiement.objects.create(
            classe_id=classe_id,
            annee_scolaire=annee_obj,
            mois=mois,
            contenu=json.loads(json.dumps(rapport_data, cls=DecimalJSONEncoder)),
            envoyeur=request.user
        )

        return Response({
            "message": "Rapport généré et enregistré avec succès.",
            "rapport_id": rapport.id
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def paiements_enfant(self, request):
        user = request.user
        enfants = Etudiant.objects.filter(parent=user)

        if not enfants.exists():
            return Response({"detail": "Aucun enfant trouvé pour ce parent"}, status=404)

        mois = request.query_params.get('mois')
        annee = request.query_params.get('annee')

        queryset = Paiement.objects.filter(
            etudiant__in=enfants,
            categorie='Ecolage'
        )

        if mois:
            queryset = queryset.filter(mois=mois)
        if annee:
            queryset = queryset.filter(datePaiement__year=annee)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsParentUser])
    def statut_paiements(self, request):
        """
        Retourne le statut de paiement par mois pour tous les enfants du parent,
        avec possibilité de filtrer par année scolaire
        """
        user = request.user
        enfants = Etudiant.objects.filter(parent=user)

        if not enfants.exists():
            return Response({"detail": "Aucun enfant trouvé pour ce parent"}, status=404)

        annee_param = request.query_params.get("annee_scolaire") 
        if annee_param:
            try:
                annee_obj = AnneeScolaire.objects.get(anneeScolaire=annee_param)
            except AnneeScolaire.DoesNotExist:
                return Response({"error": "Année scolaire introuvable."}, status=404)
            enfants = enfants.filter(classe__anneeScolaire=annee_obj)

        mois_list = [m[0] for m in Paiement.MOIS]
        result = []

        for enfant in enfants:
            paiements = Paiement.objects.filter(
                etudiant=enfant,
                categorie='Ecolage'
            )

            statuts = {
                mois: paiements.filter(mois=mois).exists()
                for mois in mois_list
            }

            result.append({
                'enfant_id': enfant.id,
                'nom_complet': f"{enfant.nom} {enfant.prenom}",
                'classe': enfant.classe.nom,
                'annee_scolaire': enfant.classe.anneeScolaire.anneeScolaire,
                'statuts_paiement': statuts,
                'total_paye': sum(p.montant for p in paiements)
            })
        return Response(result)

class EmployeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeSerializer
    permission_classes= [IsDirectionOrFinanceUser]
    
    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
        
        
class PaieViewSet(viewsets.ModelViewSet):
    queryset = Paie.objects.all()
    serializer_class = PaieSerializer

    def create(self, request, *args, **kwargs):
        # Récupération des données envoyées
        data = request.data
        employe_id = data.get('employe_id')
        mois = data.get('mois')
        annee = data.get('annee')
        montant = data.get('montant')
        mode_paiement = data.get('mode_paiement')

        # Assurez-vous de la validité des données
        if not employe_id or not mois or not annee or not montant:
            return Response({"detail": "Données invalides."}, status=status.HTTP_400_BAD_REQUEST)

        # Création du paiement
        try:
            paie = Paie.objects.create(
                employe_id=employe_id,
                mois=mois,
                annee=annee,
                montant=montant,
                mode_paiement=mode_paiement
            )
            paie.save()
            return Response(PaieSerializer(paie).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
        
        
class CotisationSocialeViewSet(viewsets.ModelViewSet):
    queryset = CotisationSociale.objects.all()
    serializer_class = CotisationSocialeSerializer
    permission_classes= [IsFinanceUser]
    
    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
    
class AssuranceViewSet(viewsets.ModelViewSet):
    queryset = AssuranceEleve.objects.all()
    serializer_class = AssuranceEleveSerializer
    permission_classes= [IsFinanceUser]
    
    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
        

class RapportPaiementViewSet(viewsets.ModelViewSet):
    queryset = RapportPaiement.objects.all().order_by('-date_envoi')
    serializer_class = RapportPaiementSerializer
    permission_classes = [IsDirectionUser]

    def perform_create(self, serializer):
        serializer.save(envoyeur=self.request.user)
        
    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        rapport = self.get_object()
        return Response(rapport.contenu)
    
def envoyer_whatsapp_message(numero_from, numero_to, message_text):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=message_text,
        from_=numero_from,
        to=f'whatsapp:{numero_to}'
    )
    return message

logger = logging.getLogger(__name__)

class DevTwilioHttpClient:
    """Client HTTP optimisé pour le développement"""
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.trust_env = False

    def request(self, method, url, params=None, data=None, headers=None, auth=None, timeout=None, allow_redirects=False):
        timeout = timeout or self.timeout
        try:
            return self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
                allow_redirects=allow_redirects
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur HTTP: {str(e)}")
            raise

class NotificationViewSet(viewsets.ViewSet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.twilio_client = self._init_twilio_client()

    def _init_twilio_client(self):
        """Initialise le client Twilio avec fallback"""
        if getattr(settings, 'TWILIO_DEBUG', True):
            logger.info("Mode debug Twilio activé")
            return None
            
        try:
            return Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
                http_client=DevTwilioHttpClient(timeout=30)
            )
        except Exception as e:
            logger.error(f"Échec initialisation Twilio: {str(e)}")
            return None

    def _format_phone(self, numero):
        """Formate les numéros malgaches"""
        if not numero:
            return ""
            
        numero = re.sub(r'[^0-9]', '', numero)
        if numero.startswith('0'):
            return f'+261{numero[1:]}'
        elif numero.startswith('261'):
            return f'+{numero}'
        elif len(numero) == 9:
            return f'+261{numero}'
        return numero

    @action(detail=False, methods=['post'], url_path='impaye')
    def notifier_impaye(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else request.data[0] if isinstance(request.data, list) else {}
            eleve_id = data.get('eleve_id')
            if not eleve_id:
                return Response({"error": "ID élève requis"}, status=status.HTTP_400_BAD_REQUEST)

            eleve = Etudiant.objects.get(id=eleve_id)
            parent = eleve.parent
            profile = parent.userprofile

            tel_parent = self._format_phone(profile.telephone)
            tel_direction = self._format_phone(getattr(settings, 'ECOLE_CONTACT', ''))
            email_parent = parent.email

            message = (
                f"Bonjour {parent.first_name or ''},\n\n"
                f"Nous vous informons qu’un paiement de frais de scolarité est en attente concernant votre enfant : "
                f"{eleve.nom.upper()} {eleve.prenom}.\n\n"
                f" Merci de procéder à la régularisation dans les meilleurs délais.\n\n"
                f"École : {getattr(settings, 'ECOLE_NOM')}\n"
                f"Contact : {tel_direction}\n"
                f" Email : {email_parent or 'non disponible'}\n\n"
                f"Cordialement,\nLa Direction"
            )

            notifications = []

        # WHATSAPP
            if getattr(settings, 'TWILIO_DEBUG', True) or not self.twilio_client:
                notifications.append(self._create_notification(
                    eleve, tel_parent, tel_direction, message, 'simulé', 'whatsapp'
                ))
            else:
                try:
                    resp = self.twilio_client.messages.create(
                        body=message,
                        from_=settings.TWILIO_WHATSAPP_NUMBER,
                        to=f"whatsapp:{tel_parent}"
                    )
                    notifications.append(self._create_notification(
                        eleve, tel_parent, tel_direction, message, 'envoyé', 'whatsapp', twilio_sid=resp.sid
                    ))
                except TwilioRestException as e:
                    logger.error(f"Erreur Twilio WhatsApp: {e.code} - {e.msg}")
                    notifications.append(self._create_notification(
                        eleve, tel_parent, tel_direction, message, 'échec', 'whatsapp'
                    ))

        # EMAIL
            if email_parent:
                email_id = envoyer_email_notification(
                    email_to=email_parent,
                    subject="Notification de paiement en attente",
                    message=message
                )
                statut_email = 'envoyé' if email_id else 'échec'
                notifications.append(self._create_notification(
                    eleve, tel_parent, tel_direction, message, statut_email, 'email',
                    email_destinataire=email_parent,
                    email_id=str(email_id) if email_id else None
                ))

            return Response({
                "success": True,
                "notifications": [notif.id for notif in notifications]
            }, status=status.HTTP_200_OK)

        except Etudiant.DoesNotExist:
            return Response({"error": "Élève introuvable"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            return Response({"error": "Erreur interne", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_notification(self, eleve, tel_parent, tel_direction, message, statut,
                         type_notification='whatsapp', twilio_sid=None, email_destinataire=None, email_id=None):
        return Notification.objects.create(
            eleve=eleve,
            telephone_parent=tel_parent,
            telephone_direction=tel_direction,
            email_destinataire=email_destinataire,
            message=message,
            statut=statut,
            type_notification=type_notification,
            twilio_sid=twilio_sid,
            email_id=email_id,
            created_at=timezone.now()
        )

            
class PaiementRetrieveUpdateDestroyAPIView (generics.RetrieveUpdateDestroyAPIView):
    """
    Cette vue permet de :
    - Récupérer un paiement (GET)
    - Modifier un paiement (PATCH / PUT)
    - Supprimer un paiement (DELETE)
    """
    queryset = Paiement.objects.all()
    serializer_class = PaiementSerializer
    permission_classes = [IsDirectionOrFinanceUser]

    # (optionnel) Si tu veux filtrer et sécuriser mieux :
    def get_queryset(self):
        return Paiement.objects.all()
    
class CongeViewSet(viewsets.ModelViewSet):
    serializer_class = CongeSerializer
    permission_classes = [IsDirectionUser]

    def get_queryset(self):
        user = self.request.user
        try:
            profile = UserProfile.objects.get(account=user)
        except UserProfile.DoesNotExist:
            raise PermissionDenied("Profil utilisateur introuvable.")

        if profile.role != 'direction':
            raise PermissionDenied("Accès réservé à la direction.")

        return Conge.objects.all().order_by('-date_creation')

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)
    



import logging

logger = logging.getLogger(__name__)

class CertificatTexteAPIView(APIView):
    permission_classes = [IsFinanceUser]

    def post(self, request):
        serializer = CertificatTexteSerializer(data=request.data)
        if serializer.is_valid():
            etudiant_id = serializer.validated_data['etudiant_id']
            annee_scolaire = serializer.validated_data['annee_scolaire']

            etudiant = get_object_or_404(Etudiant, pk=etudiant_id)

            texte_certificat = (
                f"Je soussigné, directeur de l'établissement, certifie que l'élève "
                f"{etudiant.nom} {etudiant.prenom}, né(e) le {etudiant.dateDeNaissance.strftime('%d/%m/%Y')} "
                f"est régulièrement inscrit(e) pour l'année scolaire "
                f"{annee_scolaire}.\n\n"
                f"Fait à Antananarivo, le [Date d’aujourd’hui]."
            )

            return Response({"texte_certificat": texte_certificat})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExportCertificatDocxAPIView(APIView):
    permission_classes = [IsFinanceUser]

    def post(self, request):
        serializer = ExportCertificatSerializer(data=request.data)
        if serializer.is_valid():
            etudiant_id = serializer.validated_data['etudiant_id']
            texte_certificat = serializer.validated_data['texte_certificat']

            etudiant = get_object_or_404(Etudiant, pk=etudiant_id)
            nom_etudiant = f"{etudiant.nom}_{etudiant.prenom}"

            return creer_document_certificat(nom_etudiant, texte_certificat)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class RecrutementViewSet(viewsets.ModelViewSet):
    queryset = Recrutement.objects.all()
    serializer_class = RecrutementSerializer
    permission_classes= [IsDirectionUser]
    
    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsDirectionUser]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return []
        return [IsDirectionUser()]
    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()