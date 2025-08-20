# Телеграм-бот подсчета калорий по фото — Этап 0

![Канонический образ персонажа](character/character_bot.png)

Визуальный образ персонажа бота фиксирован и служит единым референсом: `character/character_bot.png`. Во всех документах, макетах, промптах и медиа (аватарки, видео, иконки) используем именно этот образ.

Этот репозиторий подготовлен под MVP согласно `docs/roadmap.md` (этап 0). Ниже — пошаговая инструкция для новичка: как установить зависимости, куда положить ключи и как быстро проверить AI‑функции (картинка/голос/видео‑аватар).

## Требования
- Python 3.11+ на сервере (Debian 12 в OVHcloud)
- Аккаунт OpenAI (для LLM/Vision/Image/TTS)
- Аккаунт D‑ID (для talking‑head видео) — опционально

## Установка на VPS OVHcloud (Debian 12)
Можно не ставить ничего локально: все шаги выполняются на сервере. Ниже — максимально подробная инструкция для первого запуска.

1) Подключение к серверу
   - Откройте панель OVHcloud: Bare Metal Cloud → Virtual private servers → выберите свой VPS `vps-…`.
   - Справа в блоке `IP` найдите строку `IPv4` и нажмите иконку копирования. Скопированный адрес вида `57.129.75.190` — это то, что нам нужно (IPv6 пока не используем).
   - На macOS откройте Terminal и выполните:
     ```bash
     ssh root@57.129.75.190
     ```
     При первом подключении подтвердите fingerprint — введите `yes`.
   - Если запрашивает пароль, введите root‑пароль из письма OVHcloud «Your VPS is ready» (приходит после установки/переустановки). Нет пароля/не помните? В панели сервера нажмите `…` напротив `OS/Distribution` → Reinstall → выберите Debian 12 и метод доступа `Password` или `SSH key`. После завершения переустановки придёт новое письмо с паролем (или используйте свой SSH‑ключ).
   - Успешный вход выглядит как приглашение `root@vps…:~#`. Вы на сервере и можете переходить к следующему шагу.
   - Если вход по ключу не пускает пользователя `root`, попробуйте пользователя `debian`:
     ```bash
     ssh -o IdentitiesOnly=yes -i ~/.ssh/ovh-vps debian@57.129.75.190
     # затем перейдите в root
     sudo -i
     ```
     Либо выполняйте команды из шага 2 с префиксом `sudo`.
   - Если видите предупреждение `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` после переустановки VPS — это ожидаемо (сменился SSH host key). Удалите старую запись и подключитесь снова:
     ```bash
     ssh-keygen -R 57.129.75.190
     # (опционально) также очистите запись по имени VPS, если она есть:
     ssh-keygen -R vps-d4ae39f5.vps.ovh.net
     # повторное подключение
     ssh root@57.129.75.190
     ```

2) Обновление системы и установка инструментов
   ```bash
   apt update && apt -y upgrade
   apt -y install python3 python3-venv python3-pip git ffmpeg
   python3 --version   # должно показать 3.11.x
   ```
   Если команда `git` недоступна — убедитесь, что она установлена (`apt -y install git`).

3) Загрузка проекта на сервер
   - Вариант через git (проще всего):
     ```bash
     cd ~
     git clone https://github.com/evsevm-oss/botult.git calorie-photo-bot
     cd calorie-photo-bot
     ```
   - Вариант через SFTP: загрузите файлы в папку `~/calorie-photo-bot`, затем выполните `cd ~/calorie-photo-bot`.

4) Создание виртуального окружения Python и установка зависимостей
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # в начале строки командной строки появится (.venv)
   pip install -U pip
   pip install -r requirements.txt
   ```
   Если после этого вы откроете новый SSH‑сеанс — заново активируйте окружение командой `source .venv/bin/activate`.

5) Создание файла настроек `.env`
   ```bash
   cp env.example .env
   nano .env
   ```
   В редакторе `nano` найдите строку `OPENAI_API_KEY=` и вставьте свой ключ OpenAI.
   - Где взять ключ: откройте [OpenAI Platform → API keys](https://platform.openai.com/api-keys) и создайте ключ, затем скопируйте его в `.env`.
   - Остальные переменные можно пока не трогать. Если попросит `DATABASE_URL`, оставьте заглушку, например:
     `DATABASE_URL=postgresql://user:pass@localhost:5432/dbname`
   Подсказки по `nano`: сохранить — Ctrl+O, затем Enter; выйти — Ctrl+X.

