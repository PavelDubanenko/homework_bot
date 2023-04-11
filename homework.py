import logging
import os
import time
import sys
import requests
from http import HTTPStatus
import telegram
from exceptions import RequestError, HTTPRequestError

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler(sys.stdout)
)


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка переменных."""
    list_verible = [
        PRACTICUM_TOKEN,
        TELEGRAM_CHAT_ID,
        TELEGRAM_TOKEN
    ]
    try:
        return all(list_verible)
    except Exception as error:
        logging.error(f'Отсутсвует глобальная переменная: {error}')


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение в Telegram отправлено: {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except requests.RequestException:
        logging.error('Ошибка RequestError')
    if response.status_code != HTTPStatus.OK:
        raise HTTPRequestError(response)
    if response is None:
        raise RequestError(response)
    return response.json()


def check_response(response):
    """Проверка API на соответствие."""
    if not response:
        raise KeyError('Отсутсвует запрос')

    if not isinstance(response, dict):
        logging.error('Тип данных ответа не словарь')
        raise TypeError('Тип данных ответа не словарь')

    if 'homeworks' not in response:
        logging.error('Отсутсвует ключ "homeworks"')
        raise KeyError('Отсутсвует ключ "homeworks"')

    if not isinstance(response.get('homeworks'), list):
        logger.error('Тип данных ответа не список')
        raise TypeError('Тип данных ответа не список')
    return response['homeworks']


def parse_status(homework):
    """Извлечение статуса домашки."""
    if homework.get('status') not in HOMEWORK_VERDICTS:
        logging.error('Недокументированный статус домашней работы')
        raise KeyError('Недокументированный статус домашней работы')
    verdict = HOMEWORK_VERDICTS[homework.get('status')]
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError('Нет имени домашней работы')
    if 'status' not in homework:
        raise KeyError('Нет статуса проверки')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }

    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.'
            'Программа принудительно остановлена.'
        )
        exit(
            'Отсутствует обязательная переменная окружения.'
            'Программа принудительно остановлена.'
        )

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks is None:
                logging.debug('Ответ пуст, нет домашних работ.')
            for homework in homeworks:
                message = parse_status(homework)
                if last_send.get(homework['homework_name']) != message:
                    send_message(bot, message)
                    last_send[homework['homework_name']] = message

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
