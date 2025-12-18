from django.shortcuts import render
import pandas as pd
import io
import unidecode
from .models import *
from .permissions import EtudiantPermission
from rest_framework.response import Response
from rest_framework.decorators import api_view, action
from rest_framework import status
from rest_framework import viewsets, generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from .app_api.serializers import *
from fuzzywuzzy import process
from django.db.models import F, Q, Value, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, time, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Etudiant, Classe, Periode
from .services import moyenne_eleve, moyenne_classe, taux_absence_classe, evolution_notes_eleve, detecter_eleves_difficulte
from accounts.models import UserProfile, Notification as NotificationAccounts
from django.contrib.auth.models import User
from main_app.models import Notification as NotificationMainApp
from django.core.mail import send_mail



# Create your views here.
class CoursViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Cours.objects.none()
    serializer_class = CoursSerializer

    def get_queryset(self):
        user = self.request.user
        profile = user.userprofile

        if profile.role in ['direction', 'finance']:
            return Cours.objects.all()
        elif profile.role == 'enseignant':
            return Cours.objects.filter(enseignant=user)
             

class PresenceEtudiantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PresenceEtudiant.objects.all()
    serializer_class = PresenceEtudiantSerializer

class PresencePersonnelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PresencePersonnel.objects.all()
    serializer_class = PresencePersonnelSerializer

@api_view(['GET'])
def verifier_presence_par_cours(request, cours_id):
    try:
        cours = Cours.objects.get(id=cours_id)
    except Cours.DoesNotExist:
        return Response({"detail": "Cours non trouvé"}, status=status.HTTP_404_NOT_FOUND)
    user = request.user

    all_students = Etudiant.objects.filter(classe__titulaire=user)
    presence_records = PresenceEtudiant.objects.filter(cours=cours)

    # Étudiants ayant une fiche de présence
    students_with_presence_ids = presence_records.values_list('etudiant_id', flat=True)

    # Étudiants sans fiche de présence
    students_without_presence = all_students.exclude(id__in=students_with_presence_ids)

    if students_without_presence.exists():
        # Mode création : certains étudiants n'ont pas encore de fiche
        serialized_students = EtudiantSerializer(students_without_presence, many=True)
        return Response({
            "mode": "create",
            "students_without_presence": serialized_students.data
        })

    # Mode mise à jour : tous les étudiants ont une fiche
    serialized_presences = PresenceEtudiantSerializer(presence_records, many=True)
    return Response({
        "mode": "update",
        "presences": serialized_presences.data
    })

# class GetClass(APIView):
#     permission_classes = [AllowAny]
#     def get(self, request):
#         try:
#             annee = AnneeScolaire.objects.order_by('anneeScolaire').values_list('anneeScolaire', flat='true').first()
#             classe = Classe.objects.filter(annee)
#             data = [{'id': a.id,'nom':a.nom }for a in classe]
#             return Response(data, status=200)
#         except Etudiant.DoesNotExist:
#             return Response({'detail': 'Elève non trouvé'}, status=404) 
       

class PresenceStatsEleveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, eleve_id):
        try:
            eleve = Etudiant.objects.get(id=eleve_id)
        except Etudiant.DoesNotExist:
            return Response({'detail': 'Elève non trouvé'}, status=404)

        # Regrouper par mois
        stats = {}
        presences = PresenceEtudiant.objects.filter(etudiant=eleve)
        for presence in presences.select_related('cours'):
            mois = presence.cours.date.strftime('%Y-%m')
            if mois not in stats:
                stats[mois] = {
                    'mois': mois,
                    'retards_30mn': 0,
                    'absences_demi_journee': 0,
                    'heures_retard': 0.0,
                    'heures_absence': 0.0
                }
            # Retard > 30mn
            if presence.statut == PresenceEtudiant.RETARD and presence.heureA:
                cours_debut = presence.cours.heureDebut
                if presence.heureA and cours_debut:
                    from datetime import datetime, timedelta
                    dt1 = datetime.combine(datetime.today(), presence.heureA)
                    dt2 = datetime.combine(datetime.today(), cours_debut)
                    retard = dt1 - dt2
                else:
                    retard = timedelta()
                if retard.total_seconds() >= 30*60:
                    stats[mois]['retards_30mn'] += 1
                    stats[mois]['heures_retard'] += retard.total_seconds() / 3600  # Ajoute la durée du retard en heures
            # Absence > demi-journée
            if presence.statut == PresenceEtudiant.ABSENT and presence.cours.duree and presence.cours.duree >= 3:  # 3h = demi-journée
                stats[mois]['absences_demi_journee'] += 1
                stats[mois]['heures_absence'] += presence.cours.duree  # Ajoute la durée du cours comme absence (en heures)

        # Retourner les stats triées par mois
        result = list(sorted(stats.values(), key=lambda x: x['mois']))
        return Response(result)

