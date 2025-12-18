from django.db.models import Avg, Q
from .models import Etudiant, Classe, Bulletin, EvaluationEtudiant, PresenceEtudiant, Periode
from accounts.models import Notification
from django.utils import timezone

def moyenne_eleve(eleve, periode=None):
    qs = Bulletin.objects.filter(eleve=eleve)
    if periode:
        qs = qs.filter(periode=periode)
    return qs.aggregate(moyenne=Avg('moyenneGenerale'))['moyenne']

def evolution_notes_eleve(eleve, periodes=None):
    qs = Bulletin.objects.filter(eleve=eleve)
    if periodes:
        qs = qs.filter(periode__in=periodes)
    return list(qs.order_by('periode__ordre').values_list('periode__nom', 'moyenneGenerale'))

def moyenne_classe(classe, periode=None):
    eleves = Etudiant.objects.filter(classe=classe)
    qs = Bulletin.objects.filter(eleve__in=eleves)
    if periode:
        qs = qs.filter(periode=periode)
    return qs.aggregate(moyenne=Avg('moyenneGenerale'))['moyenne']

def taux_absence_classe(classe, periode=None):
    eleves = Etudiant.objects.filter(classe=classe)
    total = PresenceEtudiant.objects.filter(etudiant__in=eleves)
    absents = total.filter(statut=PresenceEtudiant.ABSENT)
    if periode:
        cours_ids = classe.cours_set.filter(date__range=(periode.dateDebut, periode.dateFin)).values_list('id', flat=True)
        total = total.filter(cours_id__in=cours_ids)
        absents = absents.filter(cours_id__in=cours_ids)
    n_total = total.count()
    n_absent = absents.count()
    return (n_absent / n_total * 100) if n_total > 0 else 0

def detecter_eleves_difficulte(seuil_moyenne=8, nb_periodes=2, absences_seuil=3, periode=None):
    # Elèves avec moyenne faible sur nb_periodes consécutives
    periodes = Periode.objects.all().order_by('-ordre')[:nb_periodes]
    eleves = Etudiant.objects.all()
    alertes = []
    for eleve in eleves:
        moyennes = evolution_notes_eleve(eleve, periodes)
        if len(moyennes) == nb_periodes and all(m is not None and m < seuil_moyenne for _, m in moyennes):
            alertes.append((eleve, 'moyenne_basse'))
        # Absences répétées
        absences = PresenceEtudiant.objects.filter(etudiant=eleve, statut=PresenceEtudiant.ABSENT)
        if periode:
            absences = absences.filter(cours__date__range=(periode.dateDebut, periode.dateFin))
        if absences.count() >= absences_seuil:
            alertes.append((eleve, 'absences_repetees'))
    return alertes

def notifier_eleves_difficulte():
    alertes = detecter_eleves_difficulte()
    for eleve, raison in alertes:
        titre = "Alerte : élève en difficulté"
        if raison == 'moyenne_basse':
            message = f"{eleve.nom} {eleve.prenom} a une moyenne basse sur plusieurs périodes."
        else:
            message = f"{eleve.nom} {eleve.prenom} a de nombreuses absences."
        Notification.objects.get_or_create(
            user=eleve.parent,
            notif_type='info',
            title=titre,
            message=message,
            link=f"/eleves/{eleve.id}/"
        )
