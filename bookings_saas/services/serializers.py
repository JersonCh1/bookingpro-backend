from rest_framework import serializers

from .models import Service, Staff


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Service
        fields = ['id', 'name', 'description', 'duration', 'price', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class StaffSerializer(serializers.ModelSerializer):
    """
    Para escritura (POST/PATCH/PUT): acepta `service_ids` (lista de PKs).
    El queryset se restringe a los servicios del propio tenant en __init__.
    """
    service_ids = serializers.PrimaryKeyRelatedField(
        source='services',
        many=True,
        queryset=Service.objects.none(),   # sobreescrito en __init__
        required=False,
    )

    class Meta:
        model  = Staff
        fields = ['id', 'name', 'phone', 'service_ids', 'is_active']
        read_only_fields = ['id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            from bookings_saas.tenants.permissions import get_tenant
            tenant = get_tenant(request.user)
            if tenant:
                self.fields['service_ids'].child_relation.queryset = (
                    Service.objects.filter(tenant=tenant)
                )


class StaffDetailSerializer(StaffSerializer):
    """
    Para lectura (GET detail): incluye objetos completos de servicios.
    """
    services = ServiceSerializer(many=True, read_only=True)

    class Meta(StaffSerializer.Meta):
        fields = StaffSerializer.Meta.fields + ['services']
