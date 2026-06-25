from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Главная страница дашборда
    path('', views.dashboard_page, name='dashboard_page'),
    
    # API endpoints для графиков
    path('api/kpi/', views.kpi_cards, name='kpi_cards'),
    path('api/funnel/', views.approval_funnel, name='approval_funnel'),
    path('api/dynamics/', views.monthly_dynamics, name='monthly_dynamics'),
    path('api/types/', views.contract_types, name='contract_types'),
    path('api/slowest/', views.slowest_contracts, name='slowest_contracts'),
]