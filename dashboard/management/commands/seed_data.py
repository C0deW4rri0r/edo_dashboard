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
            days_ago = random.randint(0, 365)
            created_date = timezone.now() - timedelta(days=days_ago)
            status = random.choices(statuses, weights=status_weights)[0]
            
            contract = Contract(
                contract_number=f"Д-{created_date.year}-{i+1:04d}",
                counterparty=fake.company(),
                contract_type=random.choice(contract_types),
                status=status,
                responsible_user=random.choice(users),
                created_at=created_date,
            )
            
            if status == Contract.Status.SIGNED:
                signing_days = random.randint(5, 30)
                contract.signed_at = created_date + timedelta(days=signing_days)
            
            contracts.append(contract)
        
        Contract.objects.bulk_create(contracts)
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(contracts)} договоров'))
        
        # 4. Генерируем историю статусов (ЦЕЛЬ: 1200-1800 записей)
        self.stdout.write('Генерирую историю статусов...')
        history_records = []
        
        all_contracts = Contract.objects.all()
        
        for contract in all_contracts:
            # 🆕 Увеличиваем количество записей: от 4 до 7 на договор
            # Это даст 300 × 5 (среднее) = 1500 записей
            num_changes = random.randint(4, 7)
            
            # Определяем конечную дату для истории
            end_date = contract.signed_at if contract.signed_at else timezone.now()
            start_date = contract.created_at
            
            # Проверяем временной диапазон
            if start_date >= end_date:
                # Создаем хотя бы одну запись
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
            
            # 🆕 Определяем реальную цепочку статусов для этого договора
            status_chain = self._build_status_chain(contract.status, num_changes)
            
            # Генерируем записи истории по цепочке
            for j, (old_status, new_status) in enumerate(status_chain):
                # Равномерно распределяем изменения по времени
                change_day = int((j + 1) * days_diff / (len(status_chain) + 1))
                change_date = start_date + timedelta(days=change_day)
                
                # Добавляем случайные часы/минуты для реалистичности
                change_date = change_date + timedelta(
                    hours=random.randint(9, 18),  # Рабочие часы 9-18
                    minutes=random.randint(0, 59)
                )
                
                # Убеждаемся, что дата не выходит за пределы
                if change_date > end_date:
                    change_date = end_date - timedelta(hours=1)
                
                history = ContractStatusHistory(
                    contract=contract,
                    old_status=old_status,
                    new_status=new_status,
                    changed_at=change_date,
                    changed_by=random.choice(users)
                )
                history_records.append(history)
        
        # Массовое создание истории
        ContractStatusHistory.objects.bulk_create(history_records)
        self.stdout.write(self.style.SUCCESS(f'✓ Создано {len(history_records)} записей истории'))
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Генерация завершена!'))
        self.stdout.write(f'Всего договоров: {Contract.objects.count()}')
        self.stdout.write(f'Всего записей истории: {ContractStatusHistory.objects.count()}')

    def _build_status_chain(self, final_status, max_changes):
        """
        Строит реалистичную цепочку переходов статусов для договора.
        Возвращает список кортежей (old_status, new_status).
        """
        chain = []
        current = Contract.Status.DRAFT
        
        # Базовая прогрессия статусов
        progressions = {
            Contract.Status.DRAFT: [Contract.Status.LAWYER_APPROVAL],
            Contract.Status.LAWYER_APPROVAL: [
                Contract.Status.ACCOUNTANT_APPROVAL,  # Успех
                Contract.Status.DRAFT,  # Возврат на доработку (реалистично!)
            ],
            Contract.Status.ACCOUNTANT_APPROVAL: [
                Contract.Status.SIGNING,  # Успех
                Contract.Status.LAWYER_APPROVAL,  # Возврат (реалистично!)
            ],
            Contract.Status.SIGNING: [
                Contract.Status.SIGNED,  # Успех
                Contract.Status.ACCOUNTANT_APPROVAL,  # Возврат (реалистично!)
            ],
            Contract.Status.SIGNED: [],
            Contract.Status.REJECTED: [],
        }
        
        # Вероятности возвратов (чем дальше в процессе, тем реже возвраты)
        rollback_probs = {
            Contract.Status.LAWYER_APPROVAL: 0.3,      # 30% шанс возврата
            Contract.Status.ACCOUNTANT_APPROVAL: 0.2,  # 20% шанс возврата
            Contract.Status.SIGNING: 0.1,              # 10% шанс возврата
        }
        
        for _ in range(max_changes):
            possible_next = progressions.get(current, [])
            if not possible_next:
                break
            
            # Определяем, будет ли возврат
            if current in rollback_probs and random.random() < rollback_probs[current]:
                # Возврат на предыдущий этап
                next_status = possible_next[-1]  # Последний вариант = возврат
            else:
                # Прогресс вперед
                next_status = possible_next[0]  # Первый вариант = прогресс
            
            chain.append((current, next_status))
            current = next_status
            
            # Если достигли финального статуса — останавливаемся
            if current in [Contract.Status.SIGNED, Contract.Status.REJECTED]:
                break
        
        # 🆕 Если финальный статус договора не совпадает с цепочкой — добавляем переход
        if chain and chain[-1][1] != final_status:
            chain.append((chain[-1][1], final_status))
        
        # Если цепочка пустая — добавляем хотя бы один переход
        if not chain:
            chain.append((Contract.Status.DRAFT, final_status))
        
        return chain

    def _get_next_statuses(self, current_status):
        """Старый метод — оставляем для совместимости"""
        transitions = {
            Contract.Status.DRAFT: [Contract.Status.LAWYER_APPROVAL],
            Contract.Status.LAWYER_APPROVAL: [Contract.Status.ACCOUNTANT_APPROVAL, Contract.Status.REJECTED],
            Contract.Status.ACCOUNTANT_APPROVAL: [Contract.Status.SIGNING, Contract.Status.REJECTED],
            Contract.Status.SIGNING: [Contract.Status.SIGNED, Contract.Status.REJECTED],
            Contract.Status.SIGNED: [],
            Contract.Status.REJECTED: [],
        }
        return transitions.get(current_status, [])
    
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