"""
Limpia datos de prueba sucios antes de mostrar a clientes reales.
Uso: python manage.py cleanup_test_data
"""
from django.core.management.base import BaseCommand
from bookings_saas.bookings.models import Booking
from bookings_saas.services.models import Service

TEST_SERVICE_KEYWORDS = ['asd', 'test', 'prueba', 'xxx', 'asdf', '123', 'qwerty']
TEST_BOOKING_NAMES    = ['chupetin', 'test', 'prueba', 'asdasd', 'juan prueba', 'demo']
TEST_BOOKING_PHONES   = ['999999999', '000000000', '111111111', '123456789']


class Command(BaseCommand):
    help = 'Elimina servicios y reservas de prueba'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra qué se eliminaría, sin borrar nada')

    def handle(self, *args, **options):
        dry = options['dry_run']
        mode = '[DRY RUN] ' if dry else ''

        # ── Servicios de prueba ───────────────────────────────────────
        self.stdout.write('\n=== SERVICIOS DE PRUEBA ===')
        from django.db.models import Q
        svc_q = Q()
        for kw in TEST_SERVICE_KEYWORDS:
            svc_q |= Q(name__icontains=kw)
        bad_svcs = Service.objects.filter(svc_q)

        if not bad_svcs.exists():
            self.stdout.write('  Ninguno encontrado.')
        else:
            for s in bad_svcs:
                self.stdout.write(f'  {mode}ELIMINAR servicio [{s.id}] "{s.name}" — {s.tenant.name}')
            if not dry:
                count = bad_svcs.count()
                bad_svcs.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ {count} servicio(s) eliminado(s)'))

        # ── Reservas de prueba ────────────────────────────────────────
        self.stdout.write('\n=== RESERVAS DE PRUEBA ===')
        bk_q = Q()
        for name in TEST_BOOKING_NAMES:
            bk_q |= Q(customer_name__icontains=name)
        for phone in TEST_BOOKING_PHONES:
            bk_q |= Q(customer_phone__icontains=phone)
        bad_bks = Booking.objects.filter(bk_q)

        if not bad_bks.exists():
            self.stdout.write('  Ninguna encontrada.')
        else:
            for b in bad_bks:
                svc = getattr(b, 'service', None)
                svc_name = svc.name if svc else '—'
                self.stdout.write(
                    f'  {mode}ELIMINAR reserva [{b.id}] "{b.customer_name}" '
                    f'{b.date} {b.start_time} {svc_name} — {b.tenant.name}'
                )
            if not dry:
                count = bad_bks.count()
                bad_bks.delete()
                self.stdout.write(self.style.SUCCESS(f'  ✓ {count} reserva(s) eliminada(s)'))

        self.stdout.write(self.style.SUCCESS('\n✓ Limpieza completada'))
