from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Contract(models.Model):
    """Модель Договора"""
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Черновик'
        LAWYER_APPROVAL = 'LAWYER', 'На согласовании у юриста'
        ACCOUNTANT_APPROVAL = 'ACCOUNTANT', 'На согласовании у бухгалтера'
        SIGNING = 'SIGNING', 'На подписании'
        SIGNED = 'SIGNED', 'Подписан'
        REJECTED = 'REJECTED', 'Отклонен'

    class ContractType(models.TextChoices):
        SUPPLY = 'SUPPLY', 'Поставка'
        SERVICES = 'SERVICES', 'Услуги'
        RENT = 'RENT', 'Аренда'
        NDA = 'NDA', 'NDA'
        OTHER = 'OTHER', 'Другое'

    # Основные поля
    contract_number = models.CharField(max_length=50, unique=True, verbose_name="Номер договора")
    counterparty = models.CharField(max_length=255, verbose_name="Контрагент")
    contract_type = models.CharField(
        max_length=20, 
        choices=ContractType.choices, 
        default=ContractType.OTHER,
        verbose_name="Тип договора"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT,
        verbose_name="Статус"
    )
    
    # Ответственные и даты
    responsible_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='contracts',
        verbose_name="Ответственный"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    signed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата подписания")

    class Meta:
        verbose_name = "Договор"
        verbose_name_plural = "Договоры"
        ordering = ['-created_at']
        # ИНДЕКСЫ для ускорения выборок (Требование ТЗ по производительности)
        indexes = [
            models.Index(fields=['status'], name='idx_status'),
            models.Index(fields=['created_at'], name='idx_created_at'),
            models.Index(fields=['contract_type'], name='idx_contract_type'),
        ]

    def __str__(self):
        return f"Договор {self.contract_number} ({self.counterparty})"


class ContractStatusHistory(models.Model):
    """Модель Истории изменений статусов (для аналитики и аудита)"""
    contract = models.ForeignKey(
        Contract, 
        on_delete=models.CASCADE, 
        related_name='history',
        verbose_name="Договор"
    )
    old_status = models.CharField(max_length=20, choices=Contract.Status.choices, verbose_name="Старый статус")
    new_status = models.CharField(max_length=20, choices=Contract.Status.choices, verbose_name="Новый статус")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата изменения")
    changed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Кто изменил"
    )

    class Meta:
        verbose_name = "История статусов"
        verbose_name_plural = "История статусов"
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.contract.contract_number}: {self.old_status} -> {self.new_status}"