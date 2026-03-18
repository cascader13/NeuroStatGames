import requests
import time
import random
import json
import threading
from datetime import datetime

SERVER_URL = 'http://localhost:5000/api/sendString'
USER_IDS = ['user1', 'user2', 'user3']  # Несколько пользователей

# Статистика для отслеживания скорости отправки
stats = {
    'sent': 0,
    'errors': 0,
    'start_time': time.time()
}


def print_stats():
    """Вывод статистики отправки"""
    elapsed = time.time() - stats['start_time']
    rate = stats['sent'] / elapsed if elapsed > 0 else 0
    print(
        f"\n📊 Статистика: Всего отправлено: {stats['sent']}, Ошибок: {stats['errors']}, Средняя скорость: {rate:.1f} сообщений/сек")


def send_data(user_id, key, value):
    payload = {
        'id': user_id,
        'text': f"{key} {value:.2f}"
    }
    try:
        response = requests.post(SERVER_URL, json=payload, headers={'Content-Type': 'application/json'}, timeout=0.5)
        if response.status_code == 200:
            stats['sent'] += 1
            if stats['sent'] % 10 == 0:  # Печатаем каждые 10 сообщений
                print(f"✅ [{user_id}] {key}: {value:.2f} (всего: {stats['sent']})")
        else:
            stats['errors'] += 1
            print(f"❌ [{user_id}] Ошибка: {response.text}")
    except Exception as e:
        stats['errors'] += 1
        print(f"❌ [{user_id}] Исключение: {e}")


def simulate_user_high_frequency(user_id):
    """Симуляция пользователя с высокой частотой отправки"""
    print(f"🚀 Запуск пользователя {user_id}")

    # Отправляем baseline
    baseline = random.uniform(80, 120)
    send_data(user_id, "concentrationBaseline", baseline)
    send_data(user_id, "stressBaseline", baseline)
    time.sleep(0.1)

    # Отправляем данные с высокой частотой
    message_count = 0
    target_rate = 10  # Целевая скорость 10 сообщений в секунду
    interval = 1.0 / target_rate  # 0.1 секунды между сообщениями

    while message_count < 100:  # Отправляем 100 сообщений для теста
        start_cycle = time.time()

        # Отправляем все три типа сообщений последовательно
        concentration = random.uniform(20, 150)
        stress = random.uniform(20, 150)
        relax = random.uniform(0, 100)

        send_data(user_id, "concentration", concentration)
        send_data(user_id, "stress", stress)
        send_data(user_id, "relax", relax)

        message_count += 3

        # Вычисляем время ожидания для поддержания нужной частоты
        elapsed = time.time() - start_cycle
        sleep_time = max(0, interval - elapsed)

        if sleep_time > 0:
            time.sleep(sleep_time)

        if message_count % 30 == 0:  # Печатаем каждые 30 сообщений
            print(f"📊 [{user_id}] Отправлено {message_count} сообщений")


def simulate_user_continuous(user_id):
    """Непрерывная симуляция с высокой частотой"""
    print(f"🚀 Запуск непрерывной симуляции для {user_id}")

    # Отправляем baseline
    baseline = random.uniform(80, 120)
    send_data(user_id, "concentrationBaseline", baseline)
    send_data(user_id, "stressBaseline", baseline)
    time.sleep(0.1)

    message_count = 0
    target_rate = 10  # 10 сообщений в секунду
    interval = 1.0 / target_rate  # 0.1 секунды

    while True:
        start_cycle = time.time()

        # Отправляем все три типа
        concentration = random.uniform(20, 150)
        stress = random.uniform(20, 150)
        relax = random.uniform(0, 100)

        send_data(user_id, "concentration", concentration)
        send_data(user_id, "stress", stress)
        send_data(user_id, "relax", relax)

        message_count += 3

        # Поддерживаем нужную частоту
        elapsed = time.time() - start_cycle
        sleep_time = max(0, interval - elapsed)

        if sleep_time > 0:
            time.sleep(sleep_time)

        if message_count % 30 == 0:
            rate = message_count / (time.time() - stats['start_time'])
            print(f"📊 [{user_id}] Отправлено {message_count} сообщений, текущая скорость: {rate:.1f}/сек")


def simulate_user_burst(user_id):
    """Отправка пачками для тестирования батчинга"""
    print(f"🚀 Запуск burst режима для {user_id}")

    # Отправляем baseline
    baseline = random.uniform(80, 120)
    send_data(user_id, "concentrationBaseline", baseline)
    send_data(user_id, "stressBaseline", baseline)
    time.sleep(0.1)

    while True:
        # Отправляем пачку из 30 сообщений быстро
        for i in range(10):  # 10 итераций * 3 сообщения = 30 сообщений
            concentration = random.uniform(20, 150)
            stress = random.uniform(20, 150)
            relax = random.uniform(0, 100)

            send_data(user_id, "concentration", concentration)
            send_data(user_id, "stress", stress)
            send_data(user_id, "relax", relax)

            # Минимальная задержка между сообщениями в пачке
            time.sleep(0.01)  # 10ms между сообщениями внутри пачки

        print(f"📊 [{user_id}] Отправлена пачка из 30 сообщений")

        # Пауза между пачками
        time.sleep(1.0)


if __name__ == '__main__':
    print("🚀 Запуск тестовых пользователей с высокой частотой...")
    print("Нажмите Ctrl+C для остановки\n")

    threads = []

    # Выберите один из режимов:
    MODE = "continuous"  # "high_frequency", "continuous", "burst"

    for user_id in USER_IDS:
        if MODE == "high_frequency":
            t = threading.Thread(target=simulate_user_high_frequency, args=(user_id,))
        elif MODE == "continuous":
            t = threading.Thread(target=simulate_user_continuous, args=(user_id,))
        elif MODE == "burst":
            t = threading.Thread(target=simulate_user_burst, args=(user_id,))

        t.daemon = True
        t.start()
        threads.append(t)


    # Запускаем поток для вывода статистики
    def stats_printer():
        while True:
            time.sleep(5)
            print_stats()


    stats_thread = threading.Thread(target=stats_printer)
    stats_thread.daemon = True
    stats_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка тестов")
        print_stats()