class PreviewExcelAPIView(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Lire toutes les feuilles Excel
            sheets = pd.read_excel(io.BytesIO(file.read()), sheet_name=None, engine="openpyxl")

            required_columns = {"nom", "prenoms", "sexe"}
            optional_columns = {"dateDeNaissance", "classe", "religion", "adresse", "image", "pere", "mere"}
            preview_data = []

            for sheet_name, df in sheets.items():
                # Normaliser les noms de colonnes (suppression accents, minuscule, suppression espaces)
                def normalize(text):
                    return unidecode.unidecode(text).lower().replace(" ", "")

                df_columns_normalized = {normalize(col): col for col in df.columns}
                
                # Trouver la meilleure correspondance pour chaque colonne requise
                column_mapping = {}
                used_columns = set()  # Ensemble pour suivre les colonnes déjà utilisées dans le mapping

                # Trouver les correspondances pour les colonnes requises
                for col in required_columns:
                    best_match = None
                    best_score = 0
                    matches = process.extract(col, df_columns_normalized.keys(), limit=5)  # Extraire les meilleures correspondances
                    for match, score in matches:
                        # Vérifier si le match n'a pas déjà été utilisé dans le mapping
                        if score > best_score and score > 80 and match not in used_columns:
                            best_score = score
                            best_match = match

                    if best_match:
                        column_mapping[df_columns_normalized[best_match]] = col
                        used_columns.add(best_match)  # Ajouter à l'ensemble des colonnes utilisées
                
                # Trouver les correspondances pour les colonnes optionnelles
                for col in optional_columns:
                    best_match = None
                    best_score = 0
                    matches = process.extract(col, df_columns_normalized.keys(), limit=5)  # Extraire les meilleures correspondances
                    for match, score in matches:
                        if score > best_score and score > 80:
                            best_match = match
                            best_score = score
                    
                    if best_match:
                        column_mapping[df_columns_normalized[best_match]] = col
                    else:
                        print(f"Aucune bonne correspondance trouvée pour la colonne requise: {col}")
                        
                
                # Vérifier si toutes les colonnes requises sont trouvées
                if not set(column_mapping.values()).issuperset(required_columns):
                    return Response({"error": f"Colonnes manquantes dans {sheet_name}: {set(required_columns) - set(column_mapping.values())}"},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Renommer les colonnes
                df = df.rename(columns=column_mapping)

                df = df.fillna('')  # Remplacer NaN par une chaîne vide ou 'null' si nécessaire

                # Convertir les dates de naissance au bon format
                if "dateDeNaissance" in df.columns:
                    df["dateDeNaissance"] = pd.to_datetime(df["dateDeNaissance"], errors="coerce").dt.strftime('%Y-%m-%d')

                # Convertir le dataframe en JSON
                json_data = df.to_dict(orient="records")
                
                # Ajouter les informations de classe si présente
                for record in json_data:
                    # Récupérer ou créer la classe si la colonne existe
                    if 'classe' in record and record['classe']:
                        try:
                            classe, created = Classe.objects.get_or_create(
                                nom=record['classe'],
                                defaults={
                                    'titulaire': request.user,  # Utiliser l'utilisateur actuel comme titulaire par défaut
                                    'niveau': Cycle.objects.first(),
                                    'categorie': Classe.PRESCOLAIRE  
                                }
                            )
                            record['classe_id'] = classe.id
                            record['classe_created'] = created
                        except Exception as e:
                            record['classe_error'] = str(e)
                    else:
                        # Ajouter un indicateur si pas de classe
                        record['classe_id'] = None

                # Ajouter un contrôle pour la présence de NaN avant la conversion en JSON
                for record in json_data:
                    for key, value in record.items():
                        if isinstance(value, float) and pd.isna(value):
                            record[key] = None  # Remplacer NaN par None (ou une autre valeur par défaut)
                    
                preview_data.append({"sheet": sheet_name, "data": json_data})
                print(json_data)

            return Response({"preview": preview_data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SaveExcelAPIView(APIView):
    def post(self, request, *args, **kwargs):
        students_data = request.data.get("students", [])
        
        # Validate input
        if not students_data:
            return Response({"error": "Aucune donnée d'étudiant fournie"}, status=status.HTTP_400_BAD_REQUEST)
        
        created_students = []
        errors = []
        
        for student_data in students_data:
            try:
                # Validate required fields
                # Vérifier les champs requis
                if not all(key in student_data for key in ['nom', 'prenoms', 'sexe', 'dateDeNaissance']):
                    errors.append({
                        "data": student_data, 
                        "error": "Champs requis manquants (nom, prenoms, sexe, dateDeNaissance)"
                    })
                    continue
                
                # Normalize data
                student_data['sexe'] = student_data['sexe'].upper()
                if student_data['sexe'] not in ['H', 'F']:
                    student_data['sexe'] = 'H'  # Default to Masculin
                
                # Convert date
                if student_data['dateDeNaissance']:
                    try:
                        student_data['dateDeNaissance'] = datetime.strptime(student_data['dateDeNaissance'], '%Y-%m-%d').date()
                    except ValueError:
                        errors.append({
                            "data": student_data, 
                            "error": f"Format de date invalide: {student_data['dateDeNaissance']}"
                        })
                        continue
                
                # Optional fields with default values
                optional_fields = [
                    'religion', 'adresse', 'pere', 'mere'
                ]
                for field in optional_fields:
                    student_data[field] = student_data.get(field, '')
                
                # Gérer l'assignation de classe
                classe = None
                if student_data.get('classe_id'):
                    try:
                        classe = Classe.objects.get(id=student_data['classe_id'])
                    except Classe.DoesNotExist:
                        errors.append({
                            "data": student_data, 
                            "error": f"Classe avec ID {student_data['classe_id']} non trouvée"
                        })
                        continue

                # Préparer les données de l'étudiant
                student_fields = {
                    'nom': student_data['nom'],
                    'prenom': student_data['prenoms'],
                    'sexe': student_data['sexe'],
                    'classe': classe  # Assignation de la classe (peut être None)
                }

                # Ajouter les champs optionnels s'ils sont présents
                optional_fields = [
                    'dateDeNaissance', 'religion', 'adresse', 'image', 'pere', 'mere'
                ]
                for field in optional_fields:
                    if field in student_data and student_data[field]:
                        student_fields[field] = student_data[field]

                # Create student
                student = Etudiant.objects.create(**student_fields)
                created_students.append(student)
            
            except Exception as e:
                errors.append({
                    "data": student_data, 
                    "error": str(e)
                })
        
        # Prepare response
        response_data = {
            "success": len(created_students),
            "total": len(students_data),
            "errors": errors
        }
        
        # Return appropriate status
        if errors:
            print(errors)
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        
        return Response(response_data, status=status.HTTP_201_CREATED)

        

class EtudiantViewSet(viewsets.ModelViewSet):
    permission_classes = [EtudiantPermission]
    queryset = Etudiant.objects.none() 
    serializer_class = EtudiantSerializer
    def get_queryset(self):
        user = self.request.user
        profile = user.userprofile

        if profile.role in ['direction', 'finance']:
            return Etudiant.objects.all()
        elif profile.role == 'enseignant':
            return Etudiant.objects.filter(classe__titulaire=user)
        elif profile.role == 'parent':
            return Etudiant.objects.filter(parent=user)
   

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        if query_params:
            param_name, param_value = list(query_params.items())[0]  # Récupère le premier paramètre et sa valeur
            
            # Essayer de filtrer avec User directement
            try:
                filtered_queryset = Etudiant.objects.filter(**{param_name: param_value})
                if not filtered_queryset.exists():  # Si aucun résultat, essayer userprofile__
                    filtered_queryset = Etudiant.objects.filter(**{f"classe__{param_name}": param_value})
                    if not filtered_queryset.exists():  
                        filtered_queryset = Etudiant.objects.filter(**{f"parent__{param_name}": param_value})
            except Exception as e:
                filtered_queryset = Etudiant.objects.filter(**{f"classe__{param_name}": param_value})

            serializer = self.get_serializer(filtered_queryset, many=True)
            return Response(serializer.data)

        return super().list(request, *args, **kwargs)
    

class ClasseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Classe.objects.none()
    serializer_class = ClasseSerializer
    
    def get_queryset(self):
        user = self.request.user
        profile = user.userprofile

        if profile.role in ['direction', 'finance']:
            return Classe.objects.all()
        elif profile.role == 'enseignant':
            return Classe.objects.filter(titulaire=user)
        

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        if query_params:
            param_name, param_value = list(query_params.items())[0] 
            
            
            try:
                filtered_queryset = Classe.objects.filter(**{param_name: param_value})
                if not filtered_queryset.exists(): 
                    filtered_queryset = Classe.objects.filter(**{f"anneeScolaire__{param_name}": param_value})
                    if not filtered_queryset.exists():  
                        filtered_queryset = Classe.objects.filter(**{f"titulaire__{param_name}": param_value})
            except Exception as e:
                filtered_queryset = Classe.objects.filter(**{f"anneeScolaire__{param_name}": param_value})

            serializer = self.get_serializer(filtered_queryset, many=True)
            return Response(serializer.data)

        return super().list(request, *args, **kwargs)

class AnneeScolaireViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = AnneeScolaire.objects.all()
    serializer_class = AnneeScolaireSerializer

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        if query_params:
            param_name, param_value = list(query_params.items())[0]
            filtered_queryset = AnneeScolaire.objects.filter(**{param_name: param_value}) 
            serializer = self.get_serializer(filtered_queryset, many=True)
            return Response(serializer.data)
        return super().list(request, *args, **kwargs)
    
class DomaineViewSet(viewsets.ModelViewSet):
    queryset = DomaineEnseignement.objects.all().order_by('ordreAffichage')
    serializer_class = DomaineSerializer
    permission_classes = [IsAuthenticated]

class CycleViewSet(viewsets.ModelViewSet):
    queryset = Cycle.objects.all()
    serializer_class = CycleSerializer
    permission_classes = [IsAuthenticated]

class PeriodeViewSet(viewsets.ModelViewSet):
    queryset = Periode.objects.all().order_by('ordre')
    serializer_class = PeriodeSerializer
    permission_classes = [IsAuthenticated]

class EvaluationEtudiantViewSet(viewsets.ModelViewSet):
    queryset = EvaluationEtudiant.objects.all()
    serializer_class = EvaluationEtudiantSerializer
    permission_classes = [IsAuthenticated]

class BulletinViewSet(viewsets.ModelViewSet):
    queryset = Bulletin.objects.all()
    serializer_class = BulletinSerializer
    permission_classes = [IsAuthenticated]

class StatistiquesClasseAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, classe_id, periode_id=None):
        try:
            classe = Classe.objects.get(id=classe_id)
        except Classe.DoesNotExist:
            return Response({'detail': 'Classe non trouvée'}, status=404)
        periode = None
        if periode_id:
            try:
                periode = Periode.objects.get(id=periode_id)
            except Periode.DoesNotExist:
                return Response({'detail': 'Période non trouvée'}, status=404)
        data = {
            'moyenne_classe': moyenne_classe(classe, periode),
            'taux_absence': taux_absence_classe(classe, periode),
        }
        return Response(data)

class EvolutionEleveAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, eleve_id):
        try:
            eleve = Etudiant.objects.get(id=eleve_id)
        except Etudiant.DoesNotExist:
            return Response({'detail': 'Elève non trouvé'}, status=404)
        evolution = evolution_notes_eleve(eleve)
        return Response({'evolution': evolution})

class AlertesDifficulteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        alertes = detecter_eleves_difficulte()
        result = [
            {
                'eleve': f"{e.nom} {e.prenom}",
                'raison': raison
            } for e, raison in alertes
        ]
        return Response({'alertes': result})

class RapportPedagogiqueViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RapportPedagogique.objects.all()
    serializer_class = RapportPedagogiqueSerializer

    def perform_create(self, serializer):
        # 'lu' reste False par défaut
        rapport = serializer.save(auteur=self.request.user, dateDuRapport=timezone.now().date(), lu=False)

        # Notifier tous les utilisateurs direction (interne + email)
        directions = User.objects.filter(userprofile__role=UserProfile.DIRECTION)
        for direction in directions:
            # Notification interne (accounts)
            NotificationAccounts.objects.create(
                user=direction,
                notif_type="info",
                title="Nouveau rapport pédagogique",
                message=f"Un nouveau rapport pédagogique a été créé par {self.request.user.get_full_name() or self.request.user.username}.",
                link=f"/direction/rapports/{rapport.id}/"
            )
            # Notification email (main_app)
            if direction.email:
                NotificationMainApp.objects.create(
                    email_destinataire=direction.email,
                    message=f"Un nouveau rapport pédagogique a été créé par {self.request.user.get_full_name() or self.request.user.username}.",
                    type_notification='email',
                    statut='envoyé',
                )
                try:
                    send_mail(
                        subject="Nouveau rapport pédagogique",
                        message=f"Un nouveau rapport pédagogique a été créé par {self.request.user.get_full_name() or self.request.user.username}.\n\nTâche: {rapport.tache}\nClasse: {rapport.classe}",
                        from_email="noreply@tonecole.com",
                        recipient_list=[direction.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    pass

    def perform_update(self, serializer):
        # Empêche un enseignant de modifier 'lu' via update
        data = serializer.validated_data
        if 'lu' in data and not self.request.user.userprofile.role == 'direction':
            data.pop('lu')
        serializer.save(auteur=self.request.user, dateDuRapport=timezone.now().date(), **data)

    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request, pk=None):
        # Action spéciale pour la direction : marquer comme lu/non lu
        rapport = self.get_object()
        if not request.user.userprofile.role == 'direction':
            return Response({'detail': 'Action réservée à la direction'}, status=status.HTTP_403_FORBIDDEN)
        lu = request.data.get('lu', True)
        rapport.lu = bool(lu)
        rapport.save()
        return Response({'status': 'ok', 'lu': rapport.lu})




# views concernant le site

class PresentationViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = PresentationComposant.objects.all()
    serializer_class = PresentationSerializer

class AccueilViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = AccueilComposant.objects.all()
    serializer_class = AccueilSerializer

class FooterViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = FooterComposant.objects.all()
    serializer_class = FooterSerializer

class DemandeViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = DemandeInscription.objects.all()
    serializer_class = DemandeSerializer

class EventListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        events = Evenement.objects.all()
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
class EventRetrieveView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = EventSerializer
    queryset = Evenement.objects.all()
        
class EventListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        events = Evenement.objects.all()
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):  
        """ Créer un événement """

        data = request.data.copy()
        print(request.user.id)
        data["idpubliepar"] = request.user.id
        serializer = EventSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Evenement.objects.all()
    serializer_class = EventSerializer


