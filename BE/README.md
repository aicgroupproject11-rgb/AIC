# Backend Base

## Cấu trúc

```text
BE/
├── apps/                  # Mỗi domain nghiệp vụ là một Django app độc lập
├── common/                # Permission, exception, utility và hạ tầng dùng chung
├── core/
│   ├── settings/
│   │   ├── base.py        # Cấu hình chung
│   │   ├── local.py       # Phát triển local
│   │   └── production.py  # Container/production
│   ├── asgi.py
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
├── tests/                 # Test xuyên module/hạ tầng
├── .env.example
├── Dockerfile
├── manage.py
└── requirements.txt
```

## Chạy local

Yêu cầu Python 3.12, PostgreSQL và Redis.

```bash
cd BE
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Nếu PostgreSQL/Redis chạy từ file Compose ở root, đổi `DB_PORT` thành `5433` và các Redis URL sang cổng `6380` trong `BE/.env`.

Chạy Celery ở terminal khác:

```bash
cd BE
source .venv/bin/activate
celery -A core worker --loglevel=info
```

Kiểm tra:

```bash
python manage.py check
python manage.py test
```

## Thêm module nghiệp vụ

Ví dụ tạo app `users`:

```bash
python manage.py startapp users apps/users
```
