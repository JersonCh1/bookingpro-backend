import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('bookings_saas')

# Mapeo de status HTTP → código de error legible
_CODE_MAP = {
    400: 'BAD_REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT_FOUND',
    405: 'METHOD_NOT_ALLOWED',
    409: 'CONFLICT',
    422: 'VALIDATION_ERROR',
    429: 'THROTTLED',
    500: 'SERVER_ERROR',
}


def custom_exception_handler(exc, context):
    """
    Convierte todas las excepciones DRF al formato:
    {"success": false, "error": "mensaje", "code": "ERROR_CODE"}
    """
    response = exception_handler(exc, context)

    if response is not None:
        code    = _CODE_MAP.get(response.status_code, 'ERROR')
        message = _extract_message(response.data)

        logger.warning(
            f'[{code}] {context["view"].__class__.__name__} — {message}',
            exc_info=False,
        )

        response.data = {
            'success': False,
            'error':   message,
            'code':    code,
        }
    else:
        # Error 500 no capturado por DRF
        logger.exception(f'Unhandled exception in {context["view"].__class__.__name__}')
        response = Response(
            {'success': False, 'error': 'Error interno del servidor.', 'code': 'SERVER_ERROR'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_message(data) -> str:
    """Extrae un mensaje legible del dict de errores de DRF."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return str(data[0]) if data else 'Error de validación.'
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'non_field_errors' in data:
            return str(data['non_field_errors'][0])
        # Primer campo con error
        for key, val in data.items():
            msg = val[0] if isinstance(val, list) else str(val)
            return f'{key}: {msg}'
    return 'Error desconocido.'
