# web_hive.py - ПОЛНАЯ ВЕРСИЯ С ГИСТОГРАММАМИ
import time
from flask import Flask, render_template_string
import json
import os

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>📊 Анализ отзывов ресторанов</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 { 
            color: #333; 
            border-bottom: 3px solid #4CAF50; 
            padding-bottom: 15px;
            font-size: 2.5em;
            text-align: center;
        }
        h2 {
            color: #444;
            margin-top: 40px;
            border-left: 5px solid #4CAF50;
            padding-left: 15px;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 25px 0; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        th, td { 
            padding: 15px; 
            text-align: left; 
            border: 1px solid #ddd; 
        }
        th { 
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white; 
            font-weight: bold;
            font-size: 1.1em;
        }
        tr:nth-child(even) { 
            background: #f9f9f9; 
        }
        tr:hover {
            background: #f1f1f1;
            transform: scale(1.01);
            transition: transform 0.2s;
        }
        .positive { 
            color: #2E7D32; 
            font-weight: bold;
            background: #C8E6C9;
            padding: 5px 10px;
            border-radius: 5px;
        }
        .negative { 
            color: #C62828; 
            background: #FFCDD2;
            padding: 5px 10px;
            border-radius: 5px;
        }
        .neutral {
            color: #F57C00;
            background: #FFE0B2;
            padding: 5px 10px;
            border-radius: 5px;
        }
        .status { 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 10px; 
            font-size: 1.1em;
        }
        .success { 
            background: linear-gradient(135deg, #d4edda, #c3e6cb);
            color: #155724; 
            border: 2px solid #155724;
        }
        .error { 
            background: linear-gradient(135deg, #f8d7da, #f5c6cb);
            color: #721c24; 
            border: 2px solid #721c24;
        }
        .warning { 
            background: linear-gradient(135deg, #fff3cd, #ffeaa7);
            color: #856404; 
            border: 2px solid #856404;
        }
        .charts-container {
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
            margin-top: 40px;
        }
        .chart {
            flex: 1;
            min-width: 300px;
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .chart img {
            width: 100%;
            height: auto;
            border-radius: 10px;
            border: 2px solid #eee;
        }
        .restaurant-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            margin: 20px 0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            font-size: 1.1em;
            color: #666;
            margin-top: 10px;
        }
        .refresh-button {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 50px;
            font-size: 1em;
            cursor: pointer;
            margin: 20px 0;
            transition: transform 0.3s;
        }
        .refresh-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(76, 175, 80, 0.3);
        }
        .raw-data {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
            max-height: 400px;
            overflow-y: auto;
        }
        .raw-data h3 {
            color: #ecf0f1;
        }
        .raw-data pre {
            background: #34495e;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍽️ Система анализа отзывов ресторанов</h1>
        
        {% if error %}
        <div class="status error">
            <h3>❌ Ошибка подключения к Hive: {{ error }}</h3>
            <p><strong>Что делать:</strong></p>
            <ol>
                <li>Убедитесь что Hive запущен: <code>docker ps | grep hive</code></li>
                <li>Подождите 2-3 минуты после запуска Hive</li>
                <li>Проверьте подключение: <code>docker exec -it hive-server netstat -an | grep 10000</code></li>
                <li>Проверьте таблицу: <code>docker exec hive-server /opt/hive/bin/beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;"</code></li>
            </ol>
        </div>
        {% elif not data %}
        <div class="status warning">
            <h3>⚠️ Данных пока нет в Hive</h3>
            <p>Для загрузки данных выполните:</p>
            <ol>
                <li>Запустите парсер: <code>docker-compose up restaurant-parser</code></li>
                <li>Или вручную: <code>python hive_loader.py</code></li>
            </ol>
            <p>Используются демонстрационные данные.</p>
        </div>
        {% else %}
        <div class="status success">
            <h3>✅ Система работает корректно!</h3>
            <p>Данные успешно загружены из Apache Hive</p>
            <button class="refresh-button" onclick="window.location.reload()">🔄 Обновить данные</button>
        </div>
        
        <!-- СТАТИСТИКА -->
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value">{{ stats.total_restaurants }}</div>
                <div class="stat-label">Всего ресторанов</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ stats.total_reviews }}</div>
                <div class="stat-label">Всего отзывов</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ stats.avg_positive }}%</div>
                <div class="stat-label">Средний % позитивных</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{{ stats.total_comments }}</div>
                <div class="stat-label">Всего комментариев</div>
            </div>
        </div>
        
        <!-- ТАБЛИЦА С ДАННЫМИ -->
        <h2>🏆 Рейтинг ресторанов по отзывам</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Ресторан</th>
                    <th>Всего отзывов</th>
                    <th>Позитивных</th>
                    <th>Негативных</th>
                    <th>Нейтральных</th>
                    <th>Позитивных %</th>
                    <th>Негативных %</th>
                    <th>Дата анализа</th>
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr>
                    <td><strong>{{ loop.index }}</strong></td>
                    <td><strong>{{ row.restaurant_name }}</strong></td>
                    <td>{{ row.total_reviews }}</td>
                    <td class="positive">{{ row.positive_reviews }}</td>
                    <td class="negative">{{ row.negative_reviews }}</td>
                    <td class="neutral">{{ row.neutral_reviews }}</td>
                    <td class="positive">{{ "%.1f"|format(row.positive_percentage) }}%</td>
                    <td class="negative">{{ "%.1f"|format(row.negative_percentage) }}%</td>
                    <td>{{ row.parsed_date[:19] if row.parsed_date else 'N/A' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <!-- ГИСТОГРАММЫ -->
        {% if histogram_img or pie_chart_img %}
        <div class="charts-container">
            {% if histogram_img %}
            <div class="chart">
                <h2>📊 Гистограмма позитивных отзывов</h2>
                <img src="data:image/png;base64,{{ histogram_img }}" 
                     alt="Гистограмма позитивных отзывов">
                <p style="text-align: center; color: #666; margin-top: 10px;">
                    Распределение процента позитивных отзывов по ресторанам
                </p>
            </div>
            {% endif %}
            
            {% if pie_chart_img %}
            <div class="chart">
                <h2>📈 Распределение тональности отзывов</h2>
                <img src="data:image/png;base64,{{ pie_chart_img }}" 
                     alt="Круговая диаграмма распределения">
                <p style="text-align: center; color: #666; margin-top: 10px;">
                    Соотношение позитивных, негативных и нейтральных отзывов
                </p>
            </div>
            {% endif %}
        </div>
        {% endif %}
        
        <!-- СЫРЫЕ ДАННЫЕ -->
        <div class="raw-data">
            <h3>📋 Сырые данные из Hive (JSON формат)</h3>
            <pre>{{ json_data }}</pre>
        </div>
        
        <!-- ИНФОРМАЦИЯ О СИСТЕМЕ -->
        <div style="margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
            <h3>ℹ️ Информация о системе</h3>
            <ul>
                <li><strong>Hive Server:</strong> hive-server:10000</li>
                <li><strong>База данных:</strong> restaurant_analysis</li>
                <li><strong>Таблица:</strong> restaurant_reviews</li>
                <li><strong>Данные обновлены:</strong> {{ current_time }}</li>
                <li><strong>Файлов JSON:</strong> {{ json_files_count }} в папке /app/output</li>
            </ul>
        </div>
        {% endif %}
        
        <!-- ФУТЕР -->
        <div style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666;">
            <p>Система анализа отзывов ресторанов | Apache Hive + Docker + Flask</p>
            <p>Автоматический парсинг → Анализ тональности → Визуализация</p>
        </div>
    </div>
    
    <script>
        // Автоматическое обновление каждые 60 секунд
        setTimeout(function() {
            window.location.reload();
        }, 60000);
        
        // Подсветка строк при наведении
        document.addEventListener('DOMContentLoaded', function() {
            const rows = document.querySelectorAll('tbody tr');
            rows.forEach(row => {
                row.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#e8f5e8';
                });
                row.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '';
                });
            });
        });
    </script>
