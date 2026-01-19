import matplotlib
matplotlib.use('Agg')  # Для работы без GUI в Docker
import matplotlib.pyplot as plt
import pandas as pd
import os
import json
import io
import base64
from pyhive import hive

def create_histogram_from_hive():
    """Создает гистограмму из данных Hive"""
    try:
        # Подключаемся к Hive
        conn = hive.Connection(host='hive-server', port=10000)
        cursor = conn.cursor()
        
        cursor.execute("USE restaurant_analysis")
        cursor.execute("SELECT restaurant_name, positive_percentage FROM restaurant_reviews")
        data = cursor.fetchall()
        
        if not data:
            return create_histogram_from_json()  # Если Hive пуст
        
        df = pd.DataFrame(data, columns=['restaurant', 'positive_percentage'])
        
        # Создаем график
        plt.figure(figsize=(12, 6))
        bars = plt.bar(df['restaurant'], df['positive_percentage'], color='skyblue')
        
        # Добавляем значения на столбцы
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        plt.title('📊 Процент позитивных отзывов по ресторанам', fontsize=16, pad=20)
        plt.xlabel('Рестораны', fontsize=12)
        plt.ylabel('Позитивные отзывы (%)', fontsize=12)
        plt.ylim(0, 100)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Сохраняем в байты
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=100)
        img_bytes.seek(0)
        plt.close()
        
        return base64.b64encode(img_bytes.read()).decode()
        
    except Exception as e:
        print(f"Ошибка при создании гистограммы из Hive: {e}")
        return create_histogram_from_json()

def create_histogram_from_json():
    """Создает гистограмму из JSON файлов"""
    try:
        data = []
        output_dir = "output"
        
        if not os.path.exists(output_dir):
            return None
        
        for file in os.listdir(output_dir):
            if file.endswith('.json'):
                with open(os.path.join(output_dir, file), 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    data.append({
                        'restaurant': json_data['restaurant_info']['name'],
                        'positive_percentage': json_data['sentiment_analysis']['positive_percentage']
                    })
        
        if not data:
            return None
        
        df = pd.DataFrame(data)
        df = df.sort_values('positive_percentage', ascending=False)
        
        # Создаем график
        plt.figure(figsize=(12, 6))
        colors = ['green' if x > 50 else 'orange' if x > 20 else 'red' for x in df['positive_percentage']]
        bars = plt.bar(df['restaurant'], df['positive_percentage'], color=colors)
        
        # Добавляем значения
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        plt.title('📊 Процент позитивных отзывов по ресторанам (из JSON)', fontsize=16, pad=20)
        plt.xlabel('Рестораны', fontsize=12)
        plt.ylabel('Позитивные отзывы (%)', fontsize=12)
        plt.ylim(0, 100)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Сохраняем в байты
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=100)
        img_bytes.seek(0)
        plt.close()
        
        return base64.b64encode(img_bytes.read()).decode()
        
    except Exception as e:
        print(f"Ошибка при создании гистограммы из JSON: {e}")
        return None

def create_pie_chart():
    """Создает круговую диаграмму"""
    try:
        conn = hive.Connection(host='hive-server', port=10000)
        cursor = conn.cursor()
        cursor.execute("USE restaurant_analysis")
        cursor.execute("""
            SELECT 
                SUM(positive_reviews) as positive,
                SUM(negative_reviews) as negative,
                SUM(neutral_reviews) as neutral
            FROM restaurant_reviews
        """)
        data = cursor.fetchone()
        
        labels = ['Позитивные', 'Негативные', 'Нейтральные']
        sizes = [data[0], data[1], data[2]]
        colors = ['#4CAF50', '#F44336', '#FFC107']
        
        plt.figure(figsize=(8, 8))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        plt.title('📈 Распределение тональности всех отзывов', fontsize=16)
        plt.axis('equal')
        
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', dpi=100)
        img_bytes.seek(0)
        plt.close()
        
        return base64.b64encode(img_bytes.read()).decode()
        
    except:
        return None

if __name__ == "__main__":
    # Тестируем
    img = create_histogram_from_hive()
    if img:
        print("Гистограмма создана успешно!")
    else:
        print("Не удалось создать гистограмму")