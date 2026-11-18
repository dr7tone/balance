# BALANCE — веб-сервис учёта личных доходов и расходов

Реализация по техническому заданию (ГОСТ 19.201-78 ЕСПД) на веб-сервис учёта личных
доходов и расходов «Баланс» (BALANCE).

## Возможности

- Регистрация и авторизация (JWT), раздельный доступ к данным пользователей, роль администратора;
- Операции: доходы/расходы (сумма, дата, категория, комментарий), редактирование, удаление, поиск и фильтрация;
- Категории: стандартный набор при регистрации + пользовательские;
- Бюджет на месяц: лимиты по категориям, контроль исполнения (остаток, процент);
- **Накопление на мечту:** цели с суммой накопления, пополнение вкладов,
  прогресс-бар, автоматический учёт откладываемой суммы как расхода «Накопления»;
- **Анализ доходов и расходов:** сводка за период (доходы, расходы, баланс),
  динамика по месяцам, структура расходов/доходов по категориям с процентами;
- Экспорт и импорт операций в CSV (UTF-8, разделитель `;`);
- Веб-интерфейс (React) и REST API (FastAPI).

## Стек (по ТЗ)

Backend: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL (для локального запуска — SQLite), Redis (опционально), PyJWT, bcrypt, pytest.
Frontend: React + Vite + SASS.
Инфраструктура: Docker / Docker Compose, Git.

## Быстрый старт (без Docker, SQLite)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite:///./balance.db"
uvicorn app.main:app --reload --port 8000
```

Документация API: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Открыть http://localhost:5173 (в dev-режиме запросы `/api` проксируются на порт 8000;
адрес бэкенда можно переопределить переменной `VITE_PROXY_TARGET=http://localhost:XXXX npm run dev`).

### Тесты backend

```bash
cd backend
export DATABASE_URL="sqlite:///./test_balance.db"
pytest -q
```

## Запуск через Docker (PostgreSQL + Redis + Backend + Frontend)

```bash
cp .env.example .env   # при необходимости
docker compose up --build -d
```

- Веб-интерфейс: **https://localhost** (http://localhost автоматически редиректит на HTTPS)
- API: https://localhost/api, документация https://localhost/api/docs

## HTTPS (локальные сертификаты)

Nginx автоматически включает HTTPS на порту 443. При первом старте контейнера
`frontend` генерируется самоподписанный сертификат (CN=localhost, SAN: localhost/127.0.0.1)
и сохраняется в volume `certs` (`/etc/nginx/ssl`).

**Вариант 1 — самоподписанный (работает сразу):**
браузер покажет предупреждение «Подключение не защищено» → «Дополнительно →
Перейти на сайт». Для локальной лабораторной работы этого достаточно.

**Вариант 2 — доверенный сертификат (mkcert, без предупреждений):**

```bash
# 1. Установить и инициализировать локальный CA (один раз)
sudo apt install libnss3-tools   # для Firefox (Chrome/Edge достаточно mkcert)
mkcert -install

# 2. Создать сертификаты для localhost
mkcert -cert-file ./certs/balance.crt -key-file ./certs/balance.key \
       localhost 127.0.0.1

# 3. Скопировать их в volume контейнера и перезапустить
docker-compose up -d --build
docker cp ./certs/balance.crt frontend:/etc/nginx/ssl/balance.crt
docker cp ./certs/balance.key frontend:/etc/nginx/ssl/balance.key
docker-compose restart frontend
```

Команды запуска: используйте `docker-compose` (через дефис) — плагин `docker compose`
в системе не установлен. Для доступа к Docker-демону может потребоваться `sudo`
(или добавьте пользователя в группу docker: `sudo usermod -aG docker $USER`).

```bash
sudo docker-compose up --build -d        # сборка и запуск
sudo docker-compose ps                   # статус контейнеров
sudo docker-compose logs -f frontend     # логи (генерация сертификата, nginx)
sudo docker-compose down                 # остановка стека
```

## Структура API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/token` | Вход (OAuth2 form) |
| GET  | `/api/auth/me` | Текущий пользователь |
| CRUD | `/api/categories` | Категории |
| CRUD | `/api/operations` | Операции (+`/export`, `/import`) |
| CRUD | `/api/budgets` | Бюджеты; `GET /api/budgets/status?month=` |
| CRUD | `/api/goals` | Цели; `POST /api/goals/{id}/contribute` |
| GET  | `/api/analytics/summary?date_from&date_to` | Сводка |
| GET  | `/api/analytics/monthly?months=6` | Динамика по месяцам |
| GET  | `/api/analytics/categories?type=&date_from&date_to` | Структура по категориям |
| GET/PATCH | `/api/admin/users` | Управление пользователями (админ) |

## Формат CSV

Экспорт/импорт: шапка `Дата;Тип;Сумма;Категория;Комментарий` (UTF-8).
`Тип` — `доход`/`расход` (или `income`/`expense`), `Дата` — `ГГГГ-ММ-ДД` или `ДД.ММ.ГГГГ`.
