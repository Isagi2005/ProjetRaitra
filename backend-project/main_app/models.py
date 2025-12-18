from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import timedelta
from datetime import datetime

def get_todayDate():
    return timezone.now().date()

class Cycle(models.Model):
    CODE_CHOICES = [
        ('TPS', 'Toute petite section'),
        ('PS', 'Petite section'),
        ('MS', 'Moyenne section'),
        ('GS', 'Grande section'),
        ('CP', 'CP'),
        ('CE1', 'CE1'),
        ('CE2', 'CE2'),
        ('CM1', 'CM1'),
        ('CM2', 'CM2'),
        ('6E', '6ème'),
        ('5E', '5ème'),
        ('4E', '4ème'),
        ('3E', '3ème'),
    ]
    code = models.CharField(max_length=3, choices=CODE_CHOICES, unique=True)
    nom = models.CharField(max_length=50)
    groupe_cycles = models.CharField(max_length=2, choices=[
        ('C1', 'Cycle 1 (Maternelle)'),
        ('C2', 'Cycle 2 (CP-CE1-CE2)'),
        ('C3', 'Cycle 3 (CM1-CM2-6ème)'),
        ('C4', 'Cycle 4 (5ème-4ème-3ème)')
    ])
    
    def __str__(self):
        return self.nom
class AnneeScolaire(models.Model):
    anneeScolaire = models.CharField(max_length=50, blank=False, null=False)
    def __str__(self):
        return self.anneeScolaire
class Classe(models.Model):
    COLLEGE = "college"
    PRESCOLAIRE = "prescolaire"
    PRIMAIRE = "primaire"
    LYCEE = "lycee"

    CATEGORIE = [
        (PRESCOLAIRE, 'prescolaire'),
        (PRIMAIRE, 'primaire'),
        (COLLEGE, 'college'),
        (LYCEE, 'lycee')
        
    ]
    nom = models.CharField(max_length=50, blank=False, null=False)
    titulaire = models.ForeignKey(User, related_name='classe' , on_delete=models.CASCADE,db_column='titulaire',  limit_choices_to={'userprofile__role': 'enseignant'})
    anneeScolaire = models.ForeignKey(
        AnneeScolaire, related_name='classe', 
        on_delete=models.SET_NULL,  
        db_column='anneeScolaire', blank=True, null=True 
    )
    niveau = models.ForeignKey(Cycle, on_delete=models.PROTECT, default=None)
    categorie = models.CharField(max_length=20, choices=CATEGORIE, default=PRESCOLAIRE, null=False)
    def __str__(self):
        return self.nom


class Etudiant(models.Model):
    MASCULIN = "H"
    FEMININ = "F"

    SEXE = [
        (MASCULIN, 'H'),
        (FEMININ, 'F')
        
    ]
    nom = models.CharField(max_length=255, blank=True, null=False)
    prenom = models.CharField(max_length=255, blank=True, null=False)
    image = models.ImageField(blank=True, null=True, upload_to="images/etudiant/")
    sexe = models.CharField(max_length=10, choices=SEXE, default=MASCULIN, null=False)
    religion = models.CharField(max_length=255, blank=True, null=False)
    adresse = models.CharField(max_length=255, blank=True, null=False)
    dateDeNaissance = models.DateField(db_column='dateDeNaissance', blank=True, null=True)
    pere = models.CharField(max_length=255,db_column='nomPere', blank=True, null=True)
    mere = models.CharField(max_length=255,db_column='nomMere', blank=True, null=True)
    classe = models.ForeignKey(
        Classe, related_name='etudiants', 
        on_delete=models.SET_NULL,  
        db_column='classe', blank=True, null=True 
    )

    parent = models.ForeignKey(
        User, related_name='etudiants', 
        on_delete=models.SET_NULL, 
        db_column='parent', blank=True, null=True, limit_choices_to={'userprofile__role': 'parent'}
    )
    def __str__(self):
        return self.nom
    class Meta:
        db_table = "Etudiant"



