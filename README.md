# Телеграм-бот подсчета калорий по фото — Этап 0

Этот репозиторий подготовлен под MVP согласно `docs/roadmap.md` (этап 0). Ниже — пошаговая инструкция для новичка: как установить зависимости, куда положить ключи и как быстро проверить AI‑функции (картинка/голос/видео‑аватар).

## Требования
- Python 3.11+ на сервере (Debian 12 в OVHcloud) или локально
- Аккаунт OpenAI (для LLM/Vision/Image/TTS)
- Аккаунт D‑ID (для talking‑head видео) — опционально

## Вариант A — локально (быстрая установка)
1) Клонируйте проект и зайдите в каталог.
2) Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```
3) Создайте файл `.env` на основе примера:
```bash
cp env.example .env
```
4) Заполните необходимые поля в `.env` (см. ниже).

## Вариант B — на VPS OVHcloud (Debian 12, без локальной установки)
Можно не ставить Python у себя: подключитесь по SSH к VPS и всё делайте прямо на сервере.

1) Подключение к серверу
   - В панели OVHcloud получите IP и доступ по SSH (пароль или ключ).
   - Подключитесь: `ssh root@<SERVER_IP>` (или используйте вашего пользователя).

2) Подготовка окружения (Debian 12)
   ```bash
   sudo apt update && sudo apt -y upgrade
   sudo apt -y install python3 python3-venv python3-pip git
   # опционально (понадобится на следующих этапах):
   sudo apt -y install ffmpeg
   python3 --version   # убедитесь, что это 3.11+
   ```

3) Загрузка проекта
   - Через git:
     ```bash
     cd ~
     git clone <URL_ВАШЕГО_РЕПО> calorie-photo-bot
     cd calorie-photo-bot
     ```
   - Или загрузите файлы через SFTP/файловый менеджер в каталог, например, `~/calorie-photo-bot`, затем `cd ~/calorie-photo-bot`.

4) Виртуальное окружение и зависимости
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -r requirements.txt
   ```

5) Настройка переменных окружения
   ```bash
   cp env.example .env
   ```
   Откройте `.env` в редакторе (nano/vim) и укажите ключи (см. ниже). Если БД не используете — задайте временную заглушку:
   `DATABASE_URL=postgresql://user:pass@localhost:5432/dbname`

6) Быстрые проверки на сервере
   - Запустите `python -q` и выполните сниппеты из раздела «Быстрые проверки» ниже. Файлы появятся в `data/demo/...` на сервере (скачайте SFTP при необходимости).

Примечание: на этапе 0 веб‑сервер/бот по вебхуку не поднимаются. Мы лишь проверяем AI‑вызовы через Python.

## Что обязательно заполнить в .env сейчас
- `OPENAI_API_KEY` — ключ OpenAI.
  - Где взять: войдите в [OpenAI Platform → API keys](https://platform.openai.com/api-keys) и создайте новый ключ.
- `OPENAI_TTS_VOICE` — голос для TTS (по умолчанию `alloy`, можно оставить).
- (опционально) `DID_API_KEY` — если хотите сгенерировать видео с «говорящей» головой.
  - Где взять: в личном кабинете [D‑ID → API](https://www.d-id.com/) создайте ключ.

Прочие переменные (`TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `REDIS_URL`, и т.д.) понадобятся позже — для этапов бота, БД и очередей. Для быстрой проверки AI можно не трогать.

Дополнительно сейчас (как заглушку, чтобы конфиг успешно читался):
- `DATABASE_URL=postgresql://user:pass@localhost:5432/dbname`

Важно: файл `.env` не коммитится (проверьте, что он в `.gitignore`). Никогда не публикуйте реальные ключи в репозиториях/скриншотах.

## Быстрые проверки (smoke‑тесты)
Ниже — минимальные примеры, чтобы убедиться, что ключи работают.

### 1) Генерация изображения (аватар) через OpenAI Images
```python
# запустите: python -q  (или python) и вставьте сниппет построчно
from services.image.openai_images import generate_and_save

path = generate_and_save(
    prompt="professional friendly nutrition coach portrait, clean background",
    target_path="data/demo/avatar.png",
)
print(f"saved: {path}")
```
Ожидаемый результат: файл `data/demo/avatar.png` появится на диске.

### 2) Озвучка текста (TTS) через OpenAI
```python
from services.voice.openai_tts import synthesize_to_file

audio_path = synthesize_to_file(
    text="Привет! Я твой AI-коуч по питанию, готов помочь с бюджетом калорий и БЖУ.",
    target_path="data/demo/voice.mp3",
)
print(f"saved: {audio_path}")
```
Ожидаемый результат: файл `data/demo/voice.mp3` появится на диске.

### 3) Talking‑Head видео (D‑ID) — опционально
D‑ID на вход принимает URL фотографии и либо `text`, либо `audio_url`.

Пример запроса и скачивания результата:
```python
from services.video.did_client import DIDClient

client = DIDClient()
# Подставьте публичные URLs на картинку и (опционально) аудио.
image_url = "https://example.com/avatar.png"

talk = client.create_talk(image_url=image_url, text="Hello from your AI coach!")
talk_id = talk.get("id")
print("created talk:", talk_id)

# Через несколько секунд опросите статус (повторите при необходимости)
status = client.get_talk(talk_id)
print("status:", status.get("status"))

# Если статус готов — скачайте итоговое видео
result_url = status.get("result_url") or status.get("result", {}).get("url")
if result_url:
    out = client.download_result(result_url, "data/demo/talking_head.mp4")
    print("saved:", out)
```
Примечания:
- Если нет публичных URL — можно загрузить файлы заранее в свое хранилище (S3/MinIO) и использовать их ссылки.
- Стоимость начисляется провайдерами за каждый вызов. Следите за тарифами в кабинетах.

## Структура проекта
- `bot/` — каркас Telegram‑бота (aiogram)
- `core/` — конфигурация (`core/config.py`)
- `infra/` — адаптеры БД/кэша/хранилища/очереди
- `services/` — интеграции AI/vision и доменные сервисы
- `domain/` — сущности и use‑cases
- `docs/` — документация (аудитория, риски, стек, глоссарий, провайдеры)
- `migrations/` — миграции (будут настроены на этапе 2)
- `data/` — рабочие файлы/артефакты (создаётся при тестах выше)

## Типичные проблемы и решения
- Ошибка «Unauthorized/401»: проверьте, что `OPENAI_API_KEY`/`DID_API_KEY` выставлены в `.env` и вы активировали виртуальное окружение.
- Ошибка при чтении конфигурации/`DATABASE_URL`: укажите временную заглушку `DATABASE_URL` в `.env` (см. выше). На этапе 0 к базе не обращаемся.
- Ошибка сертификатов/сети: попробуйте ещё раз, проверьте VPN/прокси.
- Слишком медленно или дорого: уменьшите размер изображений/длину текста, сократите количество вызовов.

## Следующие шаги
- Заполните `TELEGRAM_BOT_TOKEN` (в `.env`) и приступим к каркасу бота (этап 4 в `docs/roadmap.md`).
- Для фото‑распознавания блюд/порций будем использовать GPT‑4o (vision) и унифицированный JSON‑формат (этапы 7–9).
