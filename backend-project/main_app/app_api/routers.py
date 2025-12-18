from rest_framework import routers
from ..views import *
from ..views2 import *


router = routers.DefaultRouter()
router.register(r'etudiant', EtudiantViewSet)
router.register(r'classe', ClasseViewSet)
router.register(r'annee', AnneeScolaireViewSet)
router.register(r'cours', CoursViewSet)
router.register(r'presEtudiant', PresenceEtudiantViewSet)
router.register(r'presPerso', PresencePersonnelViewSet)
router.register(r'domaine', DomaineViewSet, basename='domaine')
router.register(r'cycles', CycleViewSet, basename='cycle')
router.register(r'periode', PeriodeViewSet, basename='periode')
router.register(r'bulletin', BulletinViewSet, basename='bulletin')
router.register(r'evaluation', EvaluationEtudiantViewSet, basename='evaluationetudiant')

# Antso
router.register('anneeScolaire',AnneeScolaireViewSet,basename='anneeScolaire')
router.register('depense', DepenseViewSet,basename='depense')
router.register('paiement',PaiementViewSet,basename='paiement')
router.register('employee',EmployeViewSet,basename='employee')
router.register('paie',PaieViewSet,basename='paie')
router.register('cotisationSociale',CotisationSocialeViewSet,basename='cotisationSociale')
router.register('assuranceEleve',AssuranceViewSet,basename='assuranceEleve')
router.register('rapport-finance', RapportPaiementViewSet, basename='rapport-finance')
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('conges', CongeViewSet, basename='conges')
router.register('notifConge', CongeViewSet, basename='notifConge')


# site
router.register('contenu/recrutement', RecrutementViewSet)
router.register('contenu/services', ServiceViewSet, basename='service')
router.register(r'events', EventViewSet)
router.register(r'demande', DemandeViewSet)
router.register(r'footer', FooterViewSet)
router.register(r'accueil', AccueilViewSet)
router.register(r'presentation', PresentationViewSet)
router.register(r'rapport-pedagogique', RapportPedagogiqueViewSet, basename='rapportpedagogique')