# Antso
class Depense (models.Model):
    TYPE_DEPENSES =  [
        ('salaire', 'Salaire'),
        ('materiel', 'materiel'),
        ('autre', 'autre'),
    ]
    description = models.CharField(max_length=255)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    type_depense = models.CharField(max_length=50, choices=TYPE_DEPENSES,default='salaire')
    date = models.DateField(null=False, blank=False, auto_now_add=True)
    creerPar = models.ForeignKey(User, on_delete=models.CASCADE, related_name='depenses', limit_choices_to={'role':'finance'})
    approuvePar = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,blank=True, related_name='approbations', limit_choices_to={'role':'direction'})
    approuve = models.BooleanField(default=False)

class Paiement(models.Model):
    CATEGORIES = [
        ('Ecolage', 'Ecolage'),
        ('Certificat', 'Certificat de scolarité'),
        ('Autre', 'Autre'),
    ]
    
    MOIS  = [
        ('JANVIER', 'JANVIER'),
        ('FEVRIER', 'FEVRIER'),
        ('MARS', 'MARS'),
        ('AVRIL', 'AVRIL'),
        ('MAI', 'MAI'),
        ('JUIN', 'JUIN'),
        ('JUILLET', 'JUILLET'),
        ('AOUT', 'AOUT'),
        ('SEPTEMBRE', 'SEPTEMBRE'),
        ('OCTOBRE', 'OCTOBRE'),
        ('NOVEMBRE', 'NOVEMBRE'),
        ('DECEMBRE', 'DECEMBRE')
    ]
    
    MODE_PAIEMENT =  [
        ('Chèques','Chèques'),
        ('Virement','Virement'),
        ('Espèces','Espèces'),
        ('Mobile Money','Mobile Money')
        ]
    etudiant= models.ForeignKey(Etudiant, related_name="paiements", on_delete=models.CASCADE)
    mois = models.CharField(max_length=20,choices=MOIS,default='JUIN')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    modePaiement = models.CharField(max_length=20,choices=MODE_PAIEMENT,default='Espèces')
    categorie = models.CharField(max_length=20, choices = CATEGORIES,default='Ecolage')
    description = models.TextField(blank=True, null=True)
    datePaiement = models.DateField(auto_now_add=True)
    effectuePar = models.ForeignKey(User,on_delete=models.SET_NULL, null = True)
    verrouille = models.BooleanField(default=False)
    
    def __str__(self):
        return  f"{self.id}-{self.etudiant.nom}-{self.mois}-{self.montant}-{self.modePaiement}-{self.categorie}-{self.datePaiement}"

class RapportPaiement(models.Model):
    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    mois = models.CharField(max_length=20)
    contenu = models.JSONField(blank=True, default=dict) 
    envoyeur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    message = models.TextField(blank=True)
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rapport {self.mois} - {self.classe.nom} ({self.annee_scolaire})"
        
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True,blank=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=50)
    date_naissance = models.DateField(blank=True, null=True)
    cin = models.CharField(max_length=20, unique=True,null=True,blank=True)
    poste = models.CharField(max_length=50,null=True,blank=True)
    salarie=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    dateEmbauche=models.DateField(blank=True, null=True)
    def __str__(self):
        return  f"{self.nom}-{self.prenom}"
    
class Paie(models.Model):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE)
    mois = models.CharField(max_length=10)  # Exemple : "Avril"
    annee = models.IntegerField()
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    datePaiement = models.DateTimeField(auto_now_add=True)
    mode_paiement = models.CharField(max_length=20, default="Espèce")  

    class Meta:
        unique_together = ('employe', 'mois', 'annee')    # Un seul paiement par mois/année par employé

    def __str__(self):
        return f"Paie de {self.employe.nom} {self.employe.prenom} - {self.mois} {self.annee}"
    

