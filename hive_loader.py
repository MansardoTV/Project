from pyhive import hive
import json
import os
import time

def main():
    print("="*60)
    print("📊 ПРОБУЕМ ПОДКЛЮЧИТЬСЯ К HIVE")
    print("="*60)
    
    try:
        # Пробуем подключиться
        print("🔌 Подключаемся к hive-server:10000...")
        conn = hive.Connection(host='hive-server', port=10000)
        cursor = conn.cursor()
        print("✅ Подключение успешно!")
        
        # Создаем базу данных
        cursor.execute("CREATE DATABASE IF NOT EXISTS restaurant_analysis")
        cursor.execute("USE restaurant_analysis")
        print("✅ База данных создана")
        
        # Создаем таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS restaurant_reviews (
                restaurant_name STRING,
                total_reviews INT,
                positive_reviews INT,
                negative_reviews INT,
                neutral_reviews INT,
                positive_percentage DOUBLE,
                negative_percentage DOUBLE,
                parsed_date STRING,
                source_url STRING
            )
        """)
        print("✅ Таблица создана")
        
        # Ищем JSON файлы
        json_files = []
        if os.path.exists("output"):
            json_files = [f for f in os.listdir("output") if f.endswith('.json')]
        
        if not json_files:
            print("⚠️ Нет JSON файлов в папке output/")
            print("   Сначала запустите парсер: python parser_docker.py")
            return
        
        print(f"📁 Найдено {len(json_files)} JSON файлов")
        
        # Загружаем каждый файл
        for json_file in json_files:
            try:
                with open(f"output/{json_file}", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                restaurant_info = data.get('restaurant_info', {})
                sentiment = data.get('sentiment_analysis', {})
                
                cursor.execute("""
                    INSERT INTO restaurant_reviews VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    restaurant_info.get('name', 'Unknown'),
                    sentiment.get('total_comments', 0),
                    sentiment.get('positive_count', 0),
                    sentiment.get('negative_count', 0),
                    sentiment.get('neutral_count', 0),
                    float(sentiment.get('positive_percentage', 0)),
                    float(sentiment.get('negative_percentage', 0)),
                    restaurant_info.get('parsed_at', ''),
                    restaurant_info.get('url', '')
                ))
                
                print(f"✅ Загружено: {restaurant_info.get('name', 'Unknown')}")
                
            except Exception as e:
                print(f"❌ Ошибка с файлом {json_file}: {str(e)[:50]}")
                continue
        
        # Проверяем что загрузилось
        cursor.execute("SELECT COUNT(*) FROM restaurant_reviews")
        count = cursor.fetchone()[0]
        print(f"\n📊 В Hive загружено: {count} записей")
        
        # Показываем данные
        cursor.execute("SELECT restaurant_name, positive_percentage FROM restaurant_reviews")
        results = cursor.fetchall()
        
        print("\n🏆 Рейтинг ресторанов из Hive:")
        for name, percent in results:
            print(f"  {name}: {percent}% позитивных")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Hive: {e}")
        print("\n💡 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("1. Hive ещё не запустился - подождите 1-2 минуты")
        print("2. Порт 10000 не открыт")
        print("3. Проблемы с сетью Docker")
        print("\n📁 Данные всё равно сохранены в папке output/ как JSON файлы")

if __name__ == "__main__":
    main()