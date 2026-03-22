import sqlite3
from config import logger
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('steam_bot.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscribed INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_games (
                user_id INTEGER,
                game_id INTEGER,
                game_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, game_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sent_deals (
                user_id INTEGER,
                game_id INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, game_id)
            )
        ''')


        cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_users (
                    user_id INTEGER PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        self.conn.commit()
        logger.info("✅ База данных инициализирована")




    def add_user(self, user_id, username):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username) 
            VALUES (?, ?)
        ''', (user_id, username))
        self.conn.commit()

    def track_game(self, user_id, game_id, game_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tracked_games (user_id, game_id, game_name) 
            VALUES (?, ?, ?)
        ''', (user_id, game_id, game_name))
        self.conn.commit()

    def get_tracked_games(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT game_id, game_name FROM tracked_games WHERE user_id = ?', (user_id,))
        return cursor.fetchall()

    def remove_tracked_game(self, user_id, game_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tracked_games WHERE user_id = ? AND game_id = ?', (user_id, game_id))
        self.conn.commit()

    def mark_deal_sent(self, user_id, game_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO sent_deals (user_id, game_id) 
            VALUES (?, ?)
        ''', (user_id, game_id))
        self.conn.commit()

    def was_deal_sent(self, user_id, game_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM sent_deals WHERE user_id = ? AND game_id = ?', (user_id, game_id))
        return cursor.fetchone() is not None

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE subscribed = 1')
        return [row[0] for row in cursor.fetchall()]

    def add_notification_user(self, user_id: int):
        """Добавляет пользователя в список для уведомлений о распродажах"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO notification_users (user_id) VALUES (?)",
                (user_id,)
            )
            self.conn.commit()
            logger.info(f"✅ Пользователь {user_id} добавлен в уведомления")
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя {user_id} в уведомления: {e}")

    def get_notification_users(self):
        """Возвращает список всех пользователей для уведомлений"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT user_id FROM notification_users")
            results = cursor.fetchall()
            return [row[0] for row in results]  # Возвращаем список user_id
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей для уведомлений: {e}")
            return []


db = Database()