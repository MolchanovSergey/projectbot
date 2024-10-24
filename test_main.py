import main
import unittest
from unittest.mock import patch
import sqlite3
from unittest import mock
import asyncio
import io
from aiogram import types
from main import dp
from datetime import datetime

db_path = './app_data/database.db'

class userTests(unittest.TestCase):

    test_telegram_id = 99999999999999
    test_telegram_id_for_creation = 999999999999991

    def setUp(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY)')
        cursor.execute('INSERT INTO users (telegram_id) VALUES (?)', (self.test_telegram_id,))
        conn.commit()
        conn.close()
    
    def testCheckUserExistanse(self):
        user = main.User(self.test_telegram_id)
        result = user.check_user_data()
        print(result)
        print(self.test_telegram_id)
        self.assertEqual(result, (self.test_telegram_id,))

    def testCreateUser(self):
        user = main.User(self.test_telegram_id_for_creation)
        # user.check_user_data()
        result_check = user.create_user_record()
        self.assertEqual(result_check, self.test_telegram_id_for_creation)
    
    def tearDown(self):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (self.test_telegram_id,))
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (self.test_telegram_id_for_creation,))
        conn.commit()
        conn.close()

class srockTests(unittest.TestCase):

    def testCheckStockEsixtanse(self):
        
        test_stock_id  = "SBER"
        test_response_json = {"boards":{"data": [["SBER"]]}}
        
        with mock.patch('requests.get') as mock_get:

            mock_response_success = mock.Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = test_response_json

            mock_response_error = mock.Mock()
            mock_response_error.status_code = 400
            mock_response_error.json.return_value = None

            mock_get.return_value = mock_response_success
            result_success = main.check_stock_existanse(test_stock_id)
            self.assertTrue(result_success)

            mock_get.return_value = mock_response_error
            result_error = main.check_stock_existanse(test_stock_id)
            self.assertFalse(result_error)

    def testGetStockPrice(self):
        
        test_stock_id  = "SBER"
        test_response_json = {"securities":{"data": [[100.0, "SUR"]]}}
        
        with mock.patch('requests.get') as mock_get:

            mock_response_success = mock.Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = test_response_json

            mock_response_error = mock.Mock()
            mock_response_error.status_code = 400
            mock_response_error.json.return_value = None

            mock_get.return_value = mock_response_success
            result_success = main.get_stock_price(test_stock_id)
            self.assertEqual(result_success, "100.0 RUB")

            mock_get.return_value = mock_response_error
            result_error = main.get_stock_price(test_stock_id)
            self.assertFalse(result_error)

