"""
notifications/whatsapp.py
─────────────────────────
Integración con TextMeBot (WhatsApp gratuito).

Cómo funciona TextMeBot:
  1. El número remitente (+51996379418) debe estar configurado en TextMeBot.
  2. Se obtiene un API key personal desde el panel de TextMeBot.
  3. Ese API key se guarda en CALLMEBOT_API_KEY (variable reutilizada).

Endpoint:
  GET https://api.textmebot.com/send.php?recipient=PHONE&apikey=APIKEY&text=TEXT

  - recipient: número con código de país (ej: +51987654321)
  - apikey:    API key personal del remitente configurado en TextMeBot
  - text:      mensaje (máx ~1000 chars)

Recomendación TextMeBot:
  - Esperar 5 segundos entre mensajes consecutivos para evitar bloqueos.

Notas de implementación:
  - Todas las llamadas HTTP se hacen en un thread daemon para no bloquear.
  - Los errores se loggean pero nunca rompen el flujo principal.
"""
import logging
import threading
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TEXTMEBOT_URL = 'https://api.textmebot.com/send.php'

_send_lock = threading.Lock()
_last_send_time = 0.0


def _do_send(phone: str, message: str, apikey: str) -> bool:
    """
    Realiza la llamada HTTP a TextMeBot (bloqueante, llamar en thread).
    Retorna True si el mensaje fue aceptado (2xx), False si no.
    Aplica un delay de 5 segundos entre envíos consecutivos.
    """
    global _last_send_time

    # Normalizar teléfono: quitar espacios y guiones, conservar '+'
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        phone = '+' + phone

    params = {
        'recipient': phone,
        'apikey':    apikey,
        'text':      message,
    }

    # Delay de 5 segundos entre envíos para no ser bloqueado por TextMeBot
    with _send_lock:
        now = time.time()
        elapsed = now - _last_send_time
        if _last_send_time > 0 and elapsed < 5:
            time.sleep(5 - elapsed)

        try:
            r = requests.get(TEXTMEBOT_URL, params=params, timeout=15)
            _last_send_time = time.time()
            if r.status_code == 200:
                logger.info('WhatsApp enviado a %s', phone)
                return True
            else:
                logger.warning('TextMeBot respuesta %s para %s: %s', r.status_code, phone, r.text[:200])
                return False
        except requests.RequestException as exc:
            _last_send_time = time.time()
            logger.error('Error enviando WhatsApp a %s: %s', phone, exc)
            return False


def send_whatsapp(phone: str, message: str, apikey: str = None) -> None:
    """
    Envía un mensaje WhatsApp de forma ASÍNCRONA (thread daemon).
    Nunca bloquea ni lanza excepciones al llamador.

    Args:
        phone:   Número del destinatario (con código de país).
        message: Texto del mensaje.
        apikey:  API key de TextMeBot. Si no se pasa, usa CALLMEBOT_API_KEY del settings.
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
        'BookingPro: Mensaje de prueba de integracion TextMeBot. '
        'Si recibes esto, la configuracion funciona correctamente.'
    )
    print(f'Enviando mensaje de prueba a {phone}...')
    result = _do_send(phone, message, key)
    if result:
        print('Mensaje enviado correctamente.')
    else:
        print('Fallo al enviar. Revisa los logs para más detalle.')
    return result
