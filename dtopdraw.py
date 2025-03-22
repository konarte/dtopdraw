import os
import time
import datetime
import requests
import json
import ctypes
from PIL import Image, ImageDraw, ImageFont
from pystray import Icon as TrayIcon, Menu as TrayMenu, MenuItem as TrayMenuItem
import threading
from io import BytesIO

# Глобальные переменные
SETTINGS_FILE = 'resources/cache/settings.json'
ORIGINAL_WALLPAPER_PATH = 'resources/tmp/original_wallpaper.png'

def create_tray_icon():
    """Создает иконку в трее."""
    def on_exit(icon, item):
        """Обработчик выхода из программы."""
        icon.stop()
        restore_original_wallpaper()
        os._exit(0)

    # Создаем простую иконку (заливка цветом)
    icon_image = Image.new('RGB', (64, 64), color=(255, 0, 0))  # Пример: красная иконка 64x64
    icon = TrayIcon("WallpaperApp", icon_image, "Wallpaper App", menu=TrayMenu(
        TrayMenuItem("Выход", on_exit)
    ))
    icon.run()

def start_tray_icon():
    """Запускает иконку в трее в отдельном потоке."""
    tray_thread = threading.Thread(target=create_tray_icon, daemon=True)
    tray_thread.start()

def save_original_wallpaper():
    """Сохраняет текущие обои рабочего стола."""
    if not os.path.exists('resources/tmp'):
        os.makedirs('resources/tmp')
    ctypes.windll.user32.SystemParametersInfoW(0x0073, 0, ORIGINAL_WALLPAPER_PATH, 0)

def restore_original_wallpaper():
    """Восстанавливает оригинальные обои рабочего стола."""
    if os.path.exists(ORIGINAL_WALLPAPER_PATH):
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, os.path.abspath(ORIGINAL_WALLPAPER_PATH), 2)

def load_settings():
    """Загружает настройки из файла."""
    if not os.path.exists(SETTINGS_FILE):
        save_settings({'version': 'v1.0'})
    with open(SETTINGS_FILE, 'r', encoding='utf8') as f:
        return json.load(f)

