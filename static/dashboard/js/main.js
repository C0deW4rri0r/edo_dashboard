/**
 * ========================================
 * Аналитический дашборд ЭДО - Main JavaScript
 * ========================================
 * 
 * Этот файл содержит всю клиентскую логику для:
 * - Загрузки данных с бэкенда через Fetch API
 * - Отрисовки интерактивных графиков с Chart.js
 * - Управления KPI-карточками
 * - Автообновления данных
 */

// ========================================
// Глобальные переменные для хранения экземпляров графиков
// ========================================
let funnelChart = null;      // График воронки согласования
let dynamicsChart = null;    // График динамики по месяцам
let typesChart = null;       // Круговая диаграмма типов договоров

// ========================================
// Инициализация при загрузке страницы
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Дашборд инициализирован');

    // Инициализация Bootstrap tooltips для KPI-карточек
    initializeTooltips();

    // Загружаем все данные при первом открытии страницы
    loadAllData();

    // Настраиваем автообновление каждые 60 секунд (требование ТЗ)
    setInterval(loadAllData, 60000);
    console.log('⏱️ Автообновление настроено: каждые 60 секунд');

    // Добавляем обработчики для анимации иконки обновления
    setupRefreshButtonAnimation();
});

/**
 * ========================================
 * Загрузка всех данных параллельно
 * ========================================
 * Используем Promise.all() для одновременной загрузки всех API endpoints
 * Это ускоряет загрузку страницы в ~5 раз по сравнению с последовательными запросами
 */
async function loadAllData() {
    console.log('📊 Начинаю загрузку всех данных...');

    await Promise.all([
        loadKpiCards(),
        loadFunnelChart(),
        loadDynamicsChart(),
        loadTypesChart(),
        loadSlowestContracts()
    ]);

    console.log('✅ Все данные загружены');
}

/**
 * ========================================
 * Обработчик кнопки "Обновить данные"
 * ========================================
 * Просто загружает данные без анимации вращения
 */
async function refreshAllData() {
    console.log('🔄 Ручное обновление данных...');

    // Загружаем все данные
    await loadAllData();

    console.log('✅ Данные обновлены вручную');
}

/**
 * ========================================
 * Загрузка KPI-карточек
 * ========================================
 * API endpoint: /api/kpi/
 * Возвращает 4 метрики:
 * - total: общее количество договоров
 * - on_approval: количество на согласовании
 * - overdue: количество просроченных
 * - avg_days: среднее время согласования
 */
async function loadKpiCards() {
    try {
        const response = await fetch('/api/kpi/');

        // Проверяем статус ответа
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Обновляем DOM с полученными значениями
        document.getElementById('kpi-total').textContent = data.total;
        document.getElementById('kpi-approval').textContent = data.on_approval;
        document.getElementById('kpi-overdue').textContent = data.overdue;
        document.getElementById('kpi-avg-days').textContent = data.avg_days;

        console.log('📈 KPI карточки обновлены:', data);

    } catch (error) {
        // Обработка ошибок (требование ТЗ по надежности)
        console.error('❌ Ошибка загрузки KPI:', error);
        showErrorNotification('Не удалось загрузить KPI данные');
    }
}

/**
 * ========================================
 * Загрузка и отрисовка воронки согласования
 * ========================================
 * API endpoint: /api/funnel/
 * Тип графика: Bar Chart (вертикальные столбцы)
 * Отображает количество договоров на каждом этапе согласования
 */
