from twilio.rest import Client
from django.conf import settings

def envoyer_whatsapp_message(numero_from, numero_to, message_text):
    """
    Envoyer un message WhatsApp via Twilio
    """
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    message = client.messages.create(
        body=message_text,
        from_=f'whatsapp:{numero_from}',
        to=f'whatsapp:{numero_to}'
    )

    return message.sid  # Retourne l'ID du message Twilio pour suivi
