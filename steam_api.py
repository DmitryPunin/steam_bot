import aiohttp
from config import logger

class SteamAPI:
    def __init__(self):
        self.base_url = "https://store.steampowered.com/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    async def search_games(self, query: str):
        """Поиск игр в Steam"""
        try:
            url = f"https://steamcommunity.com/actions/SearchApps/{query}"
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data[:10]  # Первые 10 результатов
                    return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_game_details(self, game_id: int):
        """Получение детальной информации об игре с ПРАВИЛЬНЫМИ ценами"""
        try:
            url = f"{self.base_url}/appdetails"
            params = {
                'appids': game_id,
                'cc': 'ru',  # ВАЖНО: указываем регион Россия
                'l': 'russian'
            }

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        game_data = data.get(str(game_id), {}).get('data', {})

                        if not game_data:
                            return None

                        # Правильное извлечение цены
                        price_overview = game_data.get('price_overview', {})

                        if price_overview:
                            # Цены возвращаются в копейках, делим на 100 для рублей
                            final_price = price_overview.get('final', 0) / 100
                            initial_price = price_overview.get('initial', 0) / 100
                            discount = price_overview.get('discount_percent', 0)
                        else:
                            # Если нет price_overview, игра может быть бесплатной
                            final_price = 0
                            initial_price = 0
                            discount = 0

                        return {
                            'name': game_data.get('name', 'Unknown'),
                            'final_price': final_price,
                            'initial_price': initial_price,
                            'discount': discount,
                            'header_image': game_data.get('header_image', ''),
                            'steam_url': f"https://store.steampowered.com/app/{game_id}/",
                            'is_free': game_data.get('is_free', False)
                        }
                    return None
        except Exception as e:
            logger.error(f"Game details error: {e}")
            return None

    async def get_featured_deals(self):
        """Получение акционных предложений с ПРАВИЛЬНЫМИ ценами"""
        try:
            url = f"{self.base_url}/featuredcategories"
            params = {
                'cc': 'ru',
                'l': 'russian'
            }

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_featured_deals(data)
                    return []
        except Exception as e:
            logger.error(f"Featured deals error: {e}")
            return []

    def _parse_featured_deals(self, data):
        """Парсинг акционных предложений с ПРАВИЛЬНЫМИ ценами"""
        deals = []
        try:
            # Специальные предложения
            if 'specials' in data:
                items = data['specials'].get('items', [])
                for item in items:
                    if item.get('discount_percent', 0) > 20:  # Только скидки >20%
                        # Цены в копейках, делим на 100 для рублей
                        original_price = item.get('original_price', 0) / 100
                        final_price = item.get('final_price', 0) / 100

                        deals.append({
                            'id': item['id'],
                            'name': item['name'],
                            'discount': item['discount_percent'],
                            'original_price': original_price,
                            'final_price': final_price,
                            'currency': 'RUB'
                        })
            return deals
        except Exception as e:
            logger.error(f"Parse deals error: {e}")
            return []


steam_api = SteamAPI()