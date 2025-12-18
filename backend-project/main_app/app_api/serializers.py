from accounts.models import UserProfile
from main_app.models import *
from rest_framework import serializers
from datetime import date
import locale


try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except locale.Error:
    # Fallback : essayer fr_FR ou laisser défaut
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR")
    except locale.Error:
        pass

def format_date_fr(date_obj):
    if not date_obj:
        return ""
    return date_obj.strftime('%d %B %Y')

class EtudiantSerializer(serializers.ModelSerializer):
    parentX = serializers.PrimaryKeyRelatedField(
        queryset=UserProfile.objects.filter(role="parent"),
        required=False, allow_null=True
    )
    classeName = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = Etudiant
        fields = [
            "id", "nom", "prenom", "image", "sexe", "religion",
            "adresse", "dateDeNaissance", "classe", "parent",
            "parentX", "classeName", "age"
        ]

    def get_classeName(self, obj):
        return obj.classe.nom if obj.classe else None

    def get_age(self, obj):
        if obj.dateDeNaissance:
            today = date.today()
            age = today.year - obj.dateDeNaissance.year
            # Ajuster si l’anniversaire n’est pas encore passé cette année
            if (today.month, today.day) < (obj.dateDeNaissance.month, obj.dateDeNaissance.day):
                age -= 1
            return age
        return None

class AnneeScolaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnneeScolaire
        fields = ("__all__")
        extra_kwargs = {
            'dateDeChangement': {'read_only': True}
        }
class CycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cycle
        fields = '__all__'

class ClasseSerializer(serializers.ModelSerializer):
    niveauDetail = CycleSerializer(source='niveau', read_only=True)
    anneeDetail = AnneeScolaireSerializer(source='anneeScolaire', read_only=True)
    yearName = serializers.SerializerMethodField()
    profName = serializers.SerializerMethodField()
    effectif = serializers.SerializerMethodField()
    nbrGarcon = serializers.SerializerMethodField()
    nbrFille = serializers.SerializerMethodField()
    class Meta:
        model = Classe
        fields = ["id",'nom', 'titulaire', 'anneeScolaire','niveauDetail',"anneeDetail",'categorie' ,'yearName','profName', 'effectif', 'nbrGarcon','nbrFille']
    def get_yearName(self, obj):
        return obj.anneeScolaire.anneeScolaire if obj.anneeScolaire else None
    def get_profName(self, obj):
        return f"{obj.titulaire.first_name} {obj.titulaire.last_name}" if obj.titulaire else None
    def get_effectif(self, obj):
        return Etudiant.objects.filter(classe=obj, classe__anneeScolaire=obj.anneeScolaire).count()
    def get_nbrGarcon(self, obj):
        return Etudiant.objects.filter(classe=obj, classe__anneeScolaire=obj.anneeScolaire, sexe=Etudiant.MASCULIN).count()
    def get_nbrFille(self, obj):
        return Etudiant.objects.filter(classe=obj, classe__anneeScolaire=obj.anneeScolaire, sexe=Etudiant.FEMININ).count()
    
class CoursSerializer(serializers.ModelSerializer):
    enseignantNom = serializers.SerializerMethodField()
    dateFormatte = serializers.SerializerMethodField()
    classeNom = serializers.SerializerMethodField()
    class Meta:
        model = Cours
        fields = ["id", "enseignant", "classe", "date","heureDebut","classeNom","heureFin","enseignantNom","dateFormatte"]
    def get_dateFormatte(self, obj):
        return format_date_fr(obj.date)
    def get_classeNom(self, obj):
        return f'{obj.classe.nom} {obj.classe.anneeScolaire}' if obj.classe else None
    def get_enseignantNom(self, obj):
        return f"{obj.enseignant.first_name} {obj.enseignant.last_name}" if obj.enseignant else None


