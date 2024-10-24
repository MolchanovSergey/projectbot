from datetime import datetime
from aiogram import Bot, types, Dispatcher, executor
import requests
import sys
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import os
import pandas as pd
from matplotlib import pyplot as plt
import io
from dotenv import load_dotenv

#Материалы с первого занятия https://drive.google.com/drive/folders/1ceEmfDI8JSJip_3gQnyWgY5f-YFbH7T5?usp=share_link
#https://drive.google.com/drive/folders/1j1CTWkn4gdCuysjCVEPWHO06ZVn8upZc?usp=share_link

#Создание экземпляра бота
load_dotenv()

api_token = os.getenv('API_TOKEN')

bot = Bot(token=api_token)

storage = MemoryStorage()

#Создание экземпляра диспетчера
dp = Dispatcher(bot, storage=storage)

class User:
    def __init__(self, telegram_id):
        self.telegram_id = telegram_id

    def check_user_data(self):
        # print(os.getcwd())
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        result = cursor.fetchone()
        if result is None:
            conn.close()
            return None
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (self.telegram_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def create_user_record(self):
        inserted_id = None
        if not self.check_user_data():
            conn = sqlite3.connect('./app_data/database.db')
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY)''')
            cursor.execute('INSERT INTO users (telegram_id) VALUES (?)', (self.telegram_id,))
            inserted_id = cursor.lastrowid
            conn.commit()
            conn.close()   
        return inserted_id

#Обработчик команды /start с использованием класса User

@dp.message_handler(Command('start'))
async def reg_user(message: types.Message):
    new_user = User(message.from_user.id)
    new_user.create_user_record()
    await message.reply('Добро пожаловать!')

#Создание класса ЦБ, атрибутов и методов
class Stock:
    def __init__(self, owner_id, stock_id, quantity, unit_price, purchase_date):
        self.owner_id = owner_id
        self.stock_id = stock_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.purchase_date = purchase_date
    
    def __eq__(self, other):
        if isinstance(other, Stock):
            return (
                self.owner_id == other.owner_id
                and self.stock_id == other.stock_id
                and self.quantity == other.quantity
                and self.unit_price == other.unit_price
                and self.purchase_date == other.purchase_date
            )
        return False
    
    def add_stock(self):
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS stocks
                          (owner_id INTEGER, stock_id TEXT, quantity INTEGER, unit_price REAL, purchase_date TIMESTAMP, FOREIGN KEY (owner_id) REFERENCES users(telegram_id) ON DELETE CASCADE)''')
        values = (self.owner_id, self.stock_id, self.quantity, self.unit_price, self.purchase_date)
        cursor.execute('INSERT INTO stocks VALUES (?, ?, ?, ?, ?)', values)
        inserted_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return inserted_id
    
    def get_user_stocks(owner_id):
        stocks = []
        conn = sqlite3.connect('./app_data/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stocks'")
        result = cursor.fetchone()
        if result is None:
            conn.close()
            return stocks
        cursor.execute('SELECT * FROM stocks WHERE owner_id = ?', (owner_id,))
        result = cursor.fetchall()
        conn.close()

        for row in result:
            owner_id, stock_id, quantity, unit_price, purchase_date = row
            stock = Stock(owner_id, stock_id, quantity, unit_price, purchase_date)
            stocks.append(stock)

        return stocks

#Класс, который будет хранить информацию о состоянии сценария
class CheckStockStates(StatesGroup):
    StockID = State()

class AddStockStates(StatesGroup):
    StockID = State()
    StockPrice = State()
    StockQuantity = State()

def check_stock_existanse(stock_id: str) -> bool:
    url = f"https://iss.moex.com/iss/securities/{stock_id}.json"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        exists = data.get("boards", {}).get("data", [])
        return bool(exists)
    else:
        return False

def get_stock_price(stock_id: str) -> float:
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{stock_id}.json?iss.only=securities&securities.columns=PREVPRICE,CURRENCYID"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if len(data.get("securities", {}).get("data", [[]])) > 0:
            stock_currency = data.get("securities", {}).get("data", [[]])[0][1]
            if stock_currency == 'SUR':
                stock_currency = 'RUB'
            stock_price = data.get("securities", {}).get("data", [[]])[0][0]
            stock_result = str(stock_price) + ' ' + str(stock_currency)
            return stock_result
        else:
            return None
    else:
        return None
    
#Класс, который будет хранить информацию о состоянии сценария демонстрации графика
class ShowStockChart(StatesGroup):
    Stock_ID = State()       # Состояние для ввода кода акции
    StartDate = State()      # Состояние для ввода начальной даты
    FinishDate = State()     # Состояние для ввода конечной даты

    #Функция для построения графика 
    async def getChart(stock_id: str, start_date: str, finish_date: str):
        # """Получение данных о ценах акций с API и построение графика"""
        # Пример URL, API и формат данных может отличаться
        url = f'http://iss.moex.com/iss/engines/stock/markets/shares/securities/{stock_id}/candles.json?from={start_date}&till={finish_date}&interval=24'
            
        # Отправляем запрос и получаем данные
        response = requests.get(url)

        if response.status_code != 200:
            return io.BytesIO()  # Возвращаем пустой буфер, если запрос не успешен
        
        data_chart = response.json()

        # Проверяем наличие ключа 'candles' и его содержимого
        candles_data = data_chart.get('candles')
        if not candles_data or not candles_data.get('columns') or not candles_data.get('data'):
            return io.BytesIO()  # Возвращаем пустой буфер, если данных нет или они некорректны

        if 'candles' not in data_chart or not data_chart['candles'].get('columns') or not data_chart['candles'].get('data'):
            return io.BytesIO()  # Возвращаем пустой буфер, если данных нет
        
        data_for_dataframe = [{k : r[i] for i, k in enumerate(data_chart['candles']['columns'])} for r in data_chart['candles']['data']]

        # Создаем DataFrame из полученных данных
        df_f = pd.DataFrame(data_for_dataframe)

        # Проверка, есть ли столбец 'close'
        if 'close' not in df_f:
            return io.BytesIO()  # Возвращаем пустой буфер, если столбец отсутствует    
                
        # Генерация графика на основе столбца 'close'
        plt.plot(list(df_f['close']))
        plt.title(f'Price of {stock_id}')
        plt.xlabel('Time')
        plt.ylabel('Price')
            
        # Сохранение графика в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()  # Закрываем график
        return buf
    
#Функция конвертирования пользовательского ввода дат в формат для параметров запроса к API MOEX
def dateConvert(date_input: str) -> str:
    # """Преобразование даты из формата dd.mm.yyyy в yyyy-mm-dd"""
    date_obj = datetime.strptime(date_input, '%d.%m.%Y')
    return date_obj.strftime('%Y-%m-%d')    


#Обработчик запрашивающий код ЦБ 
@dp.message_handler(Command('checkStock'))
async def check_stock_start(message: types.Message):
    await message.reply('Введите идентификатор ценной бумаги')
    await CheckStockStates.StockID.set()

#Обработчик запроса для проверки существования ценной бумаги и ее цены
@dp.message_handler(state=CheckStockStates.StockID)
async def check_stock_id(message: types.Message, state: FSMContext):
    stock_id = message.text.upper()

    stock_exists = check_stock_existanse(stock_id)
    if stock_exists is not False:
        stock_price = get_stock_price(stock_id)
        if stock_price is not None:
            await message.reply(f"Ценная бумага с идентификатором {stock_id} существует на Московской бирже. Текущий курс: {stock_price}")
        else:
            await message.reply(f"Ценная бумага с идентификатором {stock_id} не найдена на Московской бирже.")
    else:
        await message.reply(f"Ценная бумага с идентификатором {stock_id} не найдена на Московской бирже.")

    await state.finish()

#Обработчик команды /addStock 
@dp.message_handler(Command('addStock'))
async def check_stock_start(message: types.Message):
    await message.reply('Преступим к добавлению ценной бумаги')
    await bot.send_message(message.chat.id, 'Введите идентификатор приобретенного инструмента')
    await AddStockStates.StockID.set()

#Обработчик введенного кода ЦБ
@dp.message_handler(state=AddStockStates.StockID)
async def add_stock_id(message: types.Message, state: FSMContext):
    if message.text != "/stop" and message.text != "/STOP":
        stock_exists = check_stock_existanse(message.text)
        if stock_exists is not False:
            await bot.send_message(message.chat.id, 'Введите стоимость единицы ценной бумаги')
            async with state.proxy() as data:
                data['StockID'] = message.text
            await AddStockStates.StockPrice.set()
        else:
            await message.reply('Указанный идентификатор ценной бумаги не найден на Московской бирже')
            await bot.send_message(message.chat.id, 'Введите корректный идентификатор приобретенного инструмента или введите /stop для отмены')
    else:
        await state.finish()
        await message.reply('Добавление информации о приобретенной ценной бумаге отменено')

#Добавление цены приобретенной ЦБ в ручном режиме
@dp.message_handler(state=AddStockStates.StockPrice)
async def add_stock_id(message: types.Message, state: FSMContext):
    if message.text != '/stop' and message.text != '/STOP':
        try:
            float(message.text.replace(',', '.'))
            await bot.send_message(message.chat.id, 'Введите количество приобретенных единиц инструмента')
            async with state.proxy() as data:
                data['StockPrice'] = message.text.replace(',', '.')
            await AddStockStates.StockQuantity.set()
        except:
             await message.reply('Вы некорректно указали стоимость одной ценной бумаги.')
             await bot.send_message(message.chat.id, 'Введите стоимость приобретения в числовом формате или введите /stop для отмены"')
        
    else:
        await state.finish()
        await message.reply('Добавление информации о приобретенной ценной бумаге отменено')

#Сохранение информации по приобретенной ЦБ
@dp.message_handler(state=AddStockStates.StockQuantity)
async def add_stock_id(message: types.Message, state: FSMContext):
    if message.text != "/stop" and message.text != "/STOP":
        try:
            int(message.text)
            async with state.proxy() as data:
                data['StockQuantity'] = message.text
                data['StockOwnerID'] = message.from_user.id
                data['StockPurchaseDate'] = datetime.now()
            StockRecord = Stock(data['StockOwnerID'], data['StockID'], data['StockPrice'], data['StockQuantity'], data['StockPurchaseDate'])
            StockRecord.add_stock()
            await state.finish()
            await bot.send_message(message.chat.id, 'Информация о приобретенной ценной бумаге успешно сохранена!')
        except:
             await message.reply('Вы некорректно указали количество приобретенных единиц ценной бумаги.')
             await bot.send_message(message.chat.id, 'Введите количество в виде целого числа или введите /stop для отмены"')
    
    else:
        await state.finish()
        await message.reply('Добавление информации о приобретенной ценной бумаге отменено')

#Обработчик для расчета текущей стоимости портфеля
@dp.message_handler(Command('checkPortfolioSummary'))
async def check_portfolio(message: types.Message):
    user_stocks = Stock.get_user_stocks(message.from_user.id)
    portfolio_price = 0
    portfolio_stocks_count = 0
    for stock in user_stocks:
        stock_price = int(stock.quantity) * float(stock.unit_price)
        portfolio_price += stock_price
        portfolio_stocks_count += 1
    await message.reply(f'Вы приобрели {portfolio_stocks_count} раз, на общую сумму {portfolio_price} RUB')

#Обработчик команды /showChart
@dp.message_handler(Command('showChart'))
async def show_chart_start(message: types.Message):
    await message.reply('Преступим к анализу изменения цены ЦБ')
    await bot.send_message(message.chat.id, 'Введите идентификатор приобретенного инструмента')
    await ShowStockChart.Stock_ID.set()

#Обработчик введенного кода ЦБ
@dp.message_handler(state=ShowStockChart.Stock_ID)
async def add_stock_id(message: types.Message, state: FSMContext):
    if message.text != "/stop" and message.text != "/STOP":
        stock_exists = check_stock_existanse(message.text)
        if stock_exists is not False:
            await bot.send_message(message.chat.id, 'Введите дату с которой хотите начать, например: 10.03.2023')
            async with state.proxy() as data:
                data['StockID'] = message.text.upper()
            await ShowStockChart.StartDate.set()
        else:
            await message.reply('Указанный идентификатор ценной бумаги не найден на Московской бирже')
            await bot.send_message(message.chat.id, 'Введите корректный идентификатор приобретенного инструмента или введите /stop для отмены')
    else:
        await state.finish()
        await message.reply('Добавление информации о интересующей ценной бумаге отменено')

#Добавление даты начала периода изменения цены
@dp.message_handler(state=ShowStockChart.StartDate)
async def add_start_date(message: types.Message, state: FSMContext):
    if message.text != '/stop' and message.text != '/STOP':
        try:
            str(message.text)
            await bot.send_message(message.chat.id, 'Введите дату до которой хотите смотреть, например: 10.09.2023')
            async with state.proxy() as data:
                data['StartDate'] = dateConvert(message.text)
            await ShowStockChart.FinishDate.set()
        except:
             await message.reply('Вы некорректно ввели дату.')
             await bot.send_message(message.chat.id, 'Введите в формате DD.MM.YYYY или введите /stop для отмены"')
        
    else:
        await state.finish()
        await message.reply('Добавление информации о интересующей ценной бумаге отменено')

# Выведение графика изменения цены ЦБ за период
@dp.message_handler(state=ShowStockChart.FinishDate)
async def add_finish_date(message: types.Message, state: FSMContext):
    if message.text != "/stop" and message.text != "/STOP":
        try:
            str(message.text)
            async with state.proxy() as data:
                data['FinishDate'] = dateConvert(message.text)


            chart_buf = await ShowStockChart.getChart(data['StockID'], data['StartDate'], data['FinishDate'])
            await state.finish()
            await bot.send_photo(message.chat.id, photo = chart_buf)
        
        except:
             await message.reply('Вы некорректно указали дату.')
             await bot.send_message(message.chat.id, 'Введите в формате DD.MM.YYYY или введите /stop для отмены')
    
    else:
        await state.finish()
        await message.reply('Добавление информации о интересующей ценной бумаге отменено')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

#Занятие 3
#https://drive.google.com/drive/folders/1LaLMlCY2QfzbQpWAXWScGpVbem3uQNzW

#Задание 4
#https://drive.google.com/drive/folders/1uzyl0VJDD5eW-yppABlDypeyrGaUQuf2?usp=share_link