6) Проверка работы (smoke‑тесты) прямо на сервере
   Запустим Python и выполним минимальные примеры из раздела «Быстрые проверки» ниже.
   ```bash
   python -q
   ```
   Затем вставьте и выполните код из подпунктов 1 и 2 (изображение и TTS). Результаты появятся в папке `data/demo/`.
   Проверить можно так:
   ```bash
   ls -lh data/demo/
   ```

Примечание: на этапе 0 мы не поднимаем веб‑сервер/вебхуки. Наша цель — убедиться, что ключи работают, и получить файлы в `data/demo/`.

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
Ниже — минимальные примеры, чтобы убедиться, что ключи работают и файлы создаются на диске сервера.

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
- `character/` — канонический образ персонажа бота (`character/character_bot.png`)

## Типичные проблемы и решения
- Ошибка «Unauthorized/401»: проверьте, что `OPENAI_API_KEY`/`DID_API_KEY` выставлены в `.env` и вы активировали виртуальное окружение.
- Ошибка при чтении конфигурации/`DATABASE_URL`: укажите временную заглушку `DATABASE_URL` в `.env` (см. выше). На этапе 0 к базе не обращаемся.
- Ошибка сертификатов/сети: попробуйте ещё раз, проверьте VPN/прокси.
- Слишком медленно или дорого: уменьшите размер изображений/длину текста, сократите количество вызовов.

## Следующие шаги
- Заполните `TELEGRAM_BOT_TOKEN` (в `.env`) и запустите базовый бот (поллинг):
  ```bash
  source .venv/bin/activate
  python -m bot.main
  ```
  Если всё ок, бот ответит на `/start` и `/help`.
- Для фото‑распознавания блюд/порций будем использовать GPT‑4o (vision) и унифицированный JSON‑формат (этапы 7–9).

## Деплой и обновление на VPS (важно)

Ключевые правила безопасного обновления:
- На токен Telegram должен работать только ОДИН poller (используйте systemd‑сервис, не запускайте бот локально параллельно).
- Не перезаписывайте `.env` при обновлении кода.
- После смены токена: обновите `.env` → перезапустите сервис → проверьте `getMe` и `getMyCommands`.

Краткая инструкция (zip → scp → unzip → restart):

1) На локальной машине (macOS), в корне проекта:
```bash
zip -r -X /tmp/bot.zip . -x '.venv/*' '.git/*' '__pycache__/*' 'node_modules/*'
scp -o IdentitiesOnly=yes -i ~/.ssh/ovh-vps /tmp/bot.zip debian@57.129.75.190:/home/debian/
```

2) На VPS:
```bash
sudo -i
systemctl stop ultima-bot || true
mkdir -p /root/calorie-photo-bot
unzip -oq /home/debian/bot.zip -d /root/calorie-photo-bot
/root/calorie-photo-bot/.venv/bin/python -m pip install -U pip
/root/calorie-photo-bot/.venv/bin/python -m pip install -r /root/calorie-photo-bot/requirements.txt
systemctl restart ultima-bot
sleep 2
journalctl -u ultima-bot -n 40 --no-pager
```

3) Проверки после релиза:
```bash
ls -1 /root/calorie-photo-bot/bot/routers
TOKEN=$(grep ^TELEGRAM_BOT_TOKEN= /root/calorie-photo-bot/.env | cut -d= -f2 | tr -d '"')
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
curl -s "https://api.telegram.org/bot${TOKEN}/getMyCommands"
```

4) Смена токена (если нужно):
```bash
sudo -i
cd /root/calorie-photo-bot
sed -i 's/^TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=<НОВЫЙ_ТОКЕН>/' .env
TOKEN=$(grep ^TELEGRAM_BOT_TOKEN= .env | cut -d= -f2 | tr -d '"')
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
systemctl restart ultima-bot
```

Подробнее: см. `docs/ops-deployment.mdc`.