class PresenceEtudiantSerializer(serializers.ModelSerializer):
    etudiantName = serializers.SerializerMethodField()
    coursName = serializers.SerializerMethodField()
    class Meta:
        model = PresenceEtudiant
        fields = ["id","etudiant", "cours", "statut", "heureA","raison", "etudiantName", "coursName"]

    def get_etudiantName(self, obj):
        return f'{obj.etudiant.nom} {obj.etudiant.prenom}' if obj.etudiant else None

    def get_coursName(self, obj):
        return f'{obj.cours.date}' if obj.cours else None

    def validate(self, data):
        etudiant = data.get('etudiant')
        cours = data.get('cours')
        instance_id = self.instance.id if self.instance else None
        if PresenceEtudiant.objects.filter(etudiant=etudiant, cours=cours).exclude(id=instance_id).exists():
            raise serializers.ValidationError("Une fiche de présence existe déjà pour cet étudiant dans ce cours.")
        return data

    def create(self, validated_data):
        statut = validated_data.get('statut')
        cours = validated_data.get('cours')
        if statut == PresenceEtudiant.ABSENT:
            validated_data['heureA'] = None
        elif statut == PresenceEtudiant.RETARD:
            # heureA doit être fourni par le front
            pass
        elif statut == PresenceEtudiant.PRESENT:
            # heureA = heure de début du cours
            if cours:
                validated_data['heureA'] = cours.heureDebut
        return super().create(validated_data)

    def update(self, instance, validated_data):
        statut = validated_data.get('statut', instance.statut)
        cours = validated_data.get('cours', instance.cours)
        if statut == PresenceEtudiant.ABSENT:
            validated_data['heureA'] = None
        elif statut == PresenceEtudiant.RETARD:
            # heureA doit être fourni par le front
            pass
        elif statut == PresenceEtudiant.PRESENT:
            if cours:
                validated_data['heureA'] = cours.heureDebut
        return super().update(instance, validated_data)

class PresencePersonnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresencePersonnel
        fields = ["id","personnel", "date", "statut", "heureDebut", "heureFin", "raison"]
    

class DomaineSerializer(serializers.ModelSerializer):
    cyclesDetail = CycleSerializer(source='cycles', many=True, read_only=True)
    
    class Meta:
        model = DomaineEnseignement
        fields = '__all__'

class PeriodeSerializer(serializers.ModelSerializer):
    anneeScolaireNom = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Periode
        fields = '__all__'

    def get_anneeScolaireNom(self, obj):
        if obj.anneeScolaire:
            return getattr(obj.anneeScolaire, 'anneeScolaire', None)
        return None

class EvaluationEtudiantSerializer(serializers.ModelSerializer):
    domaine = DomaineSerializer(read_only=True)
    bulletin = serializers.PrimaryKeyRelatedField(read_only=True)
    domaine_id = serializers.PrimaryKeyRelatedField(
        queryset=DomaineEnseignement.objects.all(),
        source="domaine",
        write_only=True
    )
    class Meta:
        model = EvaluationEtudiant
        fields = ['id', 'domaine','domaine_id', "bulletin", 'valeurNote', 'appreciation','observations']

class BulletinSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.SerializerMethodField(read_only=True)
    classe_nom = serializers.SerializerMethodField(read_only=True)
    periode_nom = serializers.SerializerMethodField(read_only=True)
    evaluations = EvaluationEtudiantSerializer(many=True, required=False)
    moyenne_calculee = serializers.SerializerMethodField(read_only=True)
    total_heures_retard = serializers.SerializerMethodField(read_only=True)
    total_heures_absence = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bulletin
        fields = ['id', 'eleve', 'eleve_nom', 'classe_nom', 'periode', 'periode_nom',
                  'appreciationGenerale', 'pointsForts', 'besoins', 'projet', 'moyenneGenerale',
                  'moyenne_calculee', 'dateEdition', 'evaluations',
                  'total_heures_retard', 'total_heures_absence']


    def get_eleve_nom(self, obj):
        if hasattr(obj, 'eleve') and obj.eleve:
            return f"{obj.eleve.nom} {obj.eleve.prenom}"
        return ""

    def get_classe_nom(self, obj):
        if hasattr(obj, 'eleve') and obj.eleve and hasattr(obj.eleve, 'classe') and obj.eleve.classe:
            return str(obj.eleve.classe)
        return ""

    def get_periode_nom(self, obj):
        if hasattr(obj, 'periode') and obj.periode:
            return str(obj.periode.nom)
        return ""

    def get_moyenne_calculee(self, obj):
        evaluations = obj.evaluations.all()
        notes = [eval.valeurNote for eval in evaluations if eval.valeurNote is not None]
        if notes:
            return round(sum(notes) / len(notes), 2)
        return None

    def get_total_heures_retard(self, obj):
        if not obj.eleve or not obj.periode:
            return 0.0
        retards = PresenceEtudiant.objects.filter(
            etudiant=obj.eleve,
            cours__date__range=[obj.periode.dateDebut, obj.periode.dateFin],
            statut=PresenceEtudiant.RETARD,
            heureA__isnull=False,
            cours__heureDebut__isnull=False
        )
        total = 0.0
        for r in retards:
            if r.heureA and r.cours and r.cours.heureDebut:
                delta = (datetime.datetime.combine(datetime.date.today(), r.heureA) -
                         datetime.datetime.combine(datetime.date.today(), r.cours.heureDebut))
                total += delta.total_seconds() / 3600
        return round(total, 2)

    def get_total_heures_absence(self, obj):
        from main_app.models import PresenceEtudiant
        if not obj.eleve or not obj.periode:
            return 0.0
        absences = PresenceEtudiant.objects.filter(
            etudiant=obj.eleve,
            cours__date__range=[obj.periode.dateDebut, obj.periode.dateFin],
            statut=PresenceEtudiant.ABSENT
        )
        total = sum([a.cours.duree for a in absences if a.cours and a.cours.duree is not None])
        return round(total, 2)

    def create(self, validated_data):
        evaluations_data = validated_data.pop('evaluations', [])
        bulletin = Bulletin.objects.create(**validated_data)
        notes = []
        for eval_data in evaluations_data:
            note = eval_data.get('valeurNote')
            if note is not None:
                notes.append(note)
            EvaluationEtudiant.objects.create(
                bulletin=bulletin,
                **eval_data
            )
        # Calcul et sauvegarde de la moyenne
        if notes:
            bulletin.moyenneGenerale = round(sum(notes) / len(notes), 2)
            bulletin.save()
        return bulletin


# Antso serializer
class DepenseSerializer(serializers.ModelSerializer):
    class Meta :
        model = Depense
        fields = ["description", "montant","type_depense","date","creer_par", "approuve_par","approuve"]
        
        
class PaiementSerializer(serializers.ModelSerializer):
    effectuePar = serializers.StringRelatedField(read_only=True)
    etudiants = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    
    class Meta:
        model = Paiement
        fields = [
            'id', 'etudiant', 'etudiants', 'mois', 'montant',
            'modePaiement', 'categorie', 'description',
            'datePaiement', 'effectuePar'
        ]

    def validate(self, data):
        if not data.get('mois'):
            raise serializers.ValidationError({"mois": "Le mois est requis."})
        if not data.get('montant'):
            raise serializers.ValidationError({"montant": "Le montant est requis."})
        if not data.get('modePaiement'):
            raise serializers.ValidationError({"modePaiement": "Le mode de paiement est requis."})
        if not data.get('categorie'):
            raise serializers.ValidationError({"categorie": "La catégorie est requise."})
        if not data.get('description'):
            raise serializers.ValidationError({"description": "La description est requise."})
        return data

    def create(self, validated_data):
        etudiants_ids = validated_data.pop("etudiants", None)
        user = self.context['request'].user

        if etudiants_ids:
            paiements = []
            for etudiant_id in etudiants_ids:
                paiement = Paiement.objects.create(
                    etudiant_id=etudiant_id,
                    effectuePar=user,
                    **validated_data
                )
                paiements.append(paiement)
            return paiements  
        else:
            return Paiement.objects.create(effectuePar=user, **validated_data)
    
        
class EmployeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'
        
class PaieSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom', read_only=True)
    employe_prenom = serializers.CharField(source='employe.prenom', read_only=True)

    class Meta:
        model = Paie
        fields = ['id', 'employe', 'employe_nom', 'employe_prenom', 'mois', 'annee', 'montant', 'datePaiement','mode_paiement']
        
class CotisationSocialeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CotisationSociale
        fields =["employe", "type_cotisation","montant","date_paiement"]
        
class AssuranceEleveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssuranceEleve
        fields =["etudiant", "montant","date_paiement","commentaire"]
        
        