def save_settings(data=None):
    """Сохраняет настройки в файл."""
    if data is None:
        data = {'version': 'v1.0'}
    with open(SETTINGS_FILE, 'w', encoding='utf8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_currency_rates(currencies):
    """Получает курсы валют."""
    try:
        url = 'https://www.cbr-xml-daily.ru/daily_json.js'
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return [(code.upper(), round(data['Valute'][code.upper()]['Value'], 2)) for code in currencies]
    except Exception as e:
        print(f"Ошибка при получении курсов валют: {e}")
        return False

def get_weather_data(city_url):
    """Получает данные о погоде."""
    try:
        response = requests.get(city_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        start = response.text.find('M.state.weather.cw = {')
        if start == -1:
            return False
        end = response.text.find('\n', start)
        return json.loads(response.text[start + 21:end])
    except Exception as e:
        print(f"Ошибка при получении данных о погоде: {e}")
        return False

def get_current_weather(index):
    """Получает текущую погоду для указанного города."""
    city = WEATHER_URLS[index]
    weather_data = get_weather_data(city[1])
    if weather_data:
        return (city[0], weather_data['temperatureAir'][0], weather_data['description'][0])
    return False

WEATHER_URLS = [
    ('Самара', 'https://www.gismeteo.ru/weather-samara-4618/'),
    ('Тольятти', 'https://www.gismeteo.ru/weather-tolyatti-4429/'),
    ('Москва', 'https://www.gismeteo.ru/weather-moscow-4368/')
]

THEMES = [
    {'bg': (19, 19, 19), 'fg': (152, 0, 2), 'text': (255, 191, 0)},
    {'bg': (235, 220, 178), 'fg': (175, 68, 37), 'text': (85, 46, 28)},
]

def get_theme(index):
    """Возвращает тему по индексу."""
    return THEMES[index]

def load_font(name, size):
    """Загружает шрифт."""
    font_extensions = ['.ttf', '.otf']
    base_name, ext = os.path.splitext(name)
    if ext in font_extensions:
        path = os.path.join('resources', 'fonts', name)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception as e:
                print(f"Ошибка при загрузке шрифта {path}: {e}")
    for ext in font_extensions:
        path = os.path.join('resources', 'fonts', f"{base_name}{ext}")
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception as e:
                print(f"Ошибка при загрузке шрифта {path}: {e}")
    print(f"Шрифт не найден: resources/fonts/{name}(.otf|.ttf). Используется шрифт по умолчанию.")
    return ImageFont.load_default()

def draw_text(draw, font, text, position, color):
    """Отрисовывает текст."""
    draw.text(position, text, font=font, fill=color)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def create_wallpaper():
    """Создает новые обои рабочего стола."""
    settings = load_settings()
    theme = get_theme(settings.get('themeIndex', 0))
    user32 = ctypes.windll.user32
    width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    image = Image.new('RGB', (width, height), theme['bg'])
    draw = ImageDraw.Draw(image)

    # День недели
    current_font = load_font('font.otf', 100)
    day_text = datetime.datetime.today().strftime('%A').capitalize()
    w, h = draw_text(draw, current_font, day_text, (width // 2, height // 3 - 100), theme['fg'])

    # Курсы валют
    courses = get_currency_rates(settings.get('courses', ['USD', 'EUR']))
    if courses:
        current_font = load_font('font.otf', 50)
        course_text = '  '.join([f'{code}: {rate}' for code, rate in courses])
        draw_text(draw, current_font, course_text, (width // 2, h + 15), theme['fg'])

    # Время и дата
    current_font = load_font('font.otf', 100)
    time_text = datetime.datetime.now().strftime('%H:%M')
    date_text = datetime.datetime.now().strftime('%d.%m.%Y')
    tw, th = draw_text(draw, current_font, time_text, (width // 2, h + 100), theme['fg'])
    draw_text(draw, current_font, date_text, (width // 2, th + 20), theme['fg'])

    # Сохранение и применение обоев
    temp_file = 'resources/tmp/temp.png'
    image.save(temp_file)
    ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, os.path.abspath(temp_file), 2)

def create_wallpaper_in_memory():
    """Создает новые обои рабочего стола и сохраняет их в памяти."""
    settings = load_settings()
    theme = get_theme(settings.get('themeIndex', 0))
    user32 = ctypes.windll.user32
    width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    image = Image.new('RGB', (width, height), theme['bg'])
    draw = ImageDraw.Draw(image)

    # День недели
    current_font = load_font('font.otf', 100)
    day_text = datetime.datetime.today().strftime('%A').capitalize()
    w, h = draw_text(draw, current_font, day_text, (width // 2, height // 3 - 100), theme['fg'])

    # Курсы валют
    courses = get_currency_rates(settings.get('courses', ['USD', 'EUR']))
    if courses:
        current_font = load_font('font.otf', 50)
        course_text = '  '.join([f'{code}: {rate}' for code, rate in courses])
        draw_text(draw, current_font, course_text, (width // 2, h + 15), theme['fg'])

    # Время и дата
    current_font = load_font('font.otf', 100)
    time_text = datetime.datetime.now().strftime('%H:%M')
    date_text = datetime.datetime.now().strftime('%d.%m.%Y')
    tw, th = draw_text(draw, current_font, time_text, (width // 2, h + 100), theme['fg'])
    draw_text(draw, current_font, date_text, (width // 2, th + 20), theme['fg'])

    # Сохранение в памяти
    temp_file = BytesIO()
    image.save(temp_file, format='PNG')
    temp_file.seek(0)
    return temp_file

def save_wallpaper_to_disk(image_data, file_path):
    """Сохраняет изображение из памяти на диск."""
    with open(file_path, 'wb') as f:
        f.write(image_data.getvalue())

def main_loop():
    """Основной цикл программы."""
    save_original_wallpaper()  # Сохраняем оригинальный фон рабочего стола
    last_saved_time = None
    try:
        while True:
            # Создаем обои в памяти
            wallpaper_in_memory = create_wallpaper_in_memory()

            # Проверяем, нужно ли сохранять на диск (например, раз в 5 минут)
            current_minute = datetime.datetime.now().minute
            if last_saved_time is None or current_minute % 5 == 0:
                temp_file = 'resources/tmp/temp.png'
                save_wallpaper_to_disk(wallpaper_in_memory, temp_file)
                ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, os.path.abspath(temp_file), 2)
                last_saved_time = current_minute

            time.sleep(60)  # Ждем одну минуту
    except KeyboardInterrupt:
        print("Программа завершена")
        restore_original_wallpaper()  # Восстанавливаем оригинальный фон рабочего стола

if __name__ == "__main__":
    os.makedirs('resources/cache', exist_ok=True)
    os.makedirs('resources/tmp', exist_ok=True)
    os.makedirs('resources/fonts', exist_ok=True)
    os.makedirs('resources/icons', exist_ok=True)

    # Проверка загрузки шрифта
    font = load_font('font', 40)
    print(f"Используемый шрифт: {font.getname()}")
    save_settings()  # Создаем файл настроек если его нет
    start_tray_icon()  # Запускаем иконку в трее
    main_loop()  # Запускаем основной цикл
