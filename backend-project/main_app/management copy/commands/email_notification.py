# utils/email_notification.py

from django.core.mail import send_mail
from main_app.models import Parent

def envoyer_rappel_paiement():
    parents = Parent.objects.filter(
        eleve__paiement__statut='non payé'
    ).distinct()

    for parent in parents:
        if parent.email:
            send_mail(
                subject="⏰ Rappel de paiement des frais de scolarité",
                message=f"Bonjour {parent.nom},\n\nNous vous rappelons que vous avez des paiements en attente pour votre/vos enfant(s). Merci de régulariser la situation dans les plus brefs délais.\n\nCordialement,\nÉcole",
                from_email="antso.finaritra@gmail.com",
                recipient_list=[parent.email],
                fail_silently=False,
            )
