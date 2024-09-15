import asyncio
import aiomqtt
import re
import os
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.methods.send_message import SendMessage
import app.keyboards as kb

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

mqtt_host = os.getenv("MQTT_BROKER_HOST")
mqtt_port = int(os.getenv("MQTT_BROKER_PORT"))

class DeviceManager:
    def __init__(self):
        self.user_subscriptions = {}
        self.active_tasks = {}
        self.user_states = {}

    def add_device(self, user_id, device_name):
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = {}
        self.user_subscriptions[user_id][device_name] = True

    def remove_device(self, user_id, device_name):
        if device_name in self.user_subscriptions.get(user_id, {}):
            del self.user_subscriptions[user_id][device_name]

    def get_user_device(self, user_id):
        return self.user_subscriptions.get(user_id, {}).keys()

    def set_user_state(self, user_id, state):
        self.user_states[user_id] = state

    def get_user_state(self, user_id):
        return self.user_states.get(user_id, "default")

class MQQTClient:
    def __init__(self, bot, device_manager):
        self.bot = bot
        self.device_manager = device_manager

    async def subscribe_to_mqtt(self, user_id, topic):
        async with aiomqtt.Client(hostname=mqtt_host, port = mqtt_port) as client:
            await client.subscribe(topic)

            arr_message = []
            start_time = asyncio.get_event_loop().time()

            while True:
                async for message in client.messages:
                    payload = message.payload.decode()
                    text = f"Получено сообщение с топика <b>{topic}</b>: \n{payload}"
                    arr_message.append(text)

                    current_time = asyncio.get_event_loop().time()
                    if len(arr_message) >=5 or current_time - start_time >= 2:
                        combined_message = '\n\n'.join(arr_message)
                        await self.bot.send_message(user_id, combined_message, parse_mode='html')

                        arr_message = []
                        start_time = asyncio.get_event_loop().time()

