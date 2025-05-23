# Конструктор профиля работников по востребованным профессиям

## Описание проекта

Веб-приложение предназначено для формирования, оценки и визуализации компетенций сотрудников в зависимости от их должности, компании и требований рынка труда. Система позволяет создавать чек-листы, матрицы компетенций, а также назначать роли различным пользователям (администратор, методист, эксперт и др.).

## Основной функционал

* Авторизация с разграничением прав по ролям
* Управление предприятиями и должностями
* Конструктор чек-листов и матриц компетенций
* Оценка сотрудников по различным параметрам (процессы, критерии, инциденты)
* Сохранение, печать и экспорт результатов
* Поддержка состояний чек-листа

## Используемые технологии

### Backend:

* Python 3.11+
* Django 4.x
* PostgreSQL

### Frontend:

* HTML5, CSS3
* JavaScript

### DevOps:

* Docker, Docker Compose
* GitHub Actions (CI/CD)

## Установка и запуск

### Требования:

* Python 3.11+
* PostgreSQL
* Docker и Docker Compose (опционально)

### Установка вручную

```bash
git clone https://github.com/yourusername/yourproject.git
cd myproject
python -m venv venv
source venv/bin/activate       # для Linux/macOS
venv\Scripts\activate          # для Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Запуск в Docker

```bash
docker compose build
docker compose up -d
//Загрузка миграций в бд
docker-compose exec web python manage.py migrate
//Создание суперюзера username=admin, email лучше оставить пустым, password=12345
docker-compose exec web python manage.py createsuperuser
//Переходим http://localhost:8000/admin -> Выбираем Users и там нажимаем на пользователя
admin и меняем у него роль на администратора.
Теперь можно переходить на страницу авторизации http://localhost:8000/login
```

## Роли пользователей

* **Администратор** – управление пользователями, ролями, предприятиями
* **Технический руководитель** – создание подчинённых ролей
* **Методист** – управление чек-листами и компетенциями
* **Эксперт** – оценка сотрудников

## Демонстрация
![Работа приложения](demo.gif)