class RapportPaiementSerializer(serializers.ModelSerializer):
    classe_nom = serializers.CharField(source='classe.nom', read_only=True)
    annee_scolaire_nom = serializers.CharField(source='annee_scolaire.anneeScolaire', read_only=True)
    envoyeur_nom = serializers.CharField(source='envoyeur.username', read_only=True)
    

    class Meta:
        model = RapportPaiement
        fields = [
            'id', 'annee_scolaire', 'annee_scolaire_nom',
            'classe', 'classe_nom', 'mois',
            'envoyeur', 'envoyeur_nom', 'message', 'date_envoi'
        ]
        read_only_fields = ['date_envoi', 'envoyeur']
        

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        
class CongeSerializer(serializers.ModelSerializer):
    employe_nom = serializers.CharField(source='employe.nom', read_only=True)
    employe_prenom = serializers.CharField(source='employe.prenom', read_only=True)
    
    class Meta:
        model = Conge
        fields = [
            'id', 'employe', 'employe_nom', 'employe_prenom',
            'date_debut', 'date_fin', 'raison', 'type_conge',
            'statut', 'cree_par', 'date_creation'
        ]
        read_only_fields = ['cree_par', 'date_creation', 'statut']

    def validate(self, data):
        if data['date_debut'] > data['date_fin']:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        return data
    
class CertificatTexteSerializer(serializers.Serializer):
    etudiant_id = serializers.IntegerField()
    annee_scolaire = serializers.CharField()

class ExportCertificatSerializer(serializers.Serializer):
    etudiant_id = serializers.IntegerField()
    texte_certificat = serializers.CharField()
    


# serializer concernant le site
class RecrutementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recrutement
        fields = '__all__'
class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'


class RapportPedagogiqueSerializer(serializers.ModelSerializer):
    auteur = serializers.StringRelatedField(read_only=True)
    dateDuRapport = serializers.DateField(read_only=True)
    lu = serializers.BooleanField(required=False)

    class Meta:
        model = RapportPedagogique
        fields = '__all__'
        read_only_fields = ['auteur', 'dateDuRapport']
class DemandeSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    dateNaissance = serializers.SerializerMethodField()
    class Meta:
        model = DemandeInscription
        fields = ["id","nomEleve","prenomEleve","lieu","statut","emailParent", "dateDeNaissance", "dateNaissance","contactParent", "classeDemande", "dateDeDemande","date"]
    def get_date(self, obj):
        return format_date_fr(obj.dateDeDemande)
    def get_dateNaissance(self, obj):
        return format_date_fr(obj.dateDeNaissance)

class PresentationSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    class Meta:
        model = PresentationComposant
        fields = ["id","titrePresentation", "textePresentation", "section", "objectifs", "image", "dateDeChangement","date"]
        extra_kwargs = {
            'dateDeChangement': {'read_only': True}
        }
    def get_date(self, obj):
        return format_date_fr(obj.dateDeChangement)

class FooterSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    class Meta:
        model = FooterComposant
        fields = ["id","contact", "emailInfo", "adresse", "dateDeChangement","date"]
        extra_kwargs = {
            'dateDeChangement': {'read_only': True}
        }
    def get_date(self, obj):
        return format_date_fr(obj.dateDeChangement)

class AccueilSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    class Meta:
        model = AccueilComposant
        fields = ["id","titre", "texteAccueil", "image1", "image2", "image3", "dateDeChangement","date"] 
        extra_kwargs = {
            'dateDeChangement': {'read_only': True}
        }
    def get_date(self, obj):
        return format_date_fr(obj.dateDeChangement)

class EventSerializer(serializers.ModelSerializer):
    dateD = serializers.SerializerMethodField()
    dateF = serializers.SerializerMethodField()
    publiePar = serializers.SerializerMethodField()
    class Meta:
        model = Evenement
        fields = ["idevenement","titre","lieu","typeEvent", "description","image","datedebut","datefin","dateD","dateF",  "idpubliepar", "publiePar"]
    def get_dateD(self, obj):
        return format_date_fr(obj.datedebut)
    def get_publiePar(self, obj):
        return obj.idpubliepar.first_name if obj.idpubliepar else None
    def get_dateF(self, obj):
        return format_date_fr(obj.datefin)