class BotHandler:
    def __init__(self, bot, device_manager, mqtt_client):
        self.bot = bot
        self.device_manager = device_manager
        self.mqtt_client = mqtt_client
        self.router = Router()

        self.router.message(Command('start', 'help'))(self.cmd_start)
        self.router.message(F.text == 'Добавить устройство')(self.add_device)
        self.router.message(F.text == 'Вернуться назад')(self.go_back)
        self.router.message(F.text == 'Список устройств')(self.list_device)
        self.router.message(F.text == 'Начать получение данных')(self.start_receiving_data)
        self.router.message(F.text == 'Прекратить получение данных')(self.stop_receiving_data)
        self.router.message(F.text)(self.handle_user_input)
    
    async def cmd_start(self, message: Message):
        self.device_manager.set_user_state(message.from_user.id, "default")
        await message.answer(f'Привет, {message.from_user.username}!\n\nЭтот бот предназначен для прослушивания сообщений из топиков'
                             '\n\nДобавьте устройство с помощью кнопки ниже',
                             reply_markup=kb.main_add_device)

    async def add_device(self, message: Message):
        self.device_manager.set_user_state(message.from_user.id, "adding_device")
        await message.answer(f'Введите название устройства ввида DEVICE/FF-FF-FF/EVENT',
                             reply_markup=kb.back)
    
    async def go_back(self, message: Message):
        self.device_manager.set_user_state(message.from_user.id, "default")
        devices = self.device_manager.get_user_device(message.from_user.id)

        if devices:
            await message.answer(f'Выберите дальнейшее действие',
                             reply_markup=kb.main_device_added)
        else:
            await message.answer(f'Добавьте устройство',
                            reply_markup = kb.main_add_device)
    
    async def list_device(self, message: Message):
        devices = self.device_manager.get_user_device(message.from_user.id)
        if devices:
            device_keyboard = kb.devices_keyboard(devices)
            await message.answer("Список устройств", reply_markup=device_keyboard)
        else:
            await message.answer(f'У вас нет добавленных устройств')
    
    async def start_receiving_data(self, message: Message):
        user_devices = self.device_manager.get_user_device(message.from_user.id)
        if not user_devices:
            await message.answer(f'У вас нет подписанных устройств. Сначала добавьте устройство.', reply_markup=kb.main_device_added)
            return

        await message.answer(f'Начинаю получение данных...', reply_markup=kb.end_receving)
        
        tasks = []
        for device_name in user_devices:
            task = asyncio.create_task(self.mqtt_client.subscribe_to_mqtt(message.from_user.id, device_name))
            tasks.append(task)
        
        self.device_manager.active_tasks[message.from_user.id] = tasks
        

    async def stop_receiving_data(self, message: Message):
        tasks = self.device_manager.active_tasks.pop(message.from_user.id, [])
        for task in tasks:
            task.cancel()
        await message.answer(f'Прекращение получения данных', reply_markup=kb.main_device_added)

    async def handle_user_input(self, message: Message):
        text = message.text

        if self.device_manager.get_user_state(message.from_user.id) == "adding_device":
            if not (text.startswith("DEVICE/")):
                await message.answer("Неверный MAC-адрес. Пожалуйста, введите текст в формате DEVICE/FF-FF-FF/EVENT.",
                                 reply_markup=kb.back)
            else:
                await self.subcribe_to_device(message)

        elif text.startswith("Нажмите чтобы удалить"):
            device_name = text.replace('Нажмите чтобы удалить ', '')
            await self.delete_device(message, device_name)

        else:
            await message.answer("Неизвестная команда. Пожалуйста, используйте кнопки ниже.", reply_markup=kb.main_device_added)
    
    async def subcribe_to_device(self, message: Message):
        text = message.text

        try:
            parts_one = text.split('/')
            device_name = parts_one[1]       
            mac_pattern = r"^[A-F0-9]{2}-[A-F0-9]{2}-[A-F0-9]{2}$"

            if not re.match(mac_pattern, device_name):
                await message.answer("Неправильный MAC-адрес. Пожалуйста, введите в формате FF-FF-FF.",
                                    reply_markup=kb.back)
                return

            parts_two = device_name.split('-')
            if not (parts_two[0] == parts_two[1] == parts_two[2]):
                await message.answer("Все части MAC-адреса должны быть одинаковыми (например, FF-FF-FF или AA-AA-AA).",
                                    reply_markup=kb.back)
                return
            
            parts_three = parts_one[2]
            if not parts_three == 'EVENT':
                await message.answer("Неправильный формат. Пожалуйста, введите текст вида DEVICE/FF-FF-FF/EVENT.",
                                reply_markup=kb.back)
                return

            user_id = message.from_user.id
            if user_id not in self.device_manager.user_subscriptions:
                self.device_manager.user_subscriptions[user_id] = {}

            if device_name in self.device_manager.user_subscriptions[user_id]:
                await message.answer(f'Вы уже подписаны на устройство {device_name}')
            else:
                self.device_manager.user_subscriptions[user_id][device_name] = True
                await message.answer(f'Подписка на устройство {device_name} успешно оформлена.\n\nВведите другие устройства или вернитесь назад.',
                                    reply_markup=kb.back, pasrse_mode = 'html')
                self.device_manager.set_user_state(user_id, "adding_device")
            
            if not self.device_manager.get_user_state(user_id):
                self.device_manager.set_user_state(user_id, "default")
            else:
                return
        
        except IndexError:
            await message.answer("Неправильный формат. Пожалуйста, введите текст вида DEVICE/FF-FF-FF/EVENT.",
                             reply_markup=kb.back)

    async def delete_device(self, message: Message, device_name: str):
        user_id = message.from_user.id
        self.device_manager.remove_device(user_id, device_name)

        await message.answer(f"Устройство {device_name} успешно удалено.", 
                             reply_markup=kb.main_device_added, parse_mode='html')

        devices = self.device_manager.get_user_device(user_id)
        if devices:
            device_keyboard = kb.devices_keyboard(devices)
            await message.answer("Остальные устройства:", reply_markup=device_keyboard)
        else:
            await message.answer(f'Добавьте устройство', reply_markup=kb.main_add_device)


            

  



    
    
    

