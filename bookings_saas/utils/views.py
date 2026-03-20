"""
Mixins reutilizables para todas las apps del proyecto.
"""
from rest_framework import status as drf_status

from .responses import success


class SuccessResponseMixin:
    """
    Envuelve todas las respuestas estándar de DRF en el formato
    {"success": true, "data": ...}

    Compatible con ListCreateAPIView, RetrieveUpdateDestroyAPIView, etc.
    La paginación ya maneja su propio wrapping (StandardPagination).
    """

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return success(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success(serializer.data, status=drf_status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return success(None, status=drf_status.HTTP_204_NO_CONTENT)
