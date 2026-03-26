"""
notifications/whatsapp.py
─────────────────────────
Integración con TextMeBot (WhatsApp gratuito).

Endpoint:
  GET https://api.textmebot.com/send.php?recipient=PHONE&apikey=APIKEY&text=TEXT

  - recipient: número con código de país (ej: +51987654321)
  - apikey:    API key del remitente configurado en TextMeBot
  - text:      mensaje

Límite TextMeBot: 1 mensaje por cada 8 segundos (usamos 8s de margen).

Notas de implementación:
  - Todas las llamadas HTTP se hacen en un thread daemon para no bloquear.
  - Los errores se loggean pero nunca rompen el flujo principal.
  - Con múltiples workers (gunicorn) el lock es solo intra-proceso; el delay
    de 8s tiene margen suficiente para absorber colisiones entre workers.
"""
import logging
import threading
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TEXTMEBOT_URL = 'https://api.textmebot.com/send.php'
SEND_DELAY    = 8   # segundos entre envíos (TextMeBot limita a 1/5s, usamos 8 de margen)
MAX_RETRIES   = 2   # reintentos adicionales en caso de 403

_send_lock     = threading.Lock()
_last_send_time = 0.0


def _normalize_phone(phone: str) -> str:
    """
    Limpia y normaliza el número de teléfono.
    - Elimina espacios, guiones y paréntesis.
    - Si empieza por 9 y tiene 9 dígitos → número peruano, agrega +51.
    - Si no tiene '+' → agrega '+'.
    """
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not phone.startswith('+'):
        # Número peruano sin código de país: 9XXXXXXXX (9 dígitos que empiezan por 9)
        if len(phone) == 9 and phone.startswith('9'):
            phone = '+51' + phone
        else:
            phone = '+' + phone
    return phone


def _do_send(phone: str, message: str, apikey: str) -> bool:
    """
    Realiza la llamada HTTP a TextMeBot (bloqueante, llamar en thread).
    Retorna True si el mensaje fue aceptado (2xx), False si no.
    Aplica delay de SEND_DELAY segundos entre envíos y reintenta en 403.
    """
    global _last_send_time

    phone = _normalize_phone(phone)

    params = {
        'recipient': phone,
        'apikey':    apikey,
        'text':      message,
    }

    for attempt in range(1 + MAX_RETRIES):
        with _send_lock:
            now = time.time()
            elapsed = now - _last_send_time
            if _last_send_time > 0 and elapsed < SEND_DELAY:
                time.sleep(SEND_DELAY - elapsed)

            try:
                r = requests.get(TEXTMEBOT_URL, params=params, timeout=15)
                _last_send_time = time.time()

                if r.status_code == 200:
                    logger.info('WhatsApp enviado a %s', phone)
                    return True

                if r.status_code == 403 and attempt < MAX_RETRIES:
                    logger.warning(
                        'TextMeBot 403 (rate limit) para %s — reintentando en %ds (intento %d/%d)',
                        phone, SEND_DELAY, attempt + 1, MAX_RETRIES,
                    )
                    # Forzar espera antes del reintento liberando el lock
                    _last_send_time = time.time()
                    continue  # el siguiente loop dormirá SEND_DELAY completo

                logger.warning('TextMeBot respuesta %s para %s: %s', r.status_code, phone, r.text[:200])
                return False

            except requests.RequestException as exc:
                _last_send_time = time.time()
                logger.error('Error enviando WhatsApp a %s: %s', phone, exc)
                return False

    return False


def send_whatsapp(phone: str, message: str, apikey: str = None) -> None:
    """
    Envía un mensaje WhatsApp de forma ASÍNCRONA (thread daemon).
    Nunca bloquea ni lanza excepciones al llamador.

    Args:
        phone:   Número del destinatario (con código de país o número peruano de 9 dígitos).
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
        daemon=True,
    )
    t.start()


def send_test_message(phone: str, apikey: str = None) -> bool:
    """
    Prueba la integración desde el shell de Django (SÍNCRONO).

    Uso:
        python manage.py shell
        >>> from bookings_saas.notifications.whatsapp import send_test_message
        >>> send_test_message('+51987654321')
    """
    key = apikey or getattr(settings, 'CALLMEBOT_API_KEY', '')
    if not key:
        print('ERROR: CALLMEBOT_API_KEY no configurado. Agrega CALLMEBOT_API_KEY=<apikey> en .env')
        return False

    message = (
        'AgendaYa: Mensaje de prueba TextMeBot. '
        'Si recibes esto, la configuracion funciona correctamente.'
    )
    print(f'Enviando mensaje de prueba a {phone}...')
    result = _do_send(phone, message, key)
    print('OK — mensaje enviado.' if result else 'ERROR — revisa los logs.')
    return result
