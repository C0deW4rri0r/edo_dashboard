import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from faker import Faker
from dashboard.models import Contract, ContractStatusHistory

fake = Faker('ru_RU')

class Command(BaseCommand):
    help = 'Генерация тестовых данных для дашборда'

    def handle(self, *args, **kwargs):
        self.stdout.write('Начинаю генерацию тестовых данных...')
        
        # 1. Создаем пользователей
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
        
        # 3. Генерируем 300 договоров
        self.stdout.write('Генерирую договоры...')
        contracts = []
        contract_types = [ctype[0] for ctype in Contract.ContractType.choices]

        now = timezone.now()

        for i in range(300):
            days_ago = random.randint(0, 365)
            created_date = now - timedelta(days=days_ago)
            
            # РЕАЛИСТИЧНОЕ распределение статусов
            if days_ago > 60:
                # Старые договоры (>60 дней) - большинство уже подписаны или отклонены
                # Но некоторые зависли на разных этапах
                status_choice = random.choices(
                    [Contract.Status.SIGNED, Contract.Status.REJECTED, 
                    Contract.Status.LAWYER_APPROVAL, Contract.Status.ACCOUNTANT_APPROVAL, 
                    Contract.Status.SIGNING, Contract.Status.DRAFT],
                    weights=[0.65, 0.20, 0.05, 0.05, 0.03, 0.02]
                )[0]
            elif days_ago > 14:
                # Средний возраст (14-60 дней) - создаем ПРОСРОЧЕННЫЕ на разных этапах
                # Здесь должно быть больше зависших на разных стадиях
                status_choice = random.choices(
                    [Contract.Status.SIGNED, Contract.Status.REJECTED, 
                    Contract.Status.LAWYER_APPROVAL, Contract.Status.ACCOUNTANT_APPROVAL, 
                    Contract.Status.SIGNING, Contract.Status.DRAFT],
                    weights=[0.50, 0.15, 0.10, 0.10, 0.10, 0.05]
                )[0]
            else:
                # Новые договоры (<14 дней) - чаще в процессе, много черновиков
                status_choice = random.choices(
                    [Contract.Status.DRAFT, Contract.Status.LAWYER_APPROVAL, 
                    Contract.Status.ACCOUNTANT_APPROVAL, Contract.Status.SIGNING,
                    Contract.Status.SIGNED, Contract.Status.REJECTED],
                    weights=[0.20, 0.30, 0.20, 0.15, 0.10, 0.05]
                )[0]
            
            contract = Contract(
                contract_number=f"Д-{created_date.year}-{i+1:04d}",
                counterparty=fake.company(),
                contract_type=random.choice(contract_types),
                status=status_choice,
                responsible_user=random.choice(users),
                created_at=created_date,
            )
            
            # Если договор подписан - устанавливаем дату подписания
            if status_choice == Contract.Status.SIGNED:
                signing_days = random.randint(3, 25)
                signed_date = created_date + timedelta(days=signing_days)
                
                if signed_date <= now:
                    contract.signed_at = signed_date
                else:
                    contract.status = Contract.Status.SIGNING
            
            contracts.append(contract)

        Contract.objects.bulk_create(contracts)
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(contracts)} договоров'))
        
        # 4. Генерируем историю статусов
        self.stdout.write('Генерирую историю статусов...')
        history_records = []

        all_contracts = Contract.objects.all()
        self.stdout.write(f'Найдено договоров в БД: {all_contracts.count()}')

        for idx, contract in enumerate(all_contracts):
            # Определяем количество записей истории в зависимости от статуса
            if contract.status == Contract.Status.DRAFT:
                num_records = 1  # Черновик - только одна запись
            elif contract.status in [Contract.Status.LAWYER_APPROVAL, Contract.Status.ACCOUNTANT_APPROVAL]:
                num_records = random.randint(2, 3)  # На согласовании - 2-3 записи
            elif contract.status == Contract.Status.SIGNING:
                num_records = random.randint(3, 4)  # На подписании - 3-4 записи
            elif contract.status in [Contract.Status.SIGNED, Contract.Status.REJECTED]:
                num_records = random.randint(4, 6)  # Завершенные - 4-6 записей
            else:
                num_records = random.randint(2, 4)
            
            # Определяем временной диапазон
            if contract.signed_at:
                end_date = contract.signed_at
            else:
                end_date = now
            
            start_date = contract.created_at
            days_diff = (end_date - start_date).days
            
            if days_diff < 1:
                days_diff = 1
            
            # Создаём записи истории
            for j in range(num_records):
                if num_records == 1:
                    change_date = start_date + timedelta(days=days_diff // 2)
                else:
                    change_date = start_date + timedelta(days=int((j + 1) * days_diff / (num_records + 1)))
                
                change_date = change_date.replace(
                    hour=random.randint(9, 18),
                    minute=random.randint(0, 59),
                    second=0
                )
                
                # Определяем статусы для этой записи
                if j == 0:
                    old_status = Contract.Status.DRAFT
                else:
                    # Берём предыдущий статус из уже созданных записей для этого договора
                    prev_records = [r for r in history_records if r.contract == contract]
                    old_status = prev_records[-1].new_status if prev_records else Contract.Status.DRAFT
                
                # Определяем новый статус
                if j == num_records - 1:
                    new_status = contract.status
                else:
                    # Промежуточные статусы - прогрессия
                    if old_status == Contract.Status.DRAFT:
                        new_status = Contract.Status.LAWYER_APPROVAL
                    elif old_status == Contract.Status.LAWYER_APPROVAL:
                        new_status = Contract.Status.ACCOUNTANT_APPROVAL
                    elif old_status == Contract.Status.ACCOUNTANT_APPROVAL:
                        new_status = Contract.Status.SIGNING
                    elif old_status == Contract.Status.SIGNING:
                        new_status = contract.status
                    else:
                        new_status = contract.status
                
                history = ContractStatusHistory(
                    contract=contract,
                    old_status=old_status,
                    new_status=new_status,
                    changed_at=change_date,
                    changed_by=random.choice(users)
                )
                history_records.append(history)
            
            # Отладочный вывод для первых 5 договоров
            if idx < 5:
                self.stdout.write(f'  Договор {contract.contract_number} ({contract.get_status_display()}): создано {num_records} записей истории')

        ContractStatusHistory.objects.bulk_create(history_records)
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(history_records)} записей истории'))
        
        # 5. Статистика
        overdue_count = Contract.objects.filter(
            created_at__lt=now - timedelta(days=14),
            status__in=[
                Contract.Status.LAWYER_APPROVAL,
                Contract.Status.ACCOUNTANT_APPROVAL,
                Contract.Status.SIGNING
            ]
        ).count()
        
        signed_count = Contract.objects.filter(status=Contract.Status.SIGNED).count()
        
        # Отладка: проверяем просроченные договоры
        overdue_contracts = Contract.objects.filter(
            created_at__lt=now - timedelta(days=14),
            status__in=[
                Contract.Status.LAWYER_APPROVAL,
                Contract.Status.ACCOUNTANT_APPROVAL,
                Contract.Status.SIGNING
            ]
        )
        self.stdout.write(f'\nОтладка просроченных:')
        self.stdout.write(f'  Всего договоров: {Contract.objects.count()}')
        self.stdout.write(f'  Договоров старше 14 дней: {Contract.objects.filter(created_at__lt=now - timedelta(days=14)).count()}')
        self.stdout.write(f'  Договоров в процессе согласования: {Contract.objects.filter(status__in=[Contract.Status.LAWYER_APPROVAL, Contract.Status.ACCOUNTANT_APPROVAL, Contract.Status.SIGNING]).count()}')
        self.stdout.write(f'  Просроченных (оба условия): {overdue_count}')
        if overdue_count > 0:
            self.stdout.write(f'  Примеры просроченных:')
            for c in overdue_contracts[:3]:
                self.stdout.write(f'    - {c.contract_number}: создан {c.created_at}, статус {c.status}')
        
        self.stdout.write(self.style.SUCCESS(f'\n Генерация завершена!'))
        self.stdout.write(f'Всего договоров: {Contract.objects.count()}')
        self.stdout.write(f'Подписанных: {signed_count}')
        self.stdout.write(f'Просроченных: {overdue_count}')
        self.stdout.write(f'Всего записей истории: {ContractStatusHistory.objects.count()}')