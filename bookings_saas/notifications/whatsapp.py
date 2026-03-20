"""
notifications/whatsapp.py
─────────────────────────
Integración con CallMeBot (WhatsApp gratuito).

Cómo funciona CallMeBot:
  1. El usuario (negocio o cliente) debe enviar "I allow callmebot to send me messages"
     al número +34 644 64 70 17 (WhatsApp) UNA sola vez para activar su cuenta.
  2. CallMeBot responde con un API key personal.
  3. Ese API key se guarda en CALLMEBOT_API_KEY (para el negocio)
     o se pasa directamente para envíos a clientes.

Endpoint:
  GET https://api.callmebot.com/whatsapp.php?phone=PHONE&text=TEXT&apikey=APIKEY

  - phone: número con código de país, con o sin '+' (ej: +51987654321 o 51987654321)
  - text:  mensaje URL-encoded (máx ~1000 chars)
  - apikey: el API key personal del DESTINATARIO

Limitaciones gratuitas:
  - Solo funciona si el DESTINATARIO activó su cuenta con CallMeBot.
  - No es ideal para clientes finales que no han activado CallMeBot,
    pero funciona perfectamente para notificar AL NEGOCIO.
  - Para el cliente final se puede usar el mismo API key del negocio
    como relay, aunque el mensaje llegará desde la cuenta del negocio.

Notas de implementación:
  - Todas las llamadas HTTP se hacen en un thread daemon para no bloquear.
  - Los errores se loggean pero nunca rompen el flujo principal.
"""
import logging
import threading
import urllib.parse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CALLMEBOT_URL = 'https://api.callmebot.com/whatsapp.php'


def _do_send(phone: str, message: str, apikey: str) -> bool:
    """
    Realiza la llamada HTTP a CallMeBot (bloqueante, llamar en thread).
    Retorna True si el mensaje fue aceptado (2xx), False si no.
    """
    # Normalizar teléfono: quitar espacios y guiones, conservar '+'
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    params = {
        'phone':  phone,
        'text':   message,
        'apikey': apikey,
    }

    try:
        r = requests.get(CALLMEBOT_URL, params=params, timeout=15)
        if r.status_code == 200:
            logger.info('WhatsApp enviado a %s', phone)
            return True
        else:
            logger.warning('CallMeBot respuesta %s para %s: %s', r.status_code, phone, r.text[:200])
            return False
    except requests.RequestException as exc:
        logger.error('Error enviando WhatsApp a %s: %s', phone, exc)
        return False


def send_whatsapp(phone: str, message: str, apikey: str = None) -> None:
    """
    Envía un mensaje WhatsApp de forma ASÍNCRONA (thread daemon).
    Nunca bloquea ni lanza excepciones al llamador.

    Args:
        phone:   Número del destinatario (con código de país).
        message: Texto del mensaje.
        apikey:  API key de CallMeBot. Si no se pasa, usa CALLMEBOT_API_KEY del settings.
    """
    key = apikey or getattr(settings, 'CALLMEBOT_API_KEY', '')
    if not key:
        logger.warning('CALLMEBOT_API_KEY no configurado — mensaje omitido para %s', phone)
        return

    t = threading.Thread(
        target=_do_send,
        args=(phone, message, key),
        daemon=True,   # no bloquea el shutdown del proceso
    )
    t.start()


def send_test_message(phone: str, apikey: str = None) -> bool:
    """
    Prueba la integración desde el shell de Django.
    A diferencia de send_whatsapp(), esta función es SÍNCRONA
    y retorna True/False para que puedas verificar el resultado.

    Uso desde el shell:
        python manage.py shell
        >>> from bookings_saas.notifications.whatsapp import send_test_message
        >>> send_test_message('+51987654321')          # usa CALLMEBOT_API_KEY del settings
        >>> send_test_message('+51987654321', 'abc123') # apikey explícito

    Returns:
        True  → mensaje enviado correctamente
        False → fallo (ver logs para detalle)
    """
    key = apikey or getattr(settings, 'CALLMEBOT_API_KEY', '')
    if not key:
        print('ERROR: CALLMEBOT_API_KEY no está configurado en settings ni se pasó como argumento.')
        print('Agrega CALLMEBOT_API_KEY=<tu_apikey> en el archivo .env')
        return False

    message = (
        'BookingPro: Mensaje de prueba de integracion CallMeBot. '
        'Si recibes esto, la configuracion funciona correctamente.'
    )
    print(f'Enviando mensaje de prueba a {phone}...')
    result = _do_send(phone, message, key)
    if result:
        print('Mensaje enviado correctamente.')
    else:
        print('Fallo al enviar. Revisa los logs para más detalle.')
    return result