async function loadFunnelChart() {
    try {
        const response = await fetch('/api/funnel/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Получаем контекст canvas для отрисовки графика
        const ctx = document.getElementById('funnelChart').getContext('2d');

        // Уничтожаем предыдущий экземпляр графика (если есть)
        // Это необходимо для корректного обновления данных
        if (funnelChart) {
            funnelChart.destroy();
        }

        // Создаем новый график с настройками
        funnelChart = new Chart(ctx, {
            type: 'bar',  // Тип: вертикальные столбцы

            data: {
                labels: data.labels,  // Названия статусов (Черновик, На согласовании и т.д.)
                datasets: [{
                    label: 'Количество договоров',
                    data: data.counts,  // Значения для каждого статуса
                    backgroundColor: data.colors,  // Цвета для каждого столбца
                    borderColor: data.colors,
                    borderWidth: 2,
                    borderRadius: 8  // Скругленные углы столбцов
                }]
            },

            options: {
                responsive: true,  // Адаптивность
                maintainAspectRatio: true,

                plugins: {
                    legend: {
                        display: false  // Скрываем легенду (она не нужна для одного набора данных)
                    },

                    tooltip: {
                        // Кастомная подсказка при наведении
                        callbacks: {
                            label: function (context) {
                                return `Количество: ${context.parsed.y}`;
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,  // Ось Y начинается с 0
                        ticks: {
                            stepSize: 1  // Шаг делений: 1, 2, 3...
                        }
                    }
                },

                animation: {
                    duration: 1000,  // Длительность анимации: 1 секунда
                    easing: 'easeOutQuart'  // Плавное замедление в конце
                }
            }
        });

        console.log('📊 Воронка согласования отрисована');

    } catch (error) {
        console.error('❌ Ошибка загрузки воронки:', error);
        showErrorNotification('Не удалось загрузить воронку согласования');
    }
}

/**
 * ========================================
 * Загрузка и отрисовка динамики по месяцам
 * ========================================
 * API endpoint: /api/dynamics/
 * Тип графика: Line Chart (линейный график)
 * Отображает две линии: "Создано" и "Подписано" за последние 12 месяцев
 */
async function loadDynamicsChart() {
    try {
        const response = await fetch('/api/dynamics/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const ctx = document.getElementById('dynamicsChart').getContext('2d');

        if (dynamicsChart) {
            dynamicsChart.destroy();
        }

        dynamicsChart = new Chart(ctx, {
            type: 'line',  // Тип: линейный график

            data: {
                labels: data.labels,  // Месяцы (Jan 2024, Feb 2024...)
                datasets: [
                    {
                        label: 'Создано',
                        data: data.created,  // Количество созданных договоров по месяцам
                        borderColor: '#0d6efd',  // Синяя линия
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',  // Полупрозрачная заливка
                        tension: 0.4,  // Плавность кривой (0 = прямые линии, 1 = очень плавные)
                        fill: true  // Заливка области под линией
                    },
                    {
                        label: 'Подписано',
                        data: data.signed,  // Количество подписанных договоров по месяцам
                        borderColor: '#198754',  // Зеленая линия
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },

            options: {
                responsive: true,
                maintainAspectRatio: true,

                plugins: {
                    legend: {
                        position: 'top'
                    },

                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    },
                    x: {
                        ticks: {
                            // Показываем метки раз в 3 месяца на мобильных устройствах
                            callback: function (value, index, ticks) {
                                const isMobile = window.innerWidth < 768;
                                if (isMobile) {
                                    // Показываем только каждую 3-ю метку
                                    return index % 3 === 0 ? this.getLabelForValue(value) : '';
                                }
                                return this.getLabelForValue(value);
                            },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },

                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        console.log('📈 Динамика по месяцам отрисована');

    } catch (error) {
        console.error('❌ Ошибка загрузки динамики:', error);
        showErrorNotification('Не удалось загрузить динамику по месяцам');
    }
}

/**
 * ========================================
 * Загрузка и отрисовка распределения по типам
 * ========================================
 * API endpoint: /api/types/
 * Тип графика: Doughnut Chart (кольцевая диаграмма)
 * Отображает процентное соотношение типов договоров
 */
async function loadTypesChart() {
    try {
        const response = await fetch('/api/types/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const ctx = document.getElementById('typesChart').getContext('2d');

        if (typesChart) {
            typesChart.destroy();
        }

        typesChart = new Chart(ctx, {
            type: 'doughnut',  // Тип: кольцевая диаграмма

            data: {
                labels: data.labels,  // Типы договоров (Поставка, Услуги, Аренда...)
                datasets: [{
                    data: data.counts,  // Количество договоров каждого типа
                    backgroundColor: data.colors,  // Цвета для каждого сегмента
                    borderColor: '#fff',  // Белая граница между сегментами
                    borderWidth: 3  // Толщина границы
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: true,

                plugins: {
                    legend: {
                        position: 'right'  // Легенда справа
                    },

                    tooltip: {
                        // Кастомная подсказка с процентами
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;

                                // Вычисляем общую сумму для расчета процентов
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);

                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },

                animation: {
                    animateRotate: true,  // Анимация вращения
                    animateScale: true,  // Анимация масштабирования
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        console.log('🍩 Распределение по типам отрисовано');

    } catch (error) {
        console.error('❌ Ошибка загрузки типов:', error);
        showErrorNotification('Не удалось загрузить распределение по типам');
    }
}

/**
 * ========================================
 * Загрузка и отрисовка топ-5 медленных согласований
 * ========================================
 * API endpoint: /api/slowest/
 * Заполняет HTML-таблицу данными о самых долгих договорах
 */
async function loadSlowestContracts() {
    try {
        const response = await fetch('/api/slowest/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const tbody = document.getElementById('slowest-table');

        // Очищаем таблицу перед заполнением
        tbody.innerHTML = '';

        // Проверяем, есть ли данные
        if (data.data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Нет данных</td></tr>';
            return;
        }

        // Заполняем таблицу строками
        data.data.forEach(contract => {
            const row = `
                <tr>
                    <td><strong>${contract.number}</strong></td>
                    <td>${contract.counterparty}</td>
                    <td><span class="badge bg-secondary">${contract.status}</span></td>
                    <td>${contract.responsible}</td>
                    <td><span class="badge badge-slow">${contract.days} дн.</span></td>
                </tr>
            `;
            tbody.innerHTML += row;
        });

        console.log('🐢 Топ-5 медленных договоров загружен');

    } catch (error) {
        console.error('❌ Ошибка загрузки медленных договоров:', error);
        showErrorNotification('Не удалось загрузить топ-5 медленных договоров');
    }
}

/**
 * ========================================
 * Утилита: Показ уведомления об ошибке
 * ========================================
 * Использует Bootstrap Toast для отображения ошибок пользователю
 */
function showErrorNotification(message) {
    // Создаем элемент уведомления (если еще не создан)
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1050';
        document.body.appendChild(toastContainer);
    }

    // Создаем HTML уведомления
    const toastHtml = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-danger text-white">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong class="me-auto">Ошибка</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;

    // Добавляем уведомление в контейнер
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    // Получаем последний добавленный toast и показываем его
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();

    // Удаляем toast из DOM после скрытия
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * ========================================
 * Настройка анимации кнопки обновления
 * ========================================
 * Добавляет обработчики событий для вращения иконки при наведении
 */
function setupRefreshButtonAnimation() {
    const refreshBtn = document.querySelector('.refresh-btn');
    const refreshIcon = refreshBtn.querySelector('i');

    if (!refreshBtn || !refreshIcon) {
        console.warn('⚠️ Кнопка обновления не найдена');
        return;
    }

    // При наведении мыши — добавляем класс анимации
    refreshBtn.addEventListener('mouseenter', () => {
        refreshIcon.classList.add('fa-spin');
        console.log('🔄 Анимация иконки запущена');
    });

    // При уходе мыши — убираем класс анимации
    refreshBtn.addEventListener('mouseleave', () => {
        refreshIcon.classList.remove('fa-spin');
        console.log('⏹️ Анимация иконки остановлена');
    });

    console.log('✅ Анимация кнопки обновления настроена');
}

/**
 * ========================================
 * Инициализация Bootstrap tooltips
 * ========================================
 * Активирует всплывающие подсказки для KPI-карточек
 */
function initializeTooltips() {
    // Получаем все элементы с data-bs-toggle="tooltip"
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');

    // Создаем массив tooltip объектов
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover',  // Показывать при наведении
            placement: 'bottom',  // Позиция: снизу
            animation: true,  // Плавная анимация
            delay: { show: 300, hide: 100 }  // Задержка показа 300мс
        });
    });

    console.log(`✅ Инициализировано ${tooltipList.length} tooltip'ов`);
}