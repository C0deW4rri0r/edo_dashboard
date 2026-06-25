from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from .models import Contract

def dashboard_page(request):
    """Рендеринг HTML-шаблона дашборда"""
    return render(request, 'dashboard/dashboard.html')

def kpi_cards(request):
    """API: 4 KPI-карточки"""
    total = Contract.objects.count()
    
    # На согласовании (юрист, бухгалтер, подписание)
    approval_statuses = [
        Contract.Status.LAWYER_APPROVAL, 
        Contract.Status.ACCOUNTANT_APPROVAL, 
        Contract.Status.SIGNING
    ]
    on_approval = Contract.objects.filter(status__in=approval_statuses).count()
    
    # Просроченные: созданы > 14 дней назад, но еще не подписаны и не отклонены
    deadline = timezone.now() - timedelta(days=14)
    overdue = Contract.objects.filter(
        created_at__lt=deadline,
        status__in=approval_statuses
    ).count()
    
    # Среднее время согласования (только для подписанных)
    # Фильтруем только договоры, где signed_at >= created_at (исключаем аномалии)
    avg_duration = Contract.objects.filter(
        status=Contract.Status.SIGNED,
        signed_at__isnull=False
    ).exclude(
        signed_at__lt=F('created_at')  # Исключаем договоры, где дата подписания раньше создания
    ).annotate(
        duration=ExpressionWrapper(F('signed_at') - F('created_at'), output_field=DurationField())
    ).filter(
        duration__gte=timedelta(days=0)  # Дополнительная фильтрация только положительных значений
    ).aggregate(avg=Avg('duration'))['avg']

    # Переводим timedelta в дни (float)
    avg_days = round(avg_duration.total_seconds() / 86400, 1) if avg_duration else 0
    
    return JsonResponse({
        'total': total,
        'on_approval': on_approval,
        'overdue': overdue,
        'avg_days': avg_days
    })

def approval_funnel(request):
    """API: Воронка согласования (количество по статусам)"""
    # Получаем количество договоров по каждому статусу
    funnel_data = Contract.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Преобразуем в удобный для JS формат
    labels = []
    counts = []
    colors = {
        'DRAFT': '#6c757d',      # Серый
        'LAWYER': '#ffc107',     # Желтый
        'ACCOUNTANT': '#17a2b8', # Голубой
        'SIGNING': '#007bff',    # Синий
        'SIGNED': '#28a745',     # Зеленый
        'REJECTED': '#dc3545'    # Красный
    }
    
    # Получаем все статусы из модели, чтобы не потерять те, где 0 договоров
    all_statuses = dict(Contract.Status.choices)
    
    # Создаем словарь с результатами
    result_dict = {item['status']: item['count'] for item in funnel_data}
    
    for status_code, status_name in all_statuses.items():
        labels.append(status_name)
        counts.append(result_dict.get(status_code, 0))
    
    return JsonResponse({
        'labels': labels,
        'counts': counts,
        'colors': [colors.get(code, '#6c757d') for code in all_statuses.keys()]
    })

def monthly_dynamics(request):
    """API: Динамика по месяцам (создано / подписано за 12 месяцев)"""
    # Группируем по месяцам для созданных договоров
    created_by_month = Contract.objects.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Группируем по месяцам для подписанных договоров
    signed_by_month = Contract.objects.filter(
        signed_at__isnull=False
    ).annotate(
        month=TruncMonth('signed_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Преобразуем в словари для удобного объединения
    created_dict = {item['month'].strftime('%Y-%m'): item['count'] for item in created_by_month}
    signed_dict = {item['month'].strftime('%Y-%m'): item['count'] for item in signed_by_month}
    
    # Генерируем последние 12 месяцев
    labels = []
    created_counts = []
    signed_counts = []
    
    for i in range(11, -1, -1):
        date = timezone.now() - timedelta(days=i*30)
        month_str = date.strftime('%Y-%m')
        month_label = date.strftime('%b %Y')  # Например: "Jan 2024"
        
        labels.append(month_label)
        created_counts.append(created_dict.get(month_str, 0))
        signed_counts.append(signed_dict.get(month_str, 0))
    
    return JsonResponse({
        'labels': labels,
        'created': created_counts,
        'signed': signed_counts
    })

def contract_types(request):
    """API: Распределение по типам договоров"""
    types_data = Contract.objects.values('contract_type').annotate(
        count=Count('id')
    ).order_by('contract_type')
    
    labels = []
    counts = []
    colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6c757d', '#17a2b8']
    
    all_types = dict(Contract.ContractType.choices)
    result_dict = {item['contract_type']: item['count'] for item in types_data}
    
    for type_code, type_name in all_types.items():
        labels.append(type_name)
        counts.append(result_dict.get(type_code, 0))
    
    return JsonResponse({
        'labels': labels,
        'counts': counts,
        'colors': colors[:len(labels)]
    })

def slowest_contracts(request):
    """API: Топ-5 самых медленных согласований"""
    slowest = Contract.objects.filter(
        status=Contract.Status.SIGNED,
        signed_at__isnull=False
    ).annotate(
        duration_days=ExpressionWrapper(
            F('signed_at') - F('created_at'), 
            output_field=DurationField()
        )
    ).order_by('-duration_days')[:5]
    
    data = []
    for contract in slowest:
        days = contract.duration_days.total_seconds() / 86400
        data.append({
            'number': contract.contract_number,
            'counterparty': contract.counterparty,
            'status': contract.get_status_display(),
            'responsible': f"{contract.responsible_user.first_name} {contract.responsible_user.last_name}" if contract.responsible_user else 'Не указан',
            'days': round(days, 1)
        })
    
    return JsonResponse({'data': data})