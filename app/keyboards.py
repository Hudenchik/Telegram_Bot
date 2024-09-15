from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


main_add_device = ReplyKeyboardMarkup(keyboard = [
    [KeyboardButton(text = 'Добавить устройство')],
],
                            resize_keyboard=True,
                            input_field_placeholder='Выберите пункт...')

main_device_added = ReplyKeyboardMarkup(keyboard = [
    [KeyboardButton(text = 'Добавить устройство'), KeyboardButton(text = 'Список устройств')],
    [KeyboardButton(text = 'Начать получение данных')]
],
                            resize_keyboard=True,
                            input_field_placeholder='Выберите пункт...')

back = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text = 'Вернуться назад')]
],                  resize_keyboard=True)

end_receving = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text = 'Прекратить получение данных')]
],                    resize_keyboard = True)


def devices_keyboard(devices):
    device_buttons = [[KeyboardButton(text=f'Нажмите чтобы удалить {device}')] for device in devices]
    return ReplyKeyboardMarkup(
        keyboard=device_buttons + [[KeyboardButton(text='Вернуться назад')]],
        resize_keyboard=True
    )