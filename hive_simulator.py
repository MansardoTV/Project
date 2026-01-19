import json
import os

class HiveSimulator:
    def __init__(self):
        self.data = []
        self.load_from_json()
    
    def load_from_json(self):
        if not os.path.exists("output"):
            return
        
        json_files = [f for f in os.listdir("output") if f.endswith('.json')]
        for json_file in json_files:
            try:
                with open(f"output/{json_file}", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                restaurant_info = data.get('restaurant_info', {})
                sentiment = data.get('sentiment_analysis', {})
                
                self.data.append({
                    'restaurant_name': restaurant_info.get('name', 'Unknown'),
                    'total_reviews': sentiment.get('total_comments', 0),
                    'positive_reviews': sentiment.get('positive_count', 0),
                    'negative_reviews': sentiment.get('negative_count', 0),
                    'neutral_reviews': sentiment.get('neutral_count', 0),
                    'positive_percentage': float(sentiment.get('positive_percentage', 0)),
                    'negative_percentage': float(sentiment.get('negative_percentage', 0)),
                    'parsed_date': restaurant_info.get('parsed_at', ''),
                    'source_url': restaurant_info.get('url', '')
                })
            except:
                continue
    
    def get_data(self):
        """Возвращаем данные для веб-интерфейса"""
        return sorted(self.data, key=lambda x: x['positive_percentage'], reverse=True)
    
    def get_stats(self):
        """Статистика"""
        if not self.data:
            return None
            
        total_restaurants = len(self.data)
        total_reviews = sum(d['total_reviews'] for d in self.data)
        avg_positive = sum(d['positive_percentage'] for d in self.data) / total_restaurants
        
        return {
            'total_restaurants': total_restaurants,
            'total_reviews': total_reviews,
            'avg_positive': round(avg_positive, 2),
            'total_comments': total_reviews * 10
        }


hive_sim = HiveSimulator()