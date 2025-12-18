# tasks.py (ou dans un fichier géré par un cron job ou Celery)
from datetime import date
from main_app.models import Conge  # le modèle des congés
from .models import Employee  # ou User si c'est directement lié
from .models import NotificationConge  # ou selon l'app
from accounts.models import User

def check_conges_terminees():
    today = date.today()
    conges_terminees = Conge.objects.filter(date_fin=today)

    for conge in conges_terminees:
        employe = conge.employe
        direction_users = User.objects.filter(role='direction')  # ou selon ton système de rôles

        for directeur in direction_users:
            NotificationConge.objects.create(
                destinataire=directeur,
                message=f"Le congé de {employe.nom} {employe.prenom} se termine aujourd'hui ({today})"
            )
