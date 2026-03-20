from rest_framework import serializers

from .models import Schedule, BlockedSlot


def _get_tenant(context):
    """Helper: retorna el Tenant desde el contexto del serializer."""
    request = context.get('request')
    if request and request.user and request.user.is_authenticated:
        from bookings_saas.tenants.permissions import get_tenant
        return get_tenant(request.user)
    return None


class ScheduleSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model  = Schedule
        fields = ['id', 'staff', 'day_of_week', 'day_label', 'start_time', 'end_time', 'is_active']
        read_only_fields = ['id']

    def validate_staff(self, value):
        if value is None:
            return value
        tenant = _get_tenant(self.context)
        if tenant and value.tenant_id != tenant.id:
            raise serializers.ValidationError('El empleado no pertenece a tu negocio.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_time')
        end   = attrs.get('end_time')
        if start and end and start >= end:
            raise serializers.ValidationError(
                {'end_time': 'La hora de cierre debe ser posterior a la de apertura.'}
            )
        return attrs


class BlockedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BlockedSlot
        fields = ['id', 'staff', 'date', 'start_time', 'end_time', 'reason']
        read_only_fields = ['id']

    def validate_staff(self, value):
        if value is None:
            return value
        tenant = _get_tenant(self.context)
        if tenant and value.tenant_id != tenant.id:
            raise serializers.ValidationError('El empleado no pertenece a tu negocio.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_time')
        end   = attrs.get('end_time')
        if start and end and start >= end:
            raise serializers.ValidationError(
                {'end_time': 'La hora de fin debe ser posterior a la de inicio.'}
            )
        return attrs


class AvailableSlotsResponseSerializer(serializers.Serializer):
    """Solo para documentación/schema; no se usa para parse."""
    date  = serializers.DateField()
    slots = serializers.ListField(child=serializers.DictField())