class CotisationSociale(models.Model):
    employe = models.ForeignKey(Employee, on_delete=models.CASCADE)
    typeCotisation = models.CharField(max_length=50)  # Exemple : "CNAPS", "IRSA"
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    datePaiement = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.typeCotisation} - {self.employe.nom}"
    
class AssuranceEleve(models.Model):
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    datePaiement = models.DateTimeField(null=False, blank=False, auto_now_add=True)
    commentaire = models.TextField(blank=True, null= True)

class Notification(models.Model):
    STATUT_CHOICES = [
        ('envoyé', 'Envoyé'),
        ('échec', 'Échec'),
        ('simulé', 'Simulé'),
    ]

    TYPE_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ]

    eleve = models.ForeignKey('main_app.Etudiant', on_delete=models.CASCADE, null=True, blank=True)
    telephone_parent = models.CharField(max_length=20, blank=True, default="")
    telephone_direction = models.CharField(max_length=20, blank=True, default="")
    email_destinataire = models.EmailField(blank=True, null=True)
    message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='envoyé')
    type_notification = models.CharField(max_length=10, choices=TYPE_CHOICES, default='whatsapp')
    twilio_sid = models.CharField(max_length=50, blank=True, null=True)
    email_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.type_notification} - {self.statut} ({self.created_at})"

    
class Conge(models.Model):
    STATUT_CHOICES = [
        ('valide', 'Validé'),
        ('annule', 'Annulé'),
    ]

    TYPE_CONGE_CHOICES = [
        ('maladie', 'Congé maladie'),
        ('maternite', 'Congé maternité'),
        ('paternite', 'Congé paternité'),
        ('annuel', 'Congé annuel'),
        ('permission', 'Permission'),
        ('autre', 'Autre'),
    ]

    employe = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name="conges")
    date_debut = models.DateField()
    date_fin = models.DateField()
    raison = models.TextField()
    type_conge = models.CharField(max_length=20, choices=TYPE_CONGE_CHOICES, default='annuel')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='valide')
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employe} | {self.type_conge} | {self.date_debut} -> {self.date_fin} ({self.statut})"
    
class NotificationConge(models.Model):
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    date = models.DateField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    def __str__(self):
        return f"Notif pour {self.destinataire.username} : {self.message}"



# Tsiory

class Cours(models.Model):
    enseignant = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'userprofile__role': 'enseignant'})
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
    date = models.DateField(blank=True, null=False, default=get_todayDate)
    heureDebut = models.TimeField(blank=True, null=False)
    heureFin = models.TimeField(blank=True, null=False)
    class Meta:
        db_table = 'Cours'
    def __str__(self):
        return f"{self.classe} - {self.date}"
    @property
    def duree(self):
        # On suppose que heureDebut et heureFin sont toujours renseignés
        debut = datetime.combine(datetime.today(), self.heureDebut)
        fin = datetime.combine(datetime.today(), self.heureFin)
        return (fin - debut).total_seconds() / 3600

class PresenceEtudiant(models.Model):
    PRESENT = 'P'
    ABSENT = 'A'
    RETARD = 'R'
    STATUT = [
        (PRESENT, 'P'),
        (ABSENT, 'A'),
        (RETARD, 'R')
    ]
    etudiant = models.ForeignKey(Etudiant, on_delete=models.SET_NULL, null=True)
    cours = models.ForeignKey(Cours, on_delete=models.SET_NULL, null=True)
    statut = models.CharField(max_length=10, choices=STATUT, default=PRESENT)
    heureA = models.TimeField(blank=True, null=True)
    raison = models.CharField(max_length=255, blank=True, null=True)
    class Meta:
        db_table = 'PresenceEtudiant'
        unique_together = ('etudiant', 'cours')
    def __str__(self):
        return f"{self.etudiant}-{self.cours} - {self.statut}"

    def save(self, *args, **kwargs):
        if self.heureA:
            # Si l'heure d'arrivée est après le début du cours, marquer comme retard
            if self.heureA > self.cours.heureDebut:
                self.statut = self.RETARD
        
        super().save(*args, **kwargs)
        

