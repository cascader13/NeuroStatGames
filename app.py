from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import time
from datetime import datetime
from collections import defaultdict, deque
import threading
from queue import Queue, Empty
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Оптимизированные структуры данных
user_baselines = {}
user_last_values = defaultdict(lambda: {'concentration': 50, 'stress': 50, 'relax': 50})

# Буфер для батчинга сообщений
message_queue = Queue()
BATCH_SIZE = 10
BATCH_INTERVAL = 0.05  # 50ms


def batch_processor():
    """Фоновый процесс для группировки сообщений"""
    while True:
        messages = []
        start_time = time.time()

        # Собираем сообщения в батч
        while len(messages) < BATCH_SIZE and (time.time() - start_time) < BATCH_INTERVAL:
            try:
                msg = message_queue.get(timeout=0.01)
                messages.append(msg)
            except Empty:
                break

        if messages:
            # Группируем по типу события для эффективной отправки
            grouped = defaultdict(list)
            for msg in messages:
                event_type = msg.pop('event_type')
                grouped[event_type].append(msg)

            # Отправляем сгруппированные сообщения
            with app.app_context():
                for event_type, event_messages in grouped.items():
                    if len(event_messages) == 1:
                        socketio.emit(event_type, event_messages[0])
                    else:
                        # Для множественных сообщений отправляем как массив
                        socketio.emit(f'{event_type}_batch', event_messages)

        time.sleep(0.01)


# Запускаем фоновый процесс
threading.Thread(target=batch_processor, daemon=True).start()


def normalize_value(value, baseline, default=50):
    """Быстрая нормализация значения"""
    if not baseline or baseline <= 0:
        return default
    return max(0, min(100, (value / baseline) * default))


@app.route('/api/sendString', methods=['POST'])
def send_string():
    try:
        data = request.get_json(force=True)  # force=True для пропуска проверки MIME типа
        if not data or 'id' not in data or 'text' not in data:
            return jsonify({'success': False, 'error': 'Invalid data'}), 400

        user_id = data['id']
        text = data['text']

        # Быстрый парсинг
        parts = text.split()
        if len(parts) != 2:
            return jsonify({'success': False, 'error': 'Invalid format'}), 400

        key, value_str = parts

        try:
            value = float(value_str)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid value'}), 400

        # Обработка разных типов сообщений
        if key == "concentrationBaseline":
            if user_id not in user_baselines:
                user_baselines[user_id] = {}
            user_baselines[user_id]['concentration'] = value

            message_queue.put({
                'event_type': 'baseline_received',
                'user_id': user_id,
                'type': 'concentration',
                'value': value,
                'timestamp': time.time()
            })

        elif key == "stressBaseline":
            if user_id not in user_baselines:
                user_baselines[user_id] = {}
            user_baselines[user_id]['stress'] = value

        elif key == "concentration":
            baseline = user_baselines.get(user_id, {}).get('concentration')
            normalized = normalize_value(value, baseline)

            # Кэшируем последнее значение
            user_last_values[user_id]['concentration'] = normalized

            message_queue.put({
                'event_type': 'concentration_update',
                'user_id': user_id,
                'normalized_value': normalized,
                'timestamp': time.time()
            })

        elif key == "stress":
            baseline = user_baselines.get(user_id, {}).get('stress')
            normalized = normalize_value(value, baseline)
            user_last_values[user_id]['stress'] = normalized

            message_queue.put({
                'event_type': 'stress_update',
                'user_id': user_id,
                'normalized_stress': normalized,
                'timestamp': time.time()
            })

        elif key == "relax":
            # Relax уже в процентах
            normalized = max(0, min(100, value))
            user_last_values[user_id]['relax'] = normalized

            message_queue.put({
                'event_type': 'relax_update',
                'user_id': user_id,
                'normalized_relax': normalized,
                'timestamp': time.time()
            })

        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Добавляем эндпоинт для массового получения данных
@app.route('/api/last_values', methods=['GET'])
def get_last_values():
    """Быстрый доступ к последним значениям всех пользователей"""
    return jsonify(dict(user_last_values))


@app.route('/api/user/<user_id>/last', methods=['GET'])
def get_user_last(user_id):
    """Быстрый доступ к последним значениям конкретного пользователя"""
    return jsonify(user_last_values.get(user_id, {}))


# Остальные маршруты остаются без изменений
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/concentration')
def concentration():
    return render_template('dashboard.html')


@app.route('/calm_vs_stress')
def calm_vs_stress():
    return render_template('calm_vs_stress.html')


@app.route('/just_relax')
def just_relax():
    return render_template('just_relax.html')


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


if __name__ == '__main__':
    logger.info("Server starting on http://0.0.0.0:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # debug=False для продакшена