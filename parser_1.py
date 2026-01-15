import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
from selenium.common.exceptions import NoSuchElementException
from typing import Union
import re


class RestaurantReviewParser:
    def __init__(self, driver):
        # Инициализация парсера с указанным драйвером
        self.driver = driver
        # Ключевые слова для анализа тональности
        self.positive_keywords = [
            'отлично', 'прекрасно', 'хорошо', 'рекомендую', 'супер', 
            'отличный', 'замечательно', 'великолепно', 'восхитительно',
            'удовлетворен', 'понравилось', 'люблю', 'обожаю', 'восторг',
            'прекрасный', 'хороший', 'отличное', 'класс', 'топ', 'лучший',
            'вкусно', 'вкусный', 'уютно', 'чисто', 'быстро', 'вежливо',
            'потрясающе', 'шикарно', 'безупречно', 'идеально', 'нравится'
        ]
        self.negative_keywords = [
            'плохо', 'ужасно', 'отвратительно', 'недоволен', 'не рекомендую',
            'кошмар', 'разочарован', 'жутко', 'гадость', 'отвратительный',
            'плохой', 'неприятно', 'отвратительное', 'ужасный', 'не понравилось',
            'ненавижу', 'отвращение', 'ужас', 'позор', 'отвратно', 'грубо',
            'грязно', 'долго', 'дорого', 'пересолено', 'недоварено', 'пережарено',
            'несвежий', 'неопрятно', 'хамство'
        ]

    def analyze_sentiment(self, text: str) -> dict:
        """
        Анализирует тональность текста отзыва
        Возвращает словарь с результатами анализа
        """
        if not text or not isinstance(text, str):
            return {
                'sentiment': 'neutral',
                'score': 0,
                'positive_words': [],
                'negative_words': []
            }
        
        text_lower = text.lower()
        
        # Находим положительные слова
        found_positive = []
        for word in self.positive_keywords:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                found_positive.append(word)
        
        # Находим отрицательные слова
        found_negative = []
        for word in self.negative_keywords:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                found_negative.append(word)
        
        # Считаем оценку тональности
        score = len(found_positive) - len(found_negative)
        
        # Определяем общую тональность
        if score > 0:
            sentiment = 'positive'
        elif score < 0:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': score,
            'positive_words': found_positive,
            'negative_words': found_negative,
            'text_length': len(text)
        }

    def scroll_to_bottom(self, scroll_element_class: str, max_scrolls: int = 20) -> None:
        """
        Прокручивает страницу до загрузки всех отзывов
        """
        print("Начинаем прокрутку для загрузки всех отзывов...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < max_scrolls:
            # Прокручиваем вниз
            self.driver.execute_script(f"""
                var element = document.querySelector('{scroll_element_class}');
                if (element) {{
                    element.scrollTop = element.scrollHeight;
                }} else {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            """)
            
            # Ждем загрузки новых отзывов
            time.sleep(2)
            
            # Проверяем, появились ли новые отзывы
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # Проверяем наличие кнопки "Показать еще"
                try:
                    show_more_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Показать ещё')]")
                    show_more_button.click()
                    print("Нажата кнопка 'Показать ещё'")
                    time.sleep(2)
                except:
                    break  # Больше нечего загружать
            
            last_height = new_height
            scroll_attempts += 1
            print(f"Прокрутка {scroll_attempts}/{max_scrolls} завершена")
        
        print("Прокрутка завершена")

    @staticmethod
    def get_count_star(review_stars: list) -> Union[float, int]:
        star_count: float = 0
        for review_star in review_stars:
            if '_empty' in review_star.get_attribute('class'):
                continue
            if '_half' in review_star.get_attribute('class'):
                star_count = star_count + 0.5
                continue
            star_count = star_count + 1
        return star_count

    def parse_restaurant_reviews(self, url: str, restaurant_name: str = None) -> dict:
        """
        Парсит отзывы с конкретной страницы ресторана
        
        Args:
            url: URL страницы с отзывами ресторана
            restaurant_name: Название ресторана (опционально)
        """
        print(f"\n{'='*80}")
        print(f"НАЧИНАЕМ ПАРСИНГ ОТЗЫВОВ")
        print(f"Ссылка: {url}")
        if restaurant_name:
            print(f"Название ресторана: {restaurant_name}")
        print(f"{'='*80}")
        
        try:
            # Переходим на страницу
            self.driver.get(url)
            time.sleep(5)  # Ждем загрузки страницы
            
            # Пробуем получить название ресторана из страницы
            if not restaurant_name:
                try:
                    title_element = self.driver.find_element(By.CSS_SELECTOR, 'h1.orgpage-header-view__header')
                    restaurant_name = title_element.text.strip()
                    print(f"Название ресторана из страницы: {restaurant_name}")
                except:
                    restaurant_name = "Неизвестный ресторан"
            
            # Прокручиваем для загрузки всех отзывов
            print("Загружаем все отзывы...")
            self.scroll_to_bottom('.business-reviews-card-view__reviews', max_scrolls=15)
            time.sleep(3)
            
            # Ищем отзывы
            reviews_elements = self.driver.find_elements(By.CSS_SELECTOR, '.business-review-view')
            print(f"Найдено элементов отзывов: {len(reviews_elements)}")
            
            if not reviews_elements:
                # Пробуем альтернативный селектор
                reviews_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="review"]')
                print(f"Альтернативный поиск: найдено {len(reviews_elements)} элементов")
            
            user_comments = {}
            positive_comments = []
            negative_comments = []
            neutral_comments = []
            
            review_count = 0
            
            for i, review_element in enumerate(reviews_elements):
                try:
                    # Прокручиваем к элементу
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", review_element)
                    time.sleep(0.2)
                    
                    # Получаем HTML элемента для парсинга
                    review_html = review_element.get_attribute('outerHTML')
                    soup = BeautifulSoup(review_html, 'html.parser')
                    
                    # Получаем имя пользователя
                    name = "Аноним"
                    try:
                        name_element = soup.select_one('.business-review-view__author')
                        if name_element:
                            name_link = name_element.find('a')
                            if name_link:
                                name = name_link.text.strip()
                            else:
                                name = name_element.text.strip()
                    except:
                        pass
                    
                    # Получаем дату отзыва
                    date = ""
                    try:
                        date_element = soup.select_one('.business-review-view__date')
                        if date_element:
                            date = date_element.text.strip()
                    except:
                        pass
                    
                    # Получаем текст отзыва
                    text = ""
                    try:
                        text_element = soup.select_one('.business-review-view__body-text')
                        if text_element:
                            text = text_element.text.strip()
                        else:
                            # Пробуем другой селектор
                            text_element = review_element.find_element(By.CSS_SELECTOR, '[class*="body"]')
                            text = text_element.text.strip()
                    except:
                        try:
                            text = review_element.text
                        except:
                            pass
                    
                    # Получаем оценку (звезды)
                    stars = 0
                    try:
                        # Ищем звезды в элементе
                        stars_container = soup.select_one('.business-rating-badge-view__stars')
                        if stars_container:
                            star_elements = stars_container.find_all('span')
                            stars = self.get_count_star(star_elements)
                        else:
                            # Пробуем получить оценку из текста
                            rating_text = soup.select_one('.business-rating-badge-view__rating-text')
                            if rating_text:
                                try:
                                    stars = float(rating_text.text.strip())
                                except:
                                    pass
                    except:
                        pass
                    
                    # Пропускаем отзывы без текста
                    if not text or len(text.strip()) < 5:
                        continue
                    
                    # Анализируем тональность отзыва
                    sentiment_analysis = self.analyze_sentiment(text)
                    
                    # Корректируем оценку на основе звезд
                    if stars >= 4:
                        sentiment_analysis['score'] += 2
                    elif stars >= 3:
                        sentiment_analysis['score'] += 1
                    elif stars <= 2:
                        sentiment_analysis['score'] -= 2
                    elif stars <= 1:
                        sentiment_analysis['score'] -= 3
                    
                    # Определяем финальную тональность
                    final_sentiment = sentiment_analysis['sentiment']
                    if sentiment_analysis['score'] > 1:
                        final_sentiment = 'positive'
                        positive_comments.append({
                            'name': name,
                            'text': text,
                            'stars': stars,
                            'date': date
                        })
                    elif sentiment_analysis['score'] < -1:
                        final_sentiment = 'negative'
                        negative_comments.append({
                            'name': name,
                            'text': text,
                            'stars': stars,
                            'date': date
                        })
                    else:
                        final_sentiment = 'neutral'
                        neutral_comments.append({
                            'name': name,
                            'text': text,
                            'stars': stars,
                            'date': date
                        })
                    
                    # Сохраняем отзыв
                    review_id = f"review_{review_count}"
                    user_comments[review_id] = {
                        'name': name,
                        'stars': stars,
                        'date': date,
                        'text': text,
                        'sentiment': final_sentiment,
                        'analysis': sentiment_analysis
                    }
                    
                    review_count += 1
                    
                    if review_count % 10 == 0:
                        print(f"Обработано отзывов: {review_count}")
                    
                except Exception as e:
                    print(f"Ошибка при обработке отзыва {i}: {str(e)[:100]}...")
                    continue
            
            # Статистика по отзывам
            total_comments = len(user_comments)
            sentiment_stats = {
                'total_comments': total_comments,
                'positive_count': len(positive_comments),
                'negative_count': len(negative_comments),
                'neutral_count': len(neutral_comments),
                'positive_percentage': round(len(positive_comments) / total_comments * 100, 2) if total_comments > 0 else 0,
                'negative_percentage': round(len(negative_comments) / total_comments * 100, 2) if total_comments > 0 else 0,
                'neutral_percentage': round(len(neutral_comments) / total_comments * 100, 2) if total_comments > 0 else 0
            }
            
            # Формируем результат
            result = {
                'restaurant_info': {
                    'name': restaurant_name,
                    'url': url,
                    'parsed_at': time.strftime("%Y-%m-%d %H:%M:%S")
                },
                'user_comments': user_comments,
                'sentiment_analysis': sentiment_stats,
                'positive_comments': positive_comments[:20],  # Ограничиваем для наглядности
                'negative_comments': negative_comments[:20],
                'neutral_comments': neutral_comments[:20]
            }
            
            # Сохраняем в файл
            safe_name = re.sub(r'[^\w\s-]', '', restaurant_name).strip().replace(' ', '_')
            filename = f"reviews_{safe_name}_{int(time.time())}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Выводим статистику
            print(f"\n{'='*80}")
            print(f"РЕЗУЛЬТАТЫ ПАРСИНГА: {restaurant_name}")
            print(f"{'='*80}")
            print(f"Всего обработано отзывов: {sentiment_stats['total_comments']}")
            print(f"Позитивных: {sentiment_stats['positive_count']} ({sentiment_stats['positive_percentage']}%)")
            print(f"Негативных: {sentiment_stats['negative_count']} ({sentiment_stats['negative_percentage']}%)")
            print(f"Нейтральных: {sentiment_stats['neutral_count']} ({sentiment_stats['neutral_percentage']}%)")
            print(f"Файл с результатами: {filename}")
            print(f"{'='*80}")
            
            return result
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы: {e}")
            return None

    @staticmethod
    def save_to_file(data, filename):
        with open(filename, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


def main():
    """
    Основная функция для тестирования парсера
    """
    # Ссылки на отзывы ресторанов
    restaurants = [
        {
            'name': 'Руки_вверх',
            'url': 'https://yandex.ru/maps/org/ruki_vverkh_/61051687701/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.621506%2C64.547847&mode=search&sll=40.555588%2C64.547813&tab=reviews&text=category_id%3A%28184106390%29&z=12'
        },
        {
            'name': 'Напекла',
            'url': 'https://yandex.ru/maps/org/napekla/195075538071/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.621506%2C64.547847&mode=search&sll=40.555588%2C64.547813&tab=reviews&text=category_id%3A%28184106390%29&z=12'
        }
    ]
    
    # Настройка браузера
    opts = webdriver.ChromeOptions()
    
    # Раскомментируйте для фонового режима:
    # opts.add_argument('--headless')  # Фоновый режим
    # opts.add_argument('--no-sandbox')
    # opts.add_argument('--disable-dev-shm-usage')
    
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-notifications')
    opts.add_argument('--disable-popup-blocking')
    
    # User-Agent для имитации реального браузера
    opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Дополнительные опции для стабильности
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    all_results = []
    
    try:
        print("Запускаем Chrome браузер...")
        driver = webdriver.Chrome(options=opts)
        
        # Устанавливаем размер окна
        driver.set_window_size(1400, 1000)
        
        # Скрываем автоматизацию
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        # Создаем парсер
        parser = RestaurantReviewParser(driver)
        
        # Парсим отзывы для каждого ресторана
        for restaurant in restaurants:
            print(f"\n{'#'*80}")
            print(f"Парсим отзывы для: {restaurant['name']}")
            print(f"{'#'*80}")
            
            result = parser.parse_restaurant_reviews(
                url=restaurant['url'],
                restaurant_name=restaurant['name']
            )
            
            if result:
                all_results.append(result)
            
            # Пауза между ресторанами
            time.sleep(3)
        
        # Создаем сводный отчет
        if all_results:
            summary = {
                'total_restaurants': len(all_results),
                'total_reviews': sum(r['sentiment_analysis']['total_comments'] for r in all_results),
                'overall_sentiment': {
                    'positive': sum(r['sentiment_analysis']['positive_count'] for r in all_results),
                    'negative': sum(r['sentiment_analysis']['negative_count'] for r in all_results),
                    'neutral': sum(r['sentiment_analysis']['neutral_count'] for r in all_results)
                },
                'restaurants': [
                    {
                        'name': r['restaurant_info']['name'],
                        'total_reviews': r['sentiment_analysis']['total_comments'],
                        'positive_percentage': r['sentiment_analysis']['positive_percentage'],
                        'negative_percentage': r['sentiment_analysis']['negative_percentage'],
                        'file': f"reviews_{r['restaurant_info']['name'].replace(' ', '_')}_*.json"
                    } for r in all_results
                ],
                'parsed_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Добавляем общие проценты
            total_reviews = summary['total_reviews']
            if total_reviews > 0:
                summary['overall_percentages'] = {
                    'positive': round(summary['overall_sentiment']['positive'] / total_reviews * 100, 2),
                    'negative': round(summary['overall_sentiment']['negative'] / total_reviews * 100, 2),
                    'neutral': round(summary['overall_sentiment']['neutral'] / total_reviews * 100, 2)
                }
            
            # Сохраняем сводный отчет
            summary_filename = f"restaurants_summary_{int(time.time())}.json"
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"\n{'='*80}")
            print("СВОДНЫЙ ОТЧЕТ ПО ВСЕМ РЕСТОРАНАМ")
            print(f"{'='*80}")
            print(f"Всего ресторанов: {summary['total_restaurants']}")
            print(f"Всего отзывов: {summary['total_reviews']}")
            if 'overall_percentages' in summary:
                print(f"Общая позитивность: {summary['overall_percentages']['positive']}%")
                print(f"Общая негативность: {summary['overall_percentages']['negative']}%")
                print(f"Общая нейтральность: {summary['overall_percentages']['neutral']}%")
            print(f"Сводный отчет сохранен в: {summary_filename}")
            print(f"{'='*80}")
            
            # Выводим рейтинг ресторанов
            print(f"\n{'='*80}")
            print("РЕЙТИНГ РЕСТОРАНОВ ПО ПОЗИТИВНЫМ ОТЗЫВАМ")
            print(f"{'='*80}")
            sorted_restaurants = sorted(all_results, 
                                      key=lambda x: x['sentiment_analysis']['positive_percentage'], 
                                      reverse=True)
            
            for i, restaurant in enumerate(sorted_restaurants):
                stats = restaurant['sentiment_analysis']
                print(f"{i+1}. {restaurant['restaurant_info']['name']}:")
                print(f"   Всего отзывов: {stats['total_comments']}")
                print(f"   Позитивных: {stats['positive_percentage']}%")
                print(f"   Негативных: {stats['negative_percentage']}%")
                print(f"   Нейтральных: {stats['neutral_percentage']}%")
                print()
            
    except Exception as e:
        print(f"Ошибка в работе программы: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("Закрываем браузер...")
            driver.quit()
    
    print("\nПарсинг завершен!")


if __name__ == "__main__":
    main()