class PresencePersonnel(models.Model):
    personnel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    statut = models.CharField(max_length=10, choices=PresenceEtudiant.STATUT, default=PresenceEtudiant.PRESENT)
    date = models.DateField(blank=True, null=False, default=get_todayDate)
    heureA = models.TimeField(blank=True, null=True)
    raison = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'PresencePersonnel'
    def __str__(self):
        return f"{self.etudiant}-{self.cours} - {self.statut}"   

class DomaineEnseignement(models.Model):
    TYPE_CHOICES = [
        ('TRANS', 'Transversal'),
        ('DISCIP', 'Disciplinaire'),
        ('SOCIO', 'Sociocomportemental')
    ]
    
    code = models.CharField(max_length=10, unique=True)
    nom = models.CharField(max_length=100)
    typeDomaine = models.CharField(max_length=50, choices=TYPE_CHOICES)
    cycles = models.ManyToManyField(Cycle)
    ordreAffichage = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        ordering = ['ordreAffichage']
    
    def __str__(self):
        return f"{self.nom} ({self.get_typeDomaine_display()})"


    class Meta:
        ordering = ['ordreAffichage']
    
    def __str__(self):
        return f"{self.code} - {self.nom}"

class Periode(models.Model):
    TYPE_CHOICES = [
        ('TRIM', 'Trimestre'),
        ('SEM', 'Semestre'), 
        ('ANN', 'Année scolaire')
    ]
    
    nom = models.CharField(max_length=50)
    ordre = models.PositiveSmallIntegerField()
    typePeriode = models.CharField(max_length=4, choices=TYPE_CHOICES)
    dateDebut = models.DateField(null=True)
    dateFin = models.DateField(null=True)
    anneeScolaire = models.ForeignKey('AnneeScolaire', default=1,on_delete=models.CASCADE, related_name='periodes')

    class Meta:
        ordering = ['ordre']
    
    def __str__(self):
        return self.nom


class Bulletin(models.Model):
    eleve = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE)
    appreciationGenerale = models.TextField(blank=True)
    pointsForts = models.TextField(blank=True)
    besoins = models.TextField(blank=True)
    projet = models.TextField(blank=True)
    moyenneGenerale = models.DecimalField(default=0,max_digits=4, decimal_places=2, null=False, blank=True)
    dateEdition = models.DateField(auto_now_add=True)
    class Meta:
        unique_together = ('eleve', 'periode')
    
    def __str__(self):
        return f"Bulletin {self.periode} - {self.eleve}"
    
class EvaluationEtudiant(models.Model):
    bulletin = models.ForeignKey(Bulletin, on_delete=models.CASCADE,related_name="evaluations")
    domaine = models.ForeignKey(DomaineEnseignement, null=False,on_delete=models.PROTECT)  
    valeurNote = models.DecimalField(max_digits=4, decimal_places=2, null=False, blank=True)
    appreciation = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.bulletin.eleve} - {self.domaine}"


# site models
class Evenement(models.Model):
    FORMATION = "formation"
    ANNONCE = "annonce"
    SCOLAIRE = "scolaire"
    AUTRES = "autres"
    TYPE = [
        (FORMATION, 'formation'),
        (ANNONCE, 'annonce'),
        (SCOLAIRE, 'scolaire'),
        (AUTRES, 'autres')
    ]
    idevenement = models.AutoField(db_column='idEvenement', primary_key=True)
    titre = models.CharField(max_length=50, blank=True, null=True)
    lieu = models.CharField(max_length=100, blank=True, null=True)
    typeEvent = models.CharField(max_length=50, choices=TYPE, default=SCOLAIRE, null=False)
    description = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(blank=True, null=True, upload_to="images/")
    datedebut = models.DateField(db_column='dateDebut', blank=True, null=True)  
    datefin = models.DateField(db_column='dateFin', blank=True, null=True)  
    idpubliepar = models.ForeignKey(User, related_name='events' , on_delete=models.CASCADE,db_column='publiePar',  limit_choices_to={'userprofile__role': 'direction'})  

    class Meta:
        managed = True
        db_table = 'Evenement'


