from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Contract


class DashboardApiTests(TestCase):
    """Минимальные smoke-тесты API дашборда.

    Цель тестов — подтвердить, что основные JSON-endpoints открываются,
    возвращают ожидаемую структуру и не падают на типовых данных.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='ivanov',
            first_name='Иван',
            last_name='Иванов',
            password='test-password',
        )
        now = timezone.now()
        Contract.objects.create(
            contract_number='Д-2026-0001',
            counterparty='ООО Ромашка',
            contract_type=Contract.ContractType.SUPPLY,
            status=Contract.Status.SIGNED,
            responsible_user=self.user,
            created_at=now - timedelta(days=10),
            signed_at=now - timedelta(days=2),
        )
        Contract.objects.create(
            contract_number='Д-2026-0002',
            counterparty='АО Вектор',
            contract_type=Contract.ContractType.SERVICES,
            status=Contract.Status.LAWYER_APPROVAL,
            responsible_user=self.user,
            created_at=now - timedelta(days=20),
        )
        Contract.objects.create(
            contract_number='Д-2026-0003',
            counterparty='ИП Сидоров',
            contract_type=Contract.ContractType.RENT,
            status=Contract.Status.DRAFT,
            responsible_user=self.user,
            created_at=now - timedelta(days=1),
        )

    def test_kpi_endpoint_returns_expected_values(self):
        response = self.client.get(reverse('dashboard:kpi_cards'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['on_approval'], 1)
        self.assertEqual(data['overdue'], 1)
        self.assertGreater(data['avg_days'], 0)

    def test_funnel_endpoint_contains_all_statuses(self):
        response = self.client.get(reverse('dashboard:approval_funnel'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {'labels', 'counts', 'colors'})
        self.assertEqual(len(data['labels']), len(Contract.Status.choices))
        self.assertEqual(sum(data['counts']), 3)

    def test_monthly_dynamics_has_12_unique_months(self):
        response = self.client.get(reverse('dashboard:monthly_dynamics'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['labels']), 12)
        self.assertEqual(len(set(data['labels'])), 12)
        self.assertEqual(len(data['created']), 12)
        self.assertEqual(len(data['signed']), 12)

    def test_contract_types_endpoint_returns_type_distribution(self):
        response = self.client.get(reverse('dashboard:contract_types'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {'labels', 'counts', 'colors'})
        self.assertEqual(sum(data['counts']), 3)

    def test_slowest_endpoint_returns_pending_contracts(self):
        response = self.client.get(reverse('dashboard:slowest_contracts'))

        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['number'], 'Д-2026-0002')
        self.assertIn('Иванов', data[0]['responsible'])
