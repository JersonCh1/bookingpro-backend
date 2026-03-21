from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Customer, Booking


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = ['id', 'name', 'phone', 'email', 'created_at']
        read_only_fields = ['id', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    """Serializer de lectura — usado en el dashboard del negocio."""
    customer_name    = serializers.CharField(source='customer.name',     read_only=True)
    customer_phone   = serializers.CharField(source='customer.phone',    read_only=True)
    service_name     = serializers.CharField(source='service.name',      read_only=True)
    service_price    = serializers.DecimalField(source='service.price',  max_digits=8, decimal_places=2, read_only=True)
    service_duration = serializers.IntegerField(source='service.duration', read_only=True)
    staff_name       = serializers.SerializerMethodField()
    status_label     = serializers.SerializerMethodField()

    class Meta:
        model  = Booking
        fields = [
            'id',
            'customer', 'customer_name', 'customer_phone',
            'service',  'service_name',  'service_price', 'service_duration',
            'staff',    'staff_name',
            'date', 'start_time', 'end_time',
            'status', 'status_label',
            'notes', 'created_at',
        ]
        read_only_fields = ['id', 'end_time', 'created_at']

    def get_staff_name(self, obj):
        return obj.staff.name if obj.staff else None

    def get_status_label(self, obj):
        return dict(Booking.STATUS).get(obj.status, obj.status)


class BookingCreateSerializer(serializers.Serializer):
    """
    Creación pública de reservas — el cliente llena sus datos directamente.
    No requiere autenticación. El tenant se inyecta vía contexto.
    """
    # Datos del cliente
    customer_name  = serializers.CharField(max_length=200)
    customer_phone = serializers.CharField(max_length=20)
    customer_email = serializers.EmailField(required=False, allow_blank=True)

    # Datos de la reserva
    service_id = serializers.IntegerField()
    staff_id   = serializers.IntegerField(required=False, allow_null=True)
    date       = serializers.DateField()
    start_time = serializers.TimeField()
    notes      = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        from bookings_saas.services.models import Service, Staff

        tenant = self.context['tenant']

        # ── Validar servicio ──────────────────────────────
        try:
            service = Service.objects.get(id=data['service_id'], tenant=tenant, is_active=True)
        except Service.DoesNotExist:
            raise serializers.ValidationError({'service_id': 'Servicio no encontrado o inactivo.'})
        data['service'] = service

        # ── Validar staff (opcional) ──────────────────────
        staff = None
        if data.get('staff_id'):
            try:
                staff = Staff.objects.get(id=data['staff_id'], tenant=tenant, is_active=True)
            except Staff.DoesNotExist:
                raise serializers.ValidationError({'staff_id': 'Empleado no encontrado o inactivo.'})
        data['staff'] = staff

        # ── Fecha no en el pasado ─────────────────────────
        if data['date'] < timezone.now().date():
            raise serializers.ValidationError({'date': 'No puedes reservar en fechas pasadas.'})

        # ── Calcular end_time (necesario para el overlap check) ──
        start_dt        = datetime.combine(data['date'], data['start_time'])
        data['end_time'] = (start_dt + timedelta(minutes=service.duration)).time()

        # ── Verificar que el slot no esté ocupado ─────────
        overlap_qs = Booking.objects.filter(
            tenant=tenant,
            date=data['date'],
            status__in=['pending', 'confirmed'],
        ).exclude(
            end_time__lte=data['start_time']
        ).exclude(
            start_time__gte=data['end_time']
        )
        if staff:
            overlap_qs = overlap_qs.filter(staff=staff)

        if overlap_qs.exists():
            raise serializers.ValidationError(
                'Este horario no está disponible. Por favor elige otro.'
            )

        return data

    def create(self, validated_data):
        tenant = self.context['tenant']

        # Obtener o crear el cliente por teléfono dentro del tenant
        customer, _ = Customer.objects.get_or_create(
            tenant=tenant,
            phone=validated_data['customer_phone'],
            defaults={
                'name':  validated_data['customer_name'],
                'email': validated_data.get('customer_email', ''),
            },
        )
        # Actualizar nombre si el cliente vuelve a reservar con uno diferente
        if customer.name != validated_data['customer_name']:
            customer.name = validated_data['customer_name']
            customer.save(update_fields=['name'])

        # end_time lo calculará Booking.save() automáticamente,
        # pero lo pasamos igual para consistencia con el overlap check.
        return Booking.objects.create(
            tenant=tenant,
            customer=customer,
            service=validated_data['service'],
            staff=validated_data.get('staff'),
            date=validated_data['date'],
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],   # sobreescrito por model.save()
            notes=validated_data.get('notes', ''),
        )


class BookingStatusSerializer(serializers.ModelSerializer):
    """
    Usado por el dueño del negocio para cambiar el estado de una reserva.
    """
    VALID_STATUSES = {s[0] for s in Booking.STATUS}

    class Meta:
        model  = Booking
        fields = ['status', 'notes', 'staff']

    def validate_status(self, value):
        if value not in self.VALID_STATUSES:
            raise serializers.ValidationError(
                f'Estado inválido. Opciones: {", ".join(self.VALID_STATUSES)}'
            )
        return value