class DemandeInscription(models.Model):
    LU = "L"
    NON_LU = "NL"

    STATUT = [
        (LU, 'L'),
        (NON_LU, 'NL')
    ]
    nomEleve = models.CharField(max_length=255, blank=False, null= False)
    prenomEleve = models.CharField(max_length=255, blank=True, null=False)
    lieu = models.CharField(max_length=255, null=False, blank=True)
    emailParent = models.CharField(null=True, blank=True ,max_length=120)
    dateDeNaissance =  models.DateField(db_column='dateDeNaissance', blank=True, null=True)
    contactParent = models.CharField(max_length=100, blank=False, null= False)
    classeDemande = models.CharField(max_length=255, blank=True, null= False)
    dateDeDemande = models.DateField(db_column='dateDeDemande', blank=True, null=False, default= get_todayDate) 
    statut = models.CharField(max_length=20, choices=STATUT, default=NON_LU, null=False)
    class Meta:
        db_table = "DemandeInscription"

class AccueilComposant(models.Model):
    titre= models.CharField(max_length=255, blank=True, null= False)
    texteAccueil = models.TextField(blank=False, null= False)
    image1 = models.ImageField(blank=True, null=True, upload_to="images/public/")
    image2 = models.ImageField(blank=True, null=True, upload_to="images/public/")
    image3= models.ImageField(blank=True, null=True, upload_to="images/public/")
    dateDeChangement = models.DateField(db_column='dateDeChangement', blank=True, null=False, default=get_todayDate) 
    class Meta:
        db_table = "AccueilComposant"

class PresentationComposant(models.Model):
    titrePresentation = models.CharField(max_length=255, blank=True, null= False)
    section = models.CharField(max_length=255,blank=False, null= False)
    textePresentation = models.TextField(blank=False, null= False)
    objectifs = models.CharField(max_length=255,blank=False, null= False)
    image = models.ImageField(blank=True, null=True, upload_to="images/public/")
    dateDeChangement = models.DateField(db_column='dateDeChangement', blank=True, null=False, default=get_todayDate) 
    class Meta:
        db_table = "PresentationComposant"

class FooterComposant(models.Model):
    contact = models.CharField(max_length=100, blank=True, null= False)
    emailInfo = models.EmailField(null=True, blank=True)
    adresse = models.CharField(max_length=255, blank=True, null= False)
    dateDeChangement = models.DateField(db_column='dateDeChangement', blank=True, null=False, default=get_todayDate) 
    class Meta:
        db_table = "FooterComposant"

class Recrutement(models.Model):
    description = models.TextField()
    email = models.EmailField()
    image = models.ImageField(upload_to="recrutement/")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Recrutement - {self.email}"
class Service(models.Model):
    BUFFET = 'Buffet'
    TRANSPORT = 'Transport'
    
    SERVICE_TYPES = [
        (BUFFET, 'Buvette et Restauration'),
        (TRANSPORT, 'Transport Scolaire'),
    ]
    
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='services/', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_service_type_display()


class RapportPedagogique(models.Model):
    dateDuRapport = models.DateField(default=timezone.now)
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rapports_pedagogiques')
    tache = models.CharField(max_length=255)
    heureDebut = models.TimeField()
    heureFin = models.TimeField()
    classe = models.ForeignKey('Classe', on_delete=models.SET_NULL, null=True, blank=True)
    matiere = models.CharField(max_length=100, blank=True, null=True)
    commentaire = models.TextField(blank=True, null=True)
    lu = models.BooleanField(default=False)  # Par défaut, non lu

    def __str__(self):
        return f"Rapport de {self.auteur} le {self.dateDuRapport}"