class StockTestCase(unittest.TestCase):

    check_telegram_id = 999999999999
    create_telegram_id = 999999999998

    create_stock = main.Stock(create_telegram_id, 'SBER', 100, 10, '2024-10-10 03:09:21.123454')

    test_stock_values = (check_telegram_id, 'SBER', 100, 10, '2024-10-10 03:09:21.123454')

    def setUp(self) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS stocks
                          (owner_id INTEGER, stock_id TEXT, quantity INTEGER, unit_price REAL, purchase_date TIMESTAMP, FOREIGN KEY (owner_id) REFERENCES users(telegram_id) ON DELETE CASCADE)''')
        cursor.execute('INSERT INTO users (telegram_id) VALUES (?)', (self.check_telegram_id,))
        cursor.execute('INSERT INTO stocks VALUES (?, ?, ?, ?, ?)', self.test_stock_values)
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (self.check_telegram_id,))
        cursor.execute('DELETE FROM stocks WHERE owner_id = ?', (self.check_telegram_id,))
        cursor.execute('DELETE FROM users WHERE telegram_id = ?', (self.create_telegram_id,))
        cursor.execute('DELETE FROM stocks WHERE owner_id = ?', (self.create_telegram_id,))
        conn.commit()
        conn.close()

    def test_add_stock(self):
        result = []
        main.Stock.add_stock(self.create_stock)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM stocks WHERE owner_id = ?', (self.create_telegram_id,))
        result = cursor.fetchall()
        conn.close()
        self.assertNotEqual(result, [])

    def test_get_user_stocks(self):
        result = main.Stock.get_user_stocks(self.check_telegram_id)
        self.assertIsNotNone(result)

class CheckStockExistance(unittest.TestCase):

    test_stock_id = 'SBER'
    test_url = f'https://iss.moex.com/iss/securities/{test_stock_id}.json'
    test_reponse = {'boards': {'data': [['SBER']]}}

    def test_check_stock_existanse(self):

        with mock.patch('requests.get') as mock_get:

            mock_response_success = mock.Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = self.test_reponse

            mock_response_fail = mock.Mock()
            mock_response_fail.status_code = 404
            mock_response_fail.json.return_value = None

            mock_get.return_value = mock_response_success
            result_success = main.check_stock_existanse(self.test_stock_id)
            self.assertTrue(result_success)
            mock_get.assert_called_once_with(self.test_url)

            mock_get.return_value = mock_response_fail
            result_fail = main.check_stock_existanse(self.test_stock_id)
            self.assertFalse(result_fail)
            mock_get.assert_called_with(self.test_url)

# Тестирование функции dateConvert
class TestDateConvert(unittest.TestCase):
   
    def test_date_convert_valid(self):
        # Тестирование корректного преобразования даты
        self.assertEqual(main.dateConvert('18.10.2024'), '2024-10-18')

    def test_date_convert_invalid_format(self):
        # Проверка, что неверный формат вызывает ValueError
        with self.assertRaises(ValueError):
            main.dateConvert('2024-10-18')  # Некорректный формат

# Тестирование функции getChart
class TestShowStockChart(unittest.TestCase):

    def test_get_chart(self):

        # Определяем данные для теста
        test_stock_id = 'SBER'
        test_start_date = '2023-09-01'
        test_finish_date = '2023-09-30'

        # Пример ответа API
        test_response_json = {
            'candles': {
                'columns': ['open', 'close'],
                'data': [
                    [100, 110],
                    [105, 115],
                    [110, 120],
                ]
            }
        }

        # Мокаем requests.get, чтобы заменить реальный вызов
        with mock.patch('requests.get') as mock_get:

            # Создаем объект успешного ответа
            mock_response_success = mock.Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = test_response_json
        
            # Создаем объект ошибки
            mock_response_error = mock.Mock()
            mock_response_error.status_code = 400
            mock_response_error.json.return_value = None

            # Успешный результат
            mock_get.return_value = mock_response_success
            loop = asyncio.get_event_loop()
            buf = loop.run_until_complete(main.ShowStockChart.getChart(test_stock_id, test_start_date, test_finish_date))

            # Проверяем, что данные из API не пусты
            data_chart = mock_response_success.json.return_value
            self.assertTrue(data_chart)  # Проверка, что ответ не пустой

            # Проверяем, что в data_chart['candles'] есть данные
            self.assertIn('candles', data_chart)
            self.assertTrue(data_chart['candles'].get('data'))  # Проверка, что есть данные в 'data'

            # Проверяем, что возвращен объект BytesIO
            self.assertIsInstance(buf, io.BytesIO)

            # Проверяем, что график был успешно создан и содержит данные
            buf.seek(0)
            img_data = buf.read()
            self.assertTrue(len(img_data) > 0)

            # Ошибочный результат (статус 400)
            mock_get.return_value = mock_response_error
            buf = loop.run_until_complete(main.ShowStockChart.getChart(test_stock_id, test_start_date, test_finish_date))

class TestShowChartHandler(unittest.TestCase):
    
    def setUp(self):
        # Создаем тестовый объект сообщения
        self.message = types.Message(
            message_id=1, 
            from_user=types.User(id=123, is_bot=False, first_name="TestUser"), 
            chat=types.Chat(id=12345, type="private"), 
            date=None, 
            text="/showChart"
        )

if __name__ == '__main__':
    unittest.main()



