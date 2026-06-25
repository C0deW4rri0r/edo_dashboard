import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from faker import Faker
from dashboard.models import Contract, ContractStatusHistory

fake = Faker('ru_RU')  # Русская локализация для реалистичных данных

class Command(BaseCommand):
    help = 'Генерация тестовых данных для дашборда'

    def handle(self, *args, **kwargs):
        self.stdout.write('Начинаю генерацию тестовых данных...')
        
        # 1. Создаем пользователей (25 человек)
        self.stdout.write('Создаю пользователей...')
        users = []
        for i in range(25):
            username = f"user_{i+1}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'email': f"{username}@example.com",
                    'is_active': True
                }
            )
            users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(users)} пользователей'))
        
        # 2. Очищаем старые данные
        Contract.objects.all().delete()
        ContractStatusHistory.objects.all().delete()
        
        # 3. Генерируем 300 договоров за последние 12 месяцев
        self.stdout.write('Генерирую договоры...')
        contracts = []
        statuses = [status[0] for status in Contract.Status.choices]
        contract_types = [ctype[0] for ctype in Contract.ContractType.choices]
        
        # Веса для распределения статусов
        status_weights = [0.1, 0.15, 0.15, 0.1, 0.4, 0.1]
        
        for i in range(300):
            # Случайная дата за последние 12 месяцев
            days_ago = random.randint(0, 365)
            created_date = timezone.now() - timedelta(days=days_ago)
            
            # Выбираем статус с учетом весов
            status = random.choices(statuses, weights=status_weights)[0]
            
            contract = Contract(
                contract_number=f"Д-{created_date.year}-{i+1:04d}",
                counterparty=fake.company(),
                contract_type=random.choice(contract_types),
                status=status,
                responsible_user=random.choice(users),
                created_at=created_date,
            )
            
            # Если договор подписан, устанавливаем дату подписания
            if status == Contract.Status.SIGNED:
                # Подписан через 5-30 дней после создания
                signing_days = random.randint(5, 30)
                contract.signed_at = created_date + timedelta(days=signing_days)
            
            contracts.append(contract)
        
        # Массовое создание (быстрее)
        Contract.objects.bulk_create(contracts)
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(contracts)} договоров'))
        
        # 4. Генерируем историю статусов (500+ записей)
        self.stdout.write('Генерирую историю статусов...')
        history_records = []
        
        # Получаем все договоры из БД (после bulk_create они там есть)
        all_contracts = Contract.objects.all()
        
        for contract in all_contracts:
            # Для каждого договора создаем 2-4 записи истории
            num_changes = random.randint(2, 4)
            current_status = Contract.Status.DRAFT
            
            # Определяем конечную дату для истории
            end_date = contract.signed_at if contract.signed_at else timezone.now()
            start_date = contract.created_at
            
            # Проверяем, что есть временной диапазон
            if start_date >= end_date:
                # Если даты равны или start > end, добавляем хотя бы одну запись
                history = ContractStatusHistory(
                    contract=contract,
                    old_status=Contract.Status.DRAFT,
                    new_status=contract.status,
                    changed_at=start_date + timedelta(minutes=1),
                    changed_by=random.choice(users)
                )
                history_records.append(history)
                continue
            
            days_diff = (end_date - start_date).days
            if days_diff < 1:
                days_diff = 1
            
            # Генерируем записи истории с равномерным распределением по времени
            for j in range(num_changes):
                # Выбираем следующий статус
                possible_next = self._get_next_statuses(current_status)
                if not possible_next:
                    break
                
                next_status = random.choice(possible_next)
                
                # Равномерно распределяем изменения по временному диапазону
                change_day = int((j + 1) * days_diff / (num_changes + 1))
                change_date = start_date + timedelta(days=change_day)
                
                # Добавляем случайные часы для реалистичности
                change_date = change_date + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                history = ContractStatusHistory(
                    contract=contract,
                    old_status=current_status,
                    new_status=next_status,
                    changed_at=change_date,
                    changed_by=random.choice(users)
                )
                history_records.append(history)
                
                current_status = next_status
                if current_status in [Contract.Status.SIGNED, Contract.Status.REJECTED]:
                    break
        
        # Массовое создание истории
        ContractStatusHistory.objects.bulk_create(history_records)
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(history_records)} записей истории'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Генерация завершена!'))
        self.stdout.write(f'Всего договоров: {Contract.objects.count()}')
        self.stdout.write(f'Всего записей истории: {ContractStatusHistory.objects.count()}')
    
    def _get_next_statuses(self, current_status):
        """Возвращает возможные следующие статусы"""
        transitions = {
            Contract.Status.DRAFT: [Contract.Status.LAWYER_APPROVAL],
            Contract.Status.LAWYER_APPROVAL: [Contract.Status.ACCOUNTANT_APPROVAL, Contract.Status.REJECTED],
            Contract.Status.ACCOUNTANT_APPROVAL: [Contract.Status.SIGNING, Contract.Status.REJECTED],
            Contract.Status.SIGNING: [Contract.Status.SIGNED, Contract.Status.REJECTED],
            Contract.Status.SIGNED: [],
            Contract.Status.REJECTED: [],
        }
        return transitions.get(current_status, [])