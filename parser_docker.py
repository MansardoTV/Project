import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
from selenium.common.exceptions import NoSuchElementException
from typing import Union
import re
import os


class RestaurantReviewParser:
    def __init__(self, driver):
        self.driver = driver
        # Увеличил списки ключевых слов
        self.positive_keywords = [
            'отлично', 'прекрасно', 'хорошо', 'рекомендую', 'супер', 
            'отличный', 'замечательно', 'великолепно', 'восхитительно',
            'удовлетворен', 'понравилось', 'люблю', 'обожаю', 'восторг',
            'прекрасный', 'хороший', 'отличное', 'класс', 'топ', 'лучший',
            'вкусно', 'вкусный', 'уютно', 'чисто', 'быстро', 'вежливо',
            'потрясающе', 'шикарно', 'безупречно', 'идеально', 'нравится',
            'доволен', 'приятно', 'восхищение', 'наслаждение', 'обалденно',
            'превосходно', 'сказочно', 'чудесно', 'невероятно', 'фантастически',
            'кайф', 'удовольствие', 'рад', 'счастлив', 'довольна'
        ]
        self.negative_keywords = [
            'плохо', 'ужасно', 'отвратительно', 'недоволен', 'не рекомендую',
            'кошмар', 'разочарован', 'жутко', 'гадость', 'отвратительный',
            'плохой', 'неприятно', 'отвратительное', 'ужасный', 'не понравилось',
            'ненавижу', 'отвращение', 'ужас', 'позор', 'отвратно', 'грубо',
            'грязно', 'долго', 'дорого', 'пересолено', 'недоварено', 'пережарено',
            'несвежий', 'неопрятно', 'хамство', 'бесит', 'раздражает', 'зря',
            'напутали', 'перепутали', 'обманули', 'кинули', 'обсчитали',
            'переплатил', 'недовольна', 'злюсь', 'бесит', 'возмущена'
        ]

    def analyze_sentiment(self, text: str) -> dict:
        if not text or not isinstance(text, str):
            return {
                'sentiment': 'neutral',
                'score': 0,
                'positive_words': [],
                'negative_words': []
            }
        
        text_lower = text.lower()
        
        # Ищем слова с границами слов
        found_positive = []
        for word in self.positive_keywords:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                found_positive.append(word)
        
        found_negative = []
        for word in self.negative_keywords:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                found_negative.append(word)
        
        # Считаем вес: позитивные слова дают +2, негативные -2
        score = (len(found_positive) * 2) - (len(found_negative) * 2)
        
        # Определяем тональность
        if score >= 2:  # Если есть хотя бы 1 позитивное слово без негативных
            sentiment = 'positive'
        elif score <= -2:  # Если есть хотя бы 1 негативное слово без позитивных
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

    def scroll_to_bottom(self, scroll_element_class: str, max_scrolls: int = 10) -> None:
        print("Начинаем прокрутку для загрузки всех отзывов...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        
        while scroll_attempts < max_scrolls:
            self.driver.execute_script(f"""
                var element = document.querySelector('{scroll_element_class}');
                if (element) {{
                    element.scrollTop = element.scrollHeight;
                }} else {{
                    window.scrollTo(0, document.body.scrollHeight);
                }}
            """)
            
            time.sleep(3)  # Увеличил время ожидания
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                try:
                    show_more_button = self.driver.find_element(By.XPATH, 
                        "//button[contains(text(), 'Показать ещё') or contains(text(), 'Ещё отзывы')]")
                    show_more_button.click()
                    print("Нажата кнопка 'Показать ещё'")
                    time.sleep(3)
                except:
                    break
            
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
        print(f"\n{'='*80}")
        print(f"НАЧИНАЕМ ПАРСИНГ ОТЗЫВОВ")
        print(f"Ссылка: {url}")
        if restaurant_name:
            print(f"Название ресторана: {restaurant_name}")
        print(f"{'='*80}")
        
        try:
            self.driver.get(url)
            time.sleep(5)
            
            if not restaurant_name:
                try:
                    title_element = self.driver.find_element(By.CSS_SELECTOR, 'h1.orgpage-header-view__header')
                    restaurant_name = title_element.text.strip()
                    print(f"Название ресторана из страницы: {restaurant_name}")
                except:
                    restaurant_name = "Неизвестный ресторан"
            
            print("Загружаем все отзывы...")
            self.scroll_to_bottom('.business-reviews-card-view__reviews', max_scrolls=8)
            time.sleep(3)
            
            reviews_elements = self.driver.find_elements(By.CSS_SELECTOR, '.business-review-view')
            print(f"Найдено элементов отзывов: {len(reviews_elements)}")
            
            if len(reviews_elements) < 10:
                # Пробуем альтернативный селектор
                alt_reviews = self.driver.find_elements(By.CSS_SELECTOR, '[class*="review"]')
                print(f"Альтернативный поиск: найдено {len(alt_reviews)} элементов")
                if len(alt_reviews) > len(reviews_elements):
                    reviews_elements = alt_reviews
            
            user_comments = {}
            positive_comments = []
            negative_comments = []
            neutral_comments = []
            
            review_count = 0
            
            print(f"Обрабатываем {len(reviews_elements)} отзывов...")
            
            # УБРАЛ ОГРАНИЧИТЕЛЬ [:15] - теперь обрабатываем ВСЕ
            for i, review_element in enumerate(reviews_elements):
                try:
                    # Прокручиваем к элементу
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", review_element)
                    time.sleep(0.3)
                    
                    review_html = review_element.get_attribute('outerHTML')
                    soup = BeautifulSoup(review_html, 'html.parser')
                    
                    # Имя пользователя
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
                    
                    # Дата отзыва
                    date = ""
                    try:
                        date_element = soup.select_one('.business-review-view__date')
                        if date_element:
                            date = date_element.text.strip()
                    except:
                        pass
                    
                    # Текст отзыва
                    text = ""
                    try:
                        text_element = soup.select_one('.business-review-view__body-text')
                        if text_element:
                            text = text_element.text.strip()
                        else:
                            text_element = review_element.find_element(By.CSS_SELECTOR, '[class*="body"]')
                            text = text_element.text.strip()
                    except:
                        try:
                            text = review_element.text[:500]  # Берем только начало если не нашли нормально
                        except:
                            pass
                    
                    # Оценка (звезды)
                    stars = 0
                    try:
                        stars_container = soup.select_one('.business-rating-badge-view__stars')
                        if stars_container:
                            star_elements = stars_container.find_all('span')
                            stars = self.get_count_star(star_elements)
                        else:
                            rating_text = soup.select_one('.business-rating-badge-view__rating-text')
                            if rating_text:
                                try:
                                    stars = float(rating_text.text.strip())
                                except:
                                    pass
                    except:
                        pass
                    
                    # Пропускаем отзывы без текста или с мусором
                    if not text or len(text.strip()) < 10 or text == "Подписаться":
                        continue
                    
                    # Анализируем тональность
                    sentiment_analysis = self.analyze_sentiment(text)
                    
                    # Корректируем оценку на основе звезд (более мягкая логика)
                    if stars > 0:
                        if stars >= 4.5:
                            sentiment_analysis['score'] += 4
                        elif stars >= 4:
                            sentiment_analysis['score'] += 3
                        elif stars >= 3.5:
                            sentiment_analysis['score'] += 2
                        elif stars >= 3:
                            sentiment_analysis['score'] += 1
                        elif stars <= 2.5:
                            sentiment_analysis['score'] -= 1
                        elif stars <= 2:
                            sentiment_analysis['score'] -= 2
                        elif stars <= 1:
                            sentiment_analysis['score'] -= 3
                    
                    # ИСПРАВЛЕННАЯ ЛОГИКА РАСПРЕДЕЛЕНИЯ
                    final_sentiment = sentiment_analysis['sentiment']
                    
                    if sentiment_analysis['score'] >= 3:  # Четко позитивный
                        final_sentiment = 'positive'
                        positive_comments.append({
                            'name': name,
                            'text': text[:300],
                            'stars': stars,
                            'date': date
                        })
                    elif sentiment_analysis['score'] <= -3:  # Четко негативный
                        final_sentiment = 'negative'
                        negative_comments.append({
                            'name': name,
                            'text': text[:300],
                            'stars': stars,
                            'date': date
                        })
                    else:  # Нейтральный или смешанный
                        final_sentiment = 'neutral'
                        neutral_comments.append({
                            'name': name,
                            'text': text[:300],
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
                        print(f"  Обработано отзывов: {review_count}/{len(reviews_elements)}")
                    
                except Exception as e:
                    if review_count % 20 == 0:  # Не спамим ошибками
                        print(f"  Пропущен отзыв {i}: {str(e)[:50]}...")
                    continue
            
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
            
            result = {
                'restaurant_info': {
                    'name': restaurant_name,
                    'url': url,
                    'parsed_at': time.strftime("%Y-%m-%d %H:%M:%S")
                },
                'user_comments': user_comments,
                'sentiment_analysis': sentiment_stats,
                'positive_comments': positive_comments[:15],  # Ограничиваем только для отображения
                'negative_comments': negative_comments[:15],
                'neutral_comments': neutral_comments[:15]
            }
            
            # Сохраняем в файл
            safe_name = re.sub(r'[^\w\s-]', '', restaurant_name).strip().replace(' ', '_')
            filename = f"reviews_{safe_name}_{int(time.time())}.json"
            
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n{'='*80}")
            print(f"РЕЗУЛЬТАТЫ ПАРСИНГА: {restaurant_name}")
            print(f"{'='*80}")
            print(f"Всего отзывов на странице: {len(reviews_elements)}")
            print(f"Успешно обработано: {sentiment_stats['total_comments']}")
            print(f"Позитивных: {sentiment_stats['positive_count']} ({sentiment_stats['positive_percentage']}%)")
            print(f"Негативных: {sentiment_stats['negative_count']} ({sentiment_stats['negative_percentage']}%)")
            print(f"Нейтральных: {sentiment_stats['neutral_count']} ({sentiment_stats['neutral_percentage']}%)")
            print(f"Файл с результатами: {output_path}")
            print(f"{'='*80}")
            
            return result
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Основная функция для Docker"""
    from selenium.webdriver.chrome.options import Options
    
    print("=" * 80)
    print("🍽️  ПАРСЕР ОТЗЫВОВ РЕСТОРАНОВ В DOCKER")
    print("=" * 80)
    
    # Настройки для Docker
    opts = Options()
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    opts.binary_location = '/usr/bin/google-chrome'
    
    driver = None
    
    try:
        print("1. 🚀 Запускаем Chrome в Docker...")
        driver = webdriver.Chrome(options=opts)
        driver.set_window_size(1920, 1080)
        print("   ✅ Chrome успешно запущен!")
        
        # Создаем парсер
        parser = RestaurantReviewParser(driver)
        
        # СПИСОК РЕСТОРАНОВ (ТЫ ДОБАВИШЬ СВОИ ССЫЛКИ)
        restaurants = [
            {
                'name': 'Руки Вверх',
                'url': 'https://yandex.ru/maps/org/ruki_vverkh_/61051687701/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.621506%2C64.547847&mode=search&sll=40.555588%2C64.547813&tab=reviews&text=category_id%3A%28184106390%29&z=12'
            },
            {
                'name': 'БГ (Бургер Гриль)',
                'url': 'https://yandex.ru/maps/org/bg/1710293547/reviews/'
            },
            {
                'name': 'Напекла',
                'url': 'https://yandex.ru/maps/org/napekla/195075538071/reviews/'
            },
            {
                'name': 'Анров',
                'url': 'https://yandex.ru/maps/org/anrov/29048376633/reviews/'
            },
            {
                'name': 'Vkuss Суши',
                'url': 'https://yandex.ru/maps/org/vkuss_sushi/116784392153/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.555588%2C64.547847&mode=search&sll=40.555588%2C64.547813&tab=reviews&text=category_id%3A%28184106390%29&z=12'
            },
            {
                'name': 'Эребуни',
                'url': 'https://yandex.ru/maps/org/erebuni/242006151730/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Inside',
                'url': 'https://yandex.ru/maps/org/inside/126786506724/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Кофе s вафли',
                'url': 'https://yandex.ru/maps/org/kofe_s_vafli/51593471756/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Ялта',
                'url': 'https://yandex.ru/maps/org/yalta/1782833264/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Калитка Парк',
                'url': 'https://yandex.ru/maps/org/kalitka_park/5082803970/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Старый Архангельск',
                'url': 'https://yandex.ru/maps/org/stary_arkhangelsk/197813814285/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Hindi',
                'url': 'https://yandex.ru/maps/org/hindi/24767446847/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Rampa street cafe',
                'url': 'https://yandex.ru/maps/org/rampa_street_cafe/195262812284/reviews/?display-text=%D0%9A%D0%B0%D1%84%D0%B5&ll=40.513022%2C64.542904&mode=search&sctx=ZAAAAAgBEAAaKAoSCYFCPX0EQkRAEfOtD%2BuNIlBAEhIJD9B9ObNd3z8RLGLYYUz61T8iBgABAgMEBSgKOABAmIYGSAFqAnJ1nQHNzMw9oAEAqAEAvQFiVHEZwgGOAbKkw8WFB77C9YEzq4TErwbkn8Ko2AOGlOrcwwTH0aHggwXS6taslwK5mqybbIaA292IB87L0t6kAu%2BpxK6mBOiP0L6qAtON5dYGidq2rdUDn%2Fq2g%2F0Ek7n1yh77nsbxA6KtiOupAp7ql%2FlTuLakoMQE8JzvzeYG4%2BWS6rsEgsPntqoFj7fXrMUDoI3aw3yCAhdjYXRlZ29yeV9pZDooMTg0MTA2MzkwKYoCCTE4NDEwNjM5MJICAJoCDGRlc2t0b3AtbWFwc6oCFzU3Njg2ODE5MjUyLDE1NTk0MjY0NTg42gIoChIJUcQihh1HREARRt8C7Q8jUEASEgkALhmuq1W%2FPxEAkNWUAfO1P%2BACAQ%3D%3D&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=category_id%3A%28184106390%29&z=15.32'
            },
            {
                'name': 'Пур Наволок',
                'url': 'https://yandex.ru/maps/org/pur_navolok/1166831997/reviews/?display-text=%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD&ll=40.514869%2C64.542274&mode=search&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=%7B%22text%22%3A%22%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD%22%2C%22what%22%3A%5B%7B%22attr_name%22%3A%22category_id%22%2C%22attr_values%22%3A%5B%22184106394%22%5D%7D%5D%7D&z=14.03'
            },
            {
                'name': 'Cheesy',
                'url': 'https://yandex.ru/maps/org/cheesy/220827170496/reviews/?display-text=%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD&ll=40.514869%2C64.542274&mode=search&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=%7B%22text%22%3A%22%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD%22%2C%22what%22%3A%5B%7B%22attr_name%22%3A%22category_id%22%2C%22attr_values%22%3A%5B%22184106394%22%5D%7D%5D%7D&z=14.03'
            },
            {
                'name': 'Боброфф',
                'url': 'https://yandex.ru/maps/org/bobroff/1094446636/reviews/?display-text=%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD&ll=40.514869%2C64.542274&mode=search&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=%7B%22text%22%3A%22%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD%22%2C%22what%22%3A%5B%7B%22attr_name%22%3A%22category_id%22%2C%22attr_values%22%3A%5B%22184106394%22%5D%7D%5D%7D&z=14.03'
            },
            {
                'name': 'Грядка',
                'url': 'https://yandex.ru/maps/org/gryadka/61835884661/reviews/?display-text=%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD&ll=40.514869%2C64.542274&mode=search&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=%7B%22text%22%3A%22%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD%22%2C%22what%22%3A%5B%7B%22attr_name%22%3A%22category_id%22%2C%22attr_values%22%3A%5B%22184106394%22%5D%7D%5D%7D&z=14.03'
            },
            {
                'name': 'Почтовая Контора 1786',
                'url': 'https://yandex.ru/maps/org/pochtovaya_kontora_1786/222233439985/reviews/?display-text=%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD&ll=40.514869%2C64.542274&mode=search&sll=40.513022%2C64.542904&sspn=0.008216%2C0.009040&tab=reviews&text=%7B%22text%22%3A%22%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD%22%2C%22what%22%3A%5B%7B%22attr_name%22%3A%22category_id%22%2C%22attr_values%22%3A%5B%22184106394%22%5D%7D%5D%7D&z=14.03'
            },
            {
                'name': 'Мороженое 33 Пингвина',
                'url': 'https://yandex.ru/maps/org/morozhenoye_33_pingvina/157294441905/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Северная Двина',
                'url': 'https://yandex.ru/maps/org/severnaya_dvina/126996132193/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Verona',
                'url': 'https://yandex.ru/maps/org/verona/1090661448/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Додо Пицца',
                'url': 'https://yandex.ru/maps/org/dodo_pitstsa/115036100397/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Додо Пицца',
                'url': 'https://yandex.ru/maps/org/dodo_pitstsa/181056317735/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'PhoBo',
                'url': 'https://yandex.ru/maps/org/phobo/153499251427/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Сушитека',
                'url': 'https://yandex.ru/maps/org/sushiteka/242465076606/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Roomi',
                'url': 'https://yandex.ru/maps/org/roomi/78581638606/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'El Fuego',
                'url': 'https://yandex.ru/maps/org/el_fuego/1012103595/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Санта Паста',
                'url': 'https://yandex.ru/maps/org/santa_pasta/80125102056/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Азия',
                'url': 'https://yandex.ru/maps/org/aziya/125991496969/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Санта Паста',
                'url': 'https://yandex.ru/maps/org/santa_pasta/172805875911/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Эребуни',
                'url': 'https://yandex.ru/maps/org/erebuni/242006151730/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'БрауМастер',
                'url': 'https://yandex.ru/maps/org/braumaster/1013715480/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Холмс',
                'url': 'https://yandex.ru/maps/org/kholms/171000577311/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Река',
                'url': 'https://yandex.ru/maps/org/reka/222879203721/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старый Тифлис',
                'url': 'https://yandex.ru/maps/org/stary_tiflis/1734715010/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Simple. cafe',
                'url': 'https://yandex.ru/maps/org/simple_cafe/74987189586/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Генацвале',
                'url': 'https://yandex.ru/maps/org/genatsvale/172528815164/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'PhoBo',
                'url': 'https://yandex.ru/maps/org/phobo/153499251427/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'ПиццаФабрика',
                'url': 'https://yandex.ru/maps/org/pitstsafabrika/172069924702/reviews/?ll=40.615536%2C64.531254&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Престо',
                'url': 'https://yandex.ru/maps/org/presto/160606490432/reviews/?ll=40.615536%2C64.531254&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Полина',
                'url': 'https://yandex.ru/maps/org/polina/1043435387/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Verona',
                'url': 'https://yandex.ru/maps/org/verona/1090661448/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Додо Пицца',
                'url': 'https://yandex.ru/maps/org/dodo_pitstsa/115036100397/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'АндерСон',
                'url': 'https://yandex.ru/maps/org/anderson/155618806278/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Сушитека',
                'url': 'https://yandex.ru/maps/org/sushiteka/242465076606/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Vkuss Суши',
                'url': 'https://yandex.ru/maps/org/vkuss_sushi/118394883333/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Северная Двина',
                'url': 'https://yandex.ru/maps/org/severnaya_dvina/126996132193/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Римская кофейня',
                'url': 'https://yandex.ru/maps/org/rimskaya_kofeynya/1054966761/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'БлинВиль',
                'url': 'https://yandex.ru/maps/org/blinvil/133252733488/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Миндаль',
                'url': 'https://yandex.ru/maps/org/mindal/1726666723/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Престо',
                'url': 'https://yandex.ru/maps/org/presto/1224519151/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Iris Trattoria',
                'url': 'https://yandex.ru/maps/org/iris_trattoria/194329570928/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Крым',
                'url': 'https://yandex.ru/maps/org/krym/212578743868/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Двор',
                'url': 'https://yandex.ru/maps/org/dvor/137340314923/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Маяк',
                'url': 'https://yandex.ru/maps/org/mayak/228512159061/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'БлинВиль',
                'url': 'https://yandex.ru/maps/org/blinvil/155755551800/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Боброфф',
                'url': 'https://yandex.ru/maps/org/bobroff/1094446636/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Temple',
                'url': 'https://yandex.ru/maps/org/temple/53779158462/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Кензо',
                'url': 'https://yandex.ru/maps/org/kenzo/1783847102/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Штаб',
                'url': 'https://yandex.ru/maps/org/shtab/205248320235/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Дружба',
                'url': 'https://yandex.ru/maps/org/druzhba/1044367569/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Кухня',
                'url': 'https://yandex.ru/maps/org/kukhnya/97455368545/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Taboo',
                'url': 'https://yandex.ru/maps/org/taboo/100099882781/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Грядка',
                'url': 'https://yandex.ru/maps/org/gryadka/241530617158/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Жаркий',
                'url': 'https://yandex.ru/maps/org/zharkiy/167291116156/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Бакинский бульвар',
                'url': 'https://yandex.ru/maps/org/bakinskiy_bulvar/216218543150/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Настоять',
                'url': 'https://yandex.ru/maps/org/nastoyat/165450104297/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Иль Густо',
                'url': 'https://yandex.ru/maps/org/il_gusto/130822382895/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Ринкан',
                'url': 'https://yandex.ru/maps/org/rinkan/154761025756/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Вельвет',
                'url': 'https://yandex.ru/maps/org/velvet/1726344930/reviews/?ll=40.524722%2C64.558458&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Пекарня на Чумбаровке',
                'url': 'https://yandex.ru/maps/org/pekarnya_na_chumbarovke/1792624339/reviews/?ll=40.528757%2C64.534867&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'По-домашнему',
                'url': 'https://yandex.ru/maps/org/po_domashnemu/1695961727/reviews/?ll=40.528757%2C64.534867&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Кушать подано',
                'url': 'https://yandex.ru/maps/org/kushat_podano/121694968719/reviews/?ll=40.528757%2C64.534867&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старый город',
                'url': 'https://yandex.ru/maps/org/stary_gorod/125230692232/reviews/?ll=40.583157%2C64.536668&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Чердак',
                'url': 'https://yandex.ru/maps/org/cherdak/24170185628/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Казацкая слобода',
                'url': 'https://yandex.ru/maps/org/kazatskaya_sloboda/222158011895/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Met Tea 茶无双',
                'url': 'https://yandex.ru/maps/org/met_tea_/13694230846/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': '1234',
                'url': 'https://yandex.ru/maps/org/1234/202999130879/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Паратовъ',
                'url': 'https://yandex.ru/maps/org/paratov/1801653588/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Гуляй, казак!',
                'url': 'https://yandex.ru/maps/org/gulyay_kazak_/22534288670/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Panorama',
                'url': 'https://yandex.ru/maps/org/panorama/160147853396/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Iris',
                'url': 'https://yandex.ru/maps/org/iris/22622988868/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'La-Ваш',
                'url': 'https://yandex.ru/maps/org/la_vash/1736797259/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Территория еды',
                'url': 'https://yandex.ru/maps/org/territoriya_yedy/122737080058/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Арарат',
                'url': 'https://yandex.ru/maps/org/ararat/217963244758/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Яма',
                'url': 'https://yandex.ru/maps/org/yama/152757927158/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Рестопорт',
                'url': 'https://yandex.ru/maps/org/restoport/181159067473/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Абшерон',
                'url': 'https://yandex.ru/maps/org/absheron/1726563248/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Шаурма & Кофе',
                'url': 'https://yandex.ru/maps/org/shaurma_kofe/213179905210/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старфудс',
                'url': 'https://yandex.ru/maps/org/starfuds/11814643288/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старфудс',
                'url': 'https://yandex.ru/maps/org/starfuds/143604104926/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Калитка Парк',
                'url': 'https://yandex.ru/maps/org/kalitka_park/5082803970/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Грузин',
                'url': 'https://yandex.ru/maps/org/gruzin/72342542161/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Osobnyak',
                'url': 'https://yandex.ru/maps/org/osobnyak/113995198152/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Важный анчоуc',
                'url': 'https://yandex.ru/maps/org/vazhny_anchous/111278116217/reviews/?ll=40.531777%2C64.562585&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Краснодарский парень',
                'url': 'https://yandex.ru/maps/org/krasnodarskiy_paren/183187923330/reviews/?ll=40.526925%2C64.532767&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Verona',
                'url': 'https://yandex.ru/maps/org/verona/1090661448/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Додо Пицца',
                'url': 'https://yandex.ru/maps/org/dodo_pitstsa/115036100397/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Додо Пицца',
                'url': 'https://yandex.ru/maps/org/dodo_pitstsa/181056317735/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'PhoBo',
                'url': 'https://yandex.ru/maps/org/phobo/153499251427/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Сушитека',
                'url': 'https://yandex.ru/maps/org/sushiteka/242465076606/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Roomi',
                'url': 'https://yandex.ru/maps/org/roomi/78581638606/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'El Fuego',
                'url': 'https://yandex.ru/maps/org/el_fuego/1012103595/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Санта Паста',
                'url': 'https://yandex.ru/maps/org/santa_pasta/80125102056/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Азия',
                'url': 'https://yandex.ru/maps/org/aziya/125991496969/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Санта Паста',
                'url': 'https://yandex.ru/maps/org/santa_pasta/172805875911/reviews/?ll=40.569117%2C64.545040&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Эребуни',
                'url': 'https://yandex.ru/maps/org/erebuni/242006151730/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'БрауМастер',
                'url': 'https://yandex.ru/maps/org/braumaster/1013715480/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Холмс',
                'url': 'https://yandex.ru/maps/org/kholms/171000577311/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Река',
                'url': 'https://yandex.ru/maps/org/reka/222879203721/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старый Тифлис',
                'url': 'https://yandex.ru/maps/org/stary_tiflis/1734715010/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Simple. cafe',
                'url': 'https://yandex.ru/maps/org/simple_cafe/74987189586/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Генацвале',
                'url': 'https://yandex.ru/maps/org/genatsvale/172528815164/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'PhoBo',
                'url': 'https://yandex.ru/maps/org/phobo/153499251427/reviews/?ll=40.513478%2C64.542925&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'ПиццаФабрика',
                'url': 'https://yandex.ru/maps/org/pitstsafabrika/172069924702/reviews/?ll=40.615536%2C64.531254&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Престо',
                'url': 'https://yandex.ru/maps/org/presto/160606490432/reviews/?ll=40.615536%2C64.531254&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Полина',
                'url': 'https://yandex.ru/maps/org/polina/1043435387/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Verona',
                'url': 'https://yandex.ru/maps/org/verona/1090661448/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Додо Пицца',
                'url': 'https://yandex.ru/maps/org/dodo_pitstsa/115036100397/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'АндерСон',
                'url': 'https://yandex.ru/maps/org/anderson/155618806278/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Сушитека',
                'url': 'https://yandex.ru/maps/org/sushiteka/242465076606/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Vkuss Суши',
                'url': 'https://yandex.ru/maps/org/vkuss_sushi/118394883333/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Северная Двина',
                'url': 'https://yandex.ru/maps/org/severnaya_dvina/126996132193/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Римская кофейня',
                'url': 'https://yandex.ru/maps/org/rimskaya_kofeynya/1054966761/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'БлинВиль',
                'url': 'https://yandex.ru/maps/org/blinvil/133252733488/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Миндаль',
                'url': 'https://yandex.ru/maps/org/mindal/1726666723/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Престо',
                'url': 'https://yandex.ru/maps/org/presto/1224519151/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Iris Trattoria',
                'url': 'https://yandex.ru/maps/org/iris_trattoria/194329570928/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Крым',
                'url': 'https://yandex.ru/maps/org/krym/212578743868/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Двор',
                'url': 'https://yandex.ru/maps/org/dvor/137340314923/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Маяк',
                'url': 'https://yandex.ru/maps/org/mayak/228512159061/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'БлинВиль',
                'url': 'https://yandex.ru/maps/org/blinvil/155755551800/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Боброфф',
                'url': 'https://yandex.ru/maps/org/bobroff/1094446636/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Temple',
                'url': 'https://yandex.ru/maps/org/temple/53779158462/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Кензо',
                'url': 'https://yandex.ru/maps/org/kenzo/1783847102/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Штаб',
                'url': 'https://yandex.ru/maps/org/shtab/205248320235/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Дружба',
                'url': 'https://yandex.ru/maps/org/druzhba/1044367569/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Кухня',
                'url': 'https://yandex.ru/maps/org/kukhnya/97455368545/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Taboo',
                'url': 'https://yandex.ru/maps/org/taboo/100099882781/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Грядка',
                'url': 'https://yandex.ru/maps/org/gryadka/241530617158/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Жаркий',
                'url': 'https://yandex.ru/maps/org/zharkiy/167291116156/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Бакинский бульвар',
                'url': 'https://yandex.ru/maps/org/bakinskiy_bulvar/216218543150/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Настоять',
                'url': 'https://yandex.ru/maps/org/nastoyat/165450104297/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Иль Густо',
                'url': 'https://yandex.ru/maps/org/il_gusto/130822382895/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Ринкан',
                'url': 'https://yandex.ru/maps/org/rinkan/154761025756/reviews/?ll=40.523358%2C64.534777&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Вельвет',
                'url': 'https://yandex.ru/maps/org/velvet/1726344930/reviews/?ll=40.524722%2C64.558458&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Пекарня на Чумбаровке',
                'url': 'https://yandex.ru/maps/org/pekarnya_na_chumbarovke/1792624339/reviews/?ll=40.528757%2C64.534867&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'По-домашнему',
                'url': 'https://yandex.ru/maps/org/po_domashnemu/1695961727/reviews/?ll=40.528757%2C64.534867&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Кушать подано',
                'url': 'https://yandex.ru/maps/org/kushat_podano/121694968719/reviews/?ll=40.528757%2C64.534867&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старый город',
                'url': 'https://yandex.ru/maps/org/stary_gorod/125230692232/reviews/?ll=40.583157%2C64.536668&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Чердак',
                'url': 'https://yandex.ru/maps/org/cherdak/24170185628/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Казацкая слобода',
                'url': 'https://yandex.ru/maps/org/kazatskaya_sloboda/222158011895/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Met Tea 茶无双',
                'url': 'https://yandex.ru/maps/org/met_tea_/13694230846/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': '1234',
                'url': 'https://yandex.ru/maps/org/1234/202999130879/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Паратовъ',
                'url': 'https://yandex.ru/maps/org/paratov/1801653588/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Гуляй, казак!',
                'url': 'https://yandex.ru/maps/org/gulyay_kazak_/22534288670/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Panorama',
                'url': 'https://yandex.ru/maps/org/panorama/160147853396/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Iris',
                'url': 'https://yandex.ru/maps/org/iris/22622988868/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'La-Ваш',
                'url': 'https://yandex.ru/maps/org/la_vash/1736797259/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Территория еды',
                'url': 'https://yandex.ru/maps/org/territoriya_yedy/122737080058/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Арарат',
                'url': 'https://yandex.ru/maps/org/ararat/217963244758/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Яма',
                'url': 'https://yandex.ru/maps/org/yama/152757927158/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Рестопорт',
                'url': 'https://yandex.ru/maps/org/restoport/181159067473/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Абшерон',
                'url': 'https://yandex.ru/maps/org/absheron/1726563248/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Шаурма & Кофе',
                'url': 'https://yandex.ru/maps/org/shaurma_kofe/213179905210/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старфудс',
                'url': 'https://yandex.ru/maps/org/starfuds/11814643288/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Старфудс',
                'url': 'https://yandex.ru/maps/org/starfuds/143604104926/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Калитка Парк',
                'url': 'https://yandex.ru/maps/org/kalitka_park/5082803970/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Грузин',
                'url': 'https://yandex.ru/maps/org/gruzin/72342542161/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Osobnyak',
                'url': 'https://yandex.ru/maps/org/osobnyak/113995198152/reviews/?ll=40.529061%2C64.532030&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Важный анчоуc',
                'url': 'https://yandex.ru/maps/org/vazhny_anchous/111278116217/reviews/?ll=40.531777%2C64.562585&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            },
            {
                'name': 'Краснодарский парень',
                'url': 'https://yandex.ru/maps/org/krasnodarskiy_paren/183187923330/reviews/?ll=40.526925%2C64.532767&mode=search&sll=40.536158%2C64.545031&tab=reviews&text=%D0%9A%D0%B0%D1%84%D0%B5&z=13'
            }
            # ДОБАВЬ СВОИ ССЫЛКИ ЗДЕСЬ:
            # {
            #     'name': 'Название ресторана',
            #     'url': 'ССЫЛКА_НА_ОТЗЫВЫ'
            # },
            # {
            #     'name': 'Еще один ресторан',
            #     'url': 'ДРУГАЯ_ССЫЛКА'
            # }
        ]
        
        # Сколько ресторанов добавил?
        additional_restaurants = 4  # Измени на нужное количество 18 +
        
        if additional_restaurants > 0:
            print(f"⚠️  ВНИМАНИЕ: Нужно добавить {additional_restaurants} ресторанов в список!")
            print("   Добавь их в код в разделе 'СПИСОК РЕСТОРАНОВ'")
        
        print(f"\n2. 📋 Будет обработано ресторанов: {len(restaurants)}")
        if len(restaurants) > 0:
            print("   Список:")
            for i, r in enumerate(restaurants, 1):
                print(f"   {i}. {r['name']}")
        else:
            print("   ❌ Список ресторанов пуст! Добавь ссылки в код.")
            return
        
        all_results = []
        successful_parses = 0
        
        for idx, restaurant in enumerate(restaurants, 1):
            print(f"\n{'#'*80}")
            print(f"РЕСТОРАН {idx}/{len(restaurants)}: {restaurant['name']}")
            print(f"{'#'*80}")
            
            try:
                result = parser.parse_restaurant_reviews(
                    url=restaurant['url'],
                    restaurant_name=restaurant['name']
                )
                
                if result:
                    all_results.append(result)
                    successful_parses += 1
                    print(f"✅ Успешно обработан: {restaurant['name']}")
                else:
                    print(f"⚠️  Не удалось обработать: {restaurant['name']}")
                
                # Пауза между ресторанами
                if idx < len(restaurants):
                    print(f"\n⏳ Пауза 5 секунд перед следующим рестораном...")
                    time.sleep(5)
                    
            except Exception as e:
                print(f"❌ Ошибка при обработке {restaurant['name']}: {str(e)[:100]}")
                continue
        
        # Сводный отчет
        print(f"\n{'='*80}")
        print("📊 СВОДНЫЙ ОТЧЕТ")
        print(f"{'='*80}")
        print(f"Всего ресторанов в списке: {len(restaurants)}")
        print(f"Успешно обработано: {successful_parses}")
        
        if all_results:
            total_reviews = sum(r['sentiment_analysis']['total_comments'] for r in all_results)
            total_positive = sum(r['sentiment_analysis']['positive_count'] for r in all_results)
            total_negative = sum(r['sentiment_analysis']['negative_count'] for r in all_results)
            total_neutral = sum(r['sentiment_analysis']['neutral_count'] for r in all_results)
            
            print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
            print(f"   Всего отзывов: {total_reviews}")
            print(f"   Позитивных: {total_positive} ({round(total_positive/total_reviews*100, 2) if total_reviews > 0 else 0}%)")
            print(f"   Негативных: {total_negative} ({round(total_negative/total_reviews*100, 2) if total_reviews > 0 else 0}%)")
            print(f"   Нейтральных: {total_neutral} ({round(total_neutral/total_reviews*100, 2) if total_reviews > 0 else 0}%)")
            
            # Рейтинг ресторанов
            print(f"\n🏆 РЕЙТИНГ РЕСТОРАНОВ:")
            sorted_results = sorted(all_results, 
                                  key=lambda x: x['sentiment_analysis']['positive_percentage'], 
                                  reverse=True)
            
            for i, result in enumerate(sorted_results, 1):
                stats = result['sentiment_analysis']
                print(f"   {i}. {result['restaurant_info']['name']}:")
                print(f"      📝 Отзывов: {stats['total_comments']}")
                print(f"      👍 Позитивных: {stats['positive_percentage']}%")
                print(f"      👎 Негативных: {stats['negative_percentage']}%")
                print(f"      ⚖️  Нейтральных: {stats['neutral_percentage']}%")
        
        print(f"\n📁 РЕЗУЛЬТАТЫ:")
        print(f"   Все файлы сохранены в папке: /app/output/")
        print(f"   JSON файлы: reviews_*.json")
        # После сохранения JSON файла добавь:
        print(f"\n📁 РЕЗУЛЬТАТЫ:")
        print(f"   Все файлы сохранены в папке: /app/output/")
        print(f"   JSON файлы: reviews_*.json")
        output_dir = "output"  # Добавь эту строку
        # Вставь этот код после print("📊 Для загрузки в Hive выполните: python hive_loader.py")
        print(f"\n📊 Для загрузки в Hive выполните: python hive_loader.py")

        print(f"\n{'='*80}")
        print("🏁 РАБОТА ЗАВЕРШЕНА!")
        print(f"{'='*80}")
            
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {type(e).__name__}: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("\nЗакрываем браузер...")
            driver.quit()
            print("Браузер закрыт")
    
    print("\n🎉 Парсинг завершен!")


if __name__ == "__main__":
    # Создаем папки для результатов
    if not os.path.exists("output"):
        os.makedirs("output")
    
    main()