from django.contrib import admin
from .models import Contract, ContractStatusHistory

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """Админка для модели Договора"""
    list_display = ('contract_number', 'counterparty', 'contract_type', 'status', 'responsible_user', 'created_at', 'signed_at')
    list_filter = ('status', 'contract_type', 'created_at')
    search_fields = ('contract_number', 'counterparty')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('contract_number', 'counterparty', 'contract_type', 'status')
        }),
        ('Ответственные и даты', {
            'fields': ('responsible_user', 'created_at', 'signed_at')
        }),
    )

@admin.register(ContractStatusHistory)
class ContractStatusHistoryAdmin(admin.ModelAdmin):
    """Админка для модели Истории статусов"""
    list_display = ('contract', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'changed_at')
    search_fields = ('contract__contract_number', 'contract__counterparty')
    date_hierarchy = 'changed_at'
    readonly_fields = ('changed_at',)