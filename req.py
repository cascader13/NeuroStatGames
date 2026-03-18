# [file name]: test_sender_optimized.py
import requests
import time
import random
import json
import threading
from datetime import datetime
from queue import Queue
from collections import defaultdict

# Конфигурация
SERVER_URL = 'https://neurostatgames.onrender.com/api/sendString'
USER_IDS = ['user1', 'user2', 'user3']

# Настройки
TIMEOUT = 2.0  # Увеличенный таймаут
MAX_RETRIES = 3  # Максимальное количество повторных попыток
RETRY_DELAY = 0.1  # Задержка между повторами
BATCH_SIZE = 5  # Отправка пачками

# Статистика
stats = {
    'sent': 0,
    'errors': 0,
    'retries': 0,
    'start_time': time.time(),
    'by_user': defaultdict(int),
    'by_type': defaultdict(int)
}

# Очередь для отложенной отправки при ошибках
retry_queue = Queue()
print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def print_stats():
    elapsed = time.time() - stats['start_time']
    rate = stats['sent'] / elapsed if elapsed > 0 else 0
    success_rate = (stats['sent'] / (stats['sent'] + stats['errors'])) * 100 if stats['sent'] + stats[
        'errors'] > 0 else 0

    safe_print(f"\n{'=' * 60}")
    safe_print(f"📊 СТАТИСТИКА ЗА {elapsed:.1f} сек:")
    safe_print(f"   ✅ Успешно: {stats['sent']}")
    safe_print(f"   ❌ Ошибок: {stats['errors']}")
    safe_print(f"   🔄 Повторов: {stats['retries']}")
    safe_print(f"   📈 Скорость: {rate:.1f} сообщений/сек")
    safe_print(f"   🎯 Успешность: {success_rate:.1f}%")
    safe_print(f"\n   По пользователям:")
    for user, count in stats['by_user'].items():
        safe_print(f"     • {user}: {count}")
    safe_print(f"{'=' * 60}")


def send_with_retry(user_id, key, value, retry_count=0):
    """Отправка с повторными попытками при таймауте"""
    payload = {
        'id': user_id,
        'text': f"{key} {value:.2f}"
    }

    try:
        response = requests.post(
            SERVER_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=TIMEOUT
        )

        if response.status_code == 200:
            stats['sent'] += 1
            stats['by_user'][user_id] += 1
            stats['by_type'][key] += 1
            return True
        else:
            stats['errors'] += 1
            safe_print(f"❌ [{user_id}] Ошибка {response.status_code}: {response.text[:100]}")
            return False

    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            stats['retries'] += 1
            time.sleep(RETRY_DELAY * (retry_count + 1))  # Экспоненциальная задержка
            return send_with_retry(user_id, key, value, retry_count + 1)
        else:
            stats['errors'] += 1
            safe_print(f"⏰ [{user_id}] Таймаут после {MAX_RETRIES} попыток")
            return False

    except requests.exceptions.ConnectionError:
        stats['errors'] += 1
        safe_print(f"🔌 [{user_id}] Ошибка соединения")
        return False

    except Exception as e:
        stats['errors'] += 1
        safe_print(f"❌ [{user_id}] Исключение: {type(e).__name__}")
        return False


def send_batch(user_id, messages):
    """Отправка пачки сообщений"""
    for key, value in messages:
        send_with_retry(user_id, key, value)
        time.sleep(0.05)  # Небольшая задержка между сообщениями в пачке


def simulate_user_optimized(user_id):
    """Оптимизированная симуляция пользователя"""
    safe_print(f"🚀 Запуск пользователя {user_id}")

    # Отправляем baseline
    baseline = random.uniform(80, 120)
    send_with_retry(user_id, "concentrationBaseline", baseline)
    time.sleep(0.2)
    send_with_retry(user_id, "stressBaseline", baseline)
    time.sleep(0.5)

    message_count = 0
    target_rate = 5  # Уменьшенная скорость для надежности
    interval = 1.0 / target_rate

    while True:
        start_cycle = time.time()

        # Формируем пачку сообщений
        batch = []

        # Концентрация (изменяется плавно)
        concentration = 50 + 30 * math.sin(message_count * 0.1) + random.uniform(-5, 5)
        batch.append(("concentration", concentration))

        # Стресс (обратно пропорционален relax)
        stress = random.uniform(30, 70)
        batch.append(("stress", stress))

        # Relax (плавные изменения)
        relax = 50 + 20 * math.cos(message_count * 0.15) + random.uniform(-3, 3)
        batch.append(("relax", relax))

        # Отправляем пачку
        send_batch(user_id, batch)
        message_count += len(batch)

        # Контроль скорости
        elapsed = time.time() - start_cycle
        sleep_time = max(0, interval - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)

        # Статистика каждые 50 сообщений
        if message_count % 50 == 0:
            rate = message_count / (time.time() - stats['start_time'])
            safe_print(f"📊 [{user_id}] Отправлено {message_count} сообщений, скорость: {rate:.1f}/сек")


def retry_processor():
    """Обработчик очереди повторных отправок"""
    while True:
        try:
            if not retry_queue.empty():
                user_id, key, value, retry_count = retry_queue.get(timeout=1)
                if send_with_retry(user_id, key, value, retry_count + 1):
                    safe_print(f"🔄 Повторная отправка успешна: {user_id} {key}")
                else:
                    if retry_count < MAX_RETRIES:
                        retry_queue.put((user_id, key, value, retry_count + 1))
            time.sleep(0.1)
        except Exception as e:
            time.sleep(0.1)


if __name__ == '__main__':
    import math  # Добавляем для плавных изменений

    print("🚀 Запуск оптимизированного тестирования...")
    print(f"📡 Сервер: {SERVER_URL}")
    print(f"⏱️ Таймаут: {TIMEOUT}с, Повторов: {MAX_RETRIES}")
    print("Нажмите Ctrl+C для остановки\n")

    # Запускаем обработчик повторных отправок
    retry_thread = threading.Thread(target=retry_processor, daemon=True)
    retry_thread.start()

    # Запускаем пользователей
    threads = []
    for user_id in USER_IDS:
        t = threading.Thread(target=simulate_user_optimized, args=(user_id,))
        t.daemon = True
        t.start()
        threads.append(t)


    # Статистика
    def stats_printer():
        while True:
            time.sleep(10)
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