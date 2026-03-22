import sqlite3
import aiohttp
from config import logger
import asyncio
import re
from datetime import datetime

class SaleTracker:
    def __init__(self):
        self.conn = sqlite3.connect('sale_tracker.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_notifications (
                sale_id TEXT PRIMARY KEY,
                sale_name TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def mark_notification_sent(self, sale_id, sale_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sent_notifications (sale_id, sale_name) 
            VALUES (?, ?)
        ''', (sale_id, sale_name))
        self.conn.commit()

    def was_notification_sent(self, sale_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM sent_notifications WHERE sale_id = ?', (sale_id,))
        return cursor.fetchone() is not None


sale_tracker = SaleTracker()


class RealSaleChecker:
    def __init__(self):
        self.base_url = "https://store.steampowered.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }

    async def check_active_sales(self):
        """Проверяет активные распродажи на главной странице Steam"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(f"{self.base_url}", timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_active_sales(html)
                    else:
                        logger.error(f"HTTP Error: {response.status}")
                        return []
        except asyncio.TimeoutError:
            logger.error("Timeout while checking Steam")
            return []
        except Exception as e:
            logger.error(f"Error checking sales: {e}")
            return []

    def _parse_active_sales(self, html):
        """Парсит HTML на наличие активных крупных распродаж"""
        active_sales = []

        # Паттерны для поиска крупных распродаж
        sale_patterns = [
            {
                'name': '🎄 Зимняя распродажа Steam',
                'patterns': [
                    r'winter.sale', r'holiday.sale', r'christmas.sale',
                    r'зимняя.распродажа', r'новогодняя.распродажа',
                    r'Steam.Winter.Sale', r'Winter.Sale.2024'
                ],
                'id': 'winter_sale'
            },
            {
                'name': '☀️ Летняя распродажа Steam',
                'patterns': [
                    r'summer.sale', r'Steam.Summer.Sale', r'летняя.распродажа',
                    r'Summer.Sale.2024'
                ],
                'id': 'summer_sale'
            },
            {
                'name': '🍂 Осенняя распродажа Steam',
                'patterns': [
                    r'autumn.sale', r'fall.sale', r'осенняя.распродажа',
                    r'Steam.Autumn.Sale', r'Autumn.Sale.2024'
                ],
                'id': 'autumn_sale'
            },
            {
                'name': '🌸 Весенняя распродажа Steam',
                'patterns': [
                    r'spring.sale', r'весенняя.распродажа',
                    r'Steam.Spring.Sale', r'Spring.Sale.2024'
                ],
                'id': 'spring_sale'
            },
            {
                'name': '🎃 Хэллоуинская распродажа',
                'patterns': [
                    r'halloween.sale', r'хэллоуин.распродажа',
                    r'Halloween.Sale.2024'
                ],
                'id': 'halloween_sale'
            },
            {
                'name': '🏆 Распродажа Steam Next Fest',
                'patterns': [
                    r'next.fest', r'next.fest.sale',
                    r'Steam.Next.Fest'
                ],
                'id': 'next_fest'
            },
            {
                'name': '💥 Крупная распродажа Steam',
                'patterns': [
                    r'major.sale', r'big.sale', r'крупная.распродажа',
                    r'Steam.Sale'
                ],
                'id': 'major_sale'
            }
        ]

        # Проверяем каждый паттерн
        for sale in sale_patterns:
            for pattern in sale['patterns']:
                if re.search(pattern, html, re.IGNORECASE):
                    # Создаем уникальный ID с годом
                    current_year = datetime.now().year
                    sale_id = f"{sale['id']}_{current_year}"

                    active_sales.append({
                        'id': sale_id,
                        'name': sale['name'],
                        'detected_at': datetime.now().isoformat(),
                        'url': "https://store.steampowered.com"
                    })
                    logger.info(f"🎯 Обнаружена активная распродажа: {sale['name']}")
                    break

        return active_sales


real_sale_checker = RealSaleChecker()
