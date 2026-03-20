"""
Helpers para construir respuestas consistentes en las views.

Uso:
    from bookings_saas.utils.responses import success, error

    return success(data=serializer.data, status=201)
    return error("Negocio no encontrado", code="NOT_FOUND", status=404)
"""
from rest_framework.response import Response
from rest_framework import status as http_status


def success(data=None, status=http_status.HTTP_200_OK, **kwargs):
    body = {'success': True, 'data': data}
    body.update(kwargs)
    return Response(body, status=status)


def error(message: str, code: str = 'ERROR', status=http_status.HTTP_400_BAD_REQUEST):
    return Response(
        {'success': False, 'error': message, 'code': code},
        status=status,
    )