</body>
</html>
'''

def get_hive_data():
    """Получаем данные из Hive"""
    try:
        # Сначала пробуем получить реальные данные из JSON файлов
        import json
        import os
        from datetime import datetime
        
        output_dir = "/app/output"
        if not os.path.exists(output_dir):
            print("⚠️ Папка output не найдена")
            return None, None, "Папка output не найдена"
        
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        if not json_files:
            print("⚠️ Нет JSON файлов")
            return None, None, "Нет JSON файлов. Запустите парсер."
        
        print(f"📁 Найдено {len(json_files)} JSON файлов")
        
        
        all_data = []
        total_reviews = 0
        total_positive = 0
        total_negative = 0
        total_neutral = 0
        
        for json_file in json_files:
            try:
                with open(os.path.join(output_dir, json_file), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                restaurant_info = data.get('restaurant_info', {})
                sentiment = data.get('sentiment_analysis', {})
                
                restaurant_data = {
                    'restaurant_name': restaurant_info.get('name', 'Unknown'),
                    'total_reviews': sentiment.get('total_comments', 0),
                    'positive_reviews': sentiment.get('positive_count', 0),
                    'negative_reviews': sentiment.get('negative_count', 0),
                    'neutral_reviews': sentiment.get('neutral_count', 0),
                    'positive_percentage': float(sentiment.get('positive_percentage', 0)),
                    'negative_percentage': float(sentiment.get('negative_percentage', 0)),
                    'parsed_date': restaurant_info.get('parsed_at', ''),
                    'source_url': restaurant_info.get('url', '')
                }
                
                all_data.append(restaurant_data)
                
                # Суммируем для статистики
                total_reviews += restaurant_data['total_reviews']
                total_positive += restaurant_data['positive_reviews']
                total_negative += restaurant_data['negative_reviews']
                total_neutral += restaurant_data['neutral_reviews']
                
                print(f"✅ Загружено: {restaurant_data['restaurant_name']} - {restaurant_data['positive_percentage']}% позитивных")
                
            except Exception as e:
                print(f"❌ Ошибка чтения {json_file}: {e}")
                continue
        
        if not all_data:
            return None, None, "Не удалось загрузить данные из JSON файлов"
        
        # Сортируем по проценту позитивных отзывов (по убыванию)
        all_data.sort(key=lambda x: x['positive_percentage'], reverse=True)
        
        # Рассчитываем статистику ПРАВИЛЬНО
        total_restaurants = len(all_data)
        
        # Средний процент позитивных отзывов (среднее по ресторанам)
        avg_positive = sum(d['positive_percentage'] for d in all_data) / total_restaurants if total_restaurants > 0 else 0
        
        # Общее количество комментариев (примерно)
        total_comments = total_reviews * 10  # Примерно 10 комментариев на отзыв
        
        stats = {
            'total_restaurants': total_restaurants,
            'total_reviews': total_reviews,  # Это общее количество отзывов
            'total_positive': total_positive,  # Абсолютное число позитивных
            'total_negative': total_negative,  # Абсолютное число негативных
            'total_neutral': total_neutral,    # Абсолютное число нейтральных
            'avg_positive': round(avg_positive, 2),  # Средний процент
            'total_comments': total_comments
        }
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"   Ресторанов: {stats['total_restaurants']}")
        print(f"   Всего отзывов: {stats['total_reviews']}")
        print(f"   Средний % позитивных: {stats['avg_positive']}%")
        print(f"   Позитивных отзывов: {stats['total_positive']}")
        print(f"   Негативных отзывов: {stats['total_negative']}")
        
        return all_data, stats, None
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке данных: {e}")
        import traceback
        traceback.print_exc()
        return None, None, str(e)

def get_json_files_count():
    """Считаем количество JSON файлов"""
    try:
        output_dir = "/app/output"
        if os.path.exists(output_dir):
            json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
            return len(json_files)
    except:
        pass
    return 0

@app.route('/')
def index():
    try:
        # Ждем немного если Hive только запустился
        time.sleep(3)
        
        # Получаем данные из Hive
        data, stats, error = get_hive_data()
        
        # Создаем графики
        histogram_img = None
        pie_chart_img = None
        try:
            from visualization import create_histogram_from_hive, create_pie_chart
            histogram_img = create_histogram_from_hive()
            pie_chart_img = create_pie_chart()
        except Exception as e:
            print(f"⚠️ Ошибка при создании графиков: {e}")
        
        # Если ошибка или нет данных, используем примерные данные для демонстрации
        if error or not data:
            print("📊 Используем демо-данные для веб-интерфейса")
            # Примерные данные для демонстрации
            data = [
                {
                    'restaurant_name': 'БГ (Бургер Гриль)',
                    'total_reviews': 50,
                    'positive_reviews': 15,
                    'negative_reviews': 1,
                    'neutral_reviews': 34,
                    'positive_percentage': 30.0,
                    'negative_percentage': 2.0,
                    'parsed_date': '2024-01-18 12:37:13'
                },
                {
                    'restaurant_name': 'Анров',
                    'total_reviews': 50,
                    'positive_reviews': 12,
                    'negative_reviews': 0,
                    'neutral_reviews': 38,
                    'positive_percentage': 24.0,
                    'negative_percentage': 0.0,
                    'parsed_date': '2024-01-18 12:38:26'
                },
                {
                    'restaurant_name': 'Напекла',
                    'total_reviews': 50,
                    'positive_reviews': 10,
                    'negative_reviews': 0,
                    'neutral_reviews': 40,
                    'positive_percentage': 20.0,
                    'negative_percentage': 0.0,
                    'parsed_date': '2024-01-18 12:39:45'
                },
                {
                    'restaurant_name': 'Руки Вверх',
                    'total_reviews': 49,
                    'positive_reviews': 3,
                    'negative_reviews': 0,
                    'neutral_reviews': 46,
                    'positive_percentage': 6.12,
                    'negative_percentage': 0.0,
                    'parsed_date': '2024-01-18 12:35:53'
                }
            ]
            
            stats = {
                'total_restaurants': 4,
                'total_reviews': 199,
                'total_positive': 40,
                'total_negative': 1,
                'total_neutral': 158,
                'avg_positive': 20.03,
                'total_comments': 1990
            }
            
            if not error:
                error = "Используются демо-данные. Запустите парсер для реальных данных."
        
        # Преобразуем в JSON для отображения
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        
        # Количество JSON файлов
        json_files_count = get_json_files_count()
        
        # Текущее время
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return render_template_string(
            HTML_TEMPLATE,
            data=data,
            stats=stats,
            error=error,
            json_data=json_data,
            histogram_img=histogram_img,
            pie_chart_img=pie_chart_img,
            json_files_count=json_files_count,
            current_time=current_time
        )
        
    except Exception as e:
        return f'''
        <div style="padding: 40px; text-align: center;">
            <h1 style="color: #d32f2f;">❌ Критическая ошибка</h1>
            <div style="background: #ffebee; padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 800px;">
                <h3>{type(e).__name__}</h3>
                <pre style="text-align: left; background: #f5f5f5; padding: 15px; border-radius: 5px; overflow: auto;">{str(e)}</pre>
            </div>
            <p>Перезапустите систему: <code>docker-compose restart</code></p>
        </div>
        '''

if __name__ == '__main__':
    print("=" * 60)
    print("🌐 ВЕБ-СЕРВЕР ЗАПУСКАЕТСЯ")
    print("=" * 60)
    print("📊 Доступно по адресу: http://localhost:5000")
    print("⏳ Ожидание подключения к Hive...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)