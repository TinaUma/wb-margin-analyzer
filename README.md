# WB Margin Analyzer

> **AI-инструмент для анализа маржинальности товаров на Wildberries**

Продавцы на WB часто работают вслепую: загружают товар, платят комиссию и логистику — и не знают, зарабатывают они или теряют деньги. Этот инструмент решает проблему: загружаете два Excel-файла (закупки + продажи) и за секунды получаете полную картину — какие товары прибыльные, какие убыточные, и что с этим делать.

**🌐 Live demo:** [wb.tinacodes.space](https://wb.tinacodes.space) — `demo@demo.com` / `demo1234`

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-CC785C?logo=anthropic&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-60_tests-0A9EDC?logo=pytest&logoColor=white)

---

## Какую задачу решает

Продавец на Wildberries работает в условиях сложного ценообразования: цена продажи минус комиссия WB (15–25%) минус логистика туда и обратно минус закупочная стоимость. При высоком проценте возвратов товар может уходить в минус незаметно.

**Боль:** таблица в Excel с 200+ позициями, и непонятно — где прибыль, а где слив бюджета.

**Решение:** загрузил два файла → получил цветную таблицу с AI-диагнозом → сразу видишь, какие 50 товаров тянут вниз и что конкретно с ними делать.

---

## Скриншоты

### Загрузка файлов
![Upload](docs/screenshots/1%20upload.PNG)

### Дашборд — таблица маржинальности
![Dashboard](docs/screenshots/2%20dashboard.PNG)

### Карточка товара (все метрики)
![Product Card](docs/screenshots/3%20modalwindow%20wb%20card%20item.PNG)

### What If — симулятор цены
![What If](docs/screenshots/4%20what%20if.PNG)

### AI-интерпретация от Claude
![AI Interpretation](docs/screenshots/5%20AI-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%BF%D1%80%D0%B5%D1%82%D0%B0%D1%86%D0%B8%D1%8F.PNG)

### AI-чат с аналитиком
![AI Chat](docs/screenshots/6%20ai%20chat.PNG)

### Excel-отчёт с цветными строками
![Excel](docs/screenshots/7-1%20exel.PNG)

### История анализов
![History](docs/screenshots/8%20history.PNG)

---

## Быстрый старт

```bash
git clone https://github.com/TinaUma/wb-margin-analyzer.git
cd wb-margin-analyzer
cp .env.example .env          # добавьте SECRET_KEY и ANTHROPIC_API_KEY
docker compose up --build
```

- Приложение → **http://localhost:5173**
- API Docs → **http://localhost:8000/docs**

> `ANTHROPIC_API_KEY` необязателен — приложение запускается без него, AI-эндпоинты возвращают `503` с понятным сообщением.
> **Live demo:** AI-функции отключены (геоблокировка Anthropic API на RU-серверах). Скриншоты работающего AI — в секции выше.

---

## Как это работает

```
Пользователь загружает 2 .xlsx файла
       ↓
FastAPI валидирует структуру колонок (openpyxl)
       ↓
BackgroundTask: pandas считает маржу по каждому товару
  формула: (выручка − комиссия − логистика − закупка) / выручка × 100%
  возврат логистики = 1.5 × базовая (WB-тариф)
       ↓
Результат пишется в PostgreSQL
       ↓
Frontend опрашивает статус каждые 2 сек → рендерит таблицу
       ↓
Claude Sonnet 4.6 генерирует: Диагноз / Рекомендации / Риски
       ↓
Пользователь скачивает .xlsx с цветными строками и AI-листом
```

---

## Функциональность

| Функция | Детали |
|---|---|
| **Цветная таблица** | Зелёная ≥25% / Жёлтая 10–25% / Красная <10% |
| **Фильтр по зоне** | Кнопки с счётчиком товаров в каждой зоне |
| **Сортировка** | Клик на заголовок: маржа, прибыль, цена |
| **Карточка товара** | Модалка с полными цифрами по клику на строку |
| **What If симулятор** | Слайдеры цены/себестоимости — пересчёт в реальном времени |
| **AI-интерпретация** | Claude генерирует диагноз с таблицами и конкретными цифрами |
| **AI-чат** | Контекстные Q&A, скользящее окно из 5 сообщений |
| **Экспорт Excel** | Цветные строки + лист с AI-интерпретацией |
| **История** | Все прошлые анализы с датой и статусом |
| **Асинхронность** | Upload возвращает 202 мгновенно, анализ в фоне |

---

## Стек

### Бэкенд
- **FastAPI** (async) + **SQLAlchemy 2.0** async ORM
- **Alembic** — миграции (запускаются автоматически при старте контейнера)
- **pandas** — парсинг Excel и расчёт маржи
- **openpyxl** — валидация файлов и цветной Excel-экспорт
- **anthropic** Python SDK (`AsyncAnthropic`, `claude-sonnet-4-6`)
- **python-jose** + **bcrypt** — JWT-авторизация

### Фронтенд
- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS v3**
- **React Router v6**
- **Axios** с interceptors (Bearer токен, редирект на /login при 401)

### Инфраструктура
- **PostgreSQL 16** с named volume
- **Docker Compose** — запуск одной командой
- **Nginx** — раздаёт React SPA, проксирует `/api` → FastAPI

---

## Тесты

```bash
pytest -v   # 60 тестов
```

Покрыто: валидатор файлов, движок расчёта маржи, все API-эндпоинты (upload, analyses, AI, export), авторизация.

---

## Переменные окружения

| Переменная | Обязательна | Описание |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async URL |
| `SECRET_KEY` | ✅ | JWT секрет (`openssl rand -hex 32`) |
| `ANTHROPIC_API_KEY` | ☑ опционально | Ключ Claude API — без него AI возвращает 503 |
| `CORS_ORIGINS` | ☑ опционально | JSON-список origin'ов |

---

## Документация

- [Техническое задание (PDF)](docs/WB%20Margin%20Analyzer%20—%20ТЗ%20v2.0.pdf) — полное ТЗ проекта
- [API Docs](http://localhost:8000/docs) — интерактивная Swagger-документация

---

## Структура проекта

```
wb-margin-analyzer/
├── backend/
│   ├── api/v1/          # FastAPI роутеры (auth, uploads, analyses)
│   ├── core/            # Config (pydantic-settings)
│   ├── models/          # SQLAlchemy модели
│   ├── schemas/         # Pydantic схемы
│   └── services/        # Бизнес-логика (analysis, AI, export, validator)
├── frontend/
│   └── src/
│       ├── api/         # Axios клиент + типизированные функции
│       ├── components/  # MarginTable, WhatIfPanel, ChatBlock, FileDropzone
│       ├── context/     # AuthContext (JWT)
│       └── pages/       # Login, Register, Upload, Dashboard, History
├── tests/               # pytest — 60 тестов
├── docs/                # Скриншоты + ТЗ
├── alembic/             # Миграции БД
└── docker-compose.yml
```
