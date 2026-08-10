# Base Platform

## Công nghệ

- Backend: Python 3.12, Django 5, Django REST Framework, PostgreSQL, Redis, Celery, Gunicorn.
- Frontend: Node 24, React 19, TypeScript, Vite, Tailwind CSS, React Router, Zod.
- Runtime: Docker Compose và Nginx.

## Chạy nhanh bằng Docker

Yêu cầu Docker Engine/Desktop có Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

Sau khi các container healthy:

- Frontend: <http://localhost:3000>
- Backend health check: <http://localhost:8000/api/health/>
- Swagger UI: <http://localhost:8000/api/docs/>
- Django Admin: <http://localhost:8000/admin/>

Tạo tài khoản quản trị:

```bash
docker compose exec backend python manage.py createsuperuser
```

Dừng hệ thống:

```bash
docker compose down
```

Dữ liệu PostgreSQL, Redis, static và media nằm trong named volumes. Chỉ dùng `docker compose down -v` khi chủ động muốn xóa toàn bộ dữ liệu local.

## Chạy từng phần để phát triển

Có thể chỉ bật hạ tầng bằng Docker:

```bash
docker compose up -d db redis
```

Sau đó làm theo [README backend](./BE/README.md) và [README frontend](./FE/README.md). Cấu hình mặc định publish PostgreSQL tại `localhost:5433` và Redis tại `localhost:6380` để tránh đụng các dịch vụ local; có thể đổi bằng `POSTGRES_PORT` và `REDIS_PORT` trong `.env`. Khi BE chạy ngoài Docker với hạ tầng Compose, cập nhật `DB_PORT=5433`, `CELERY_BROKER_URL=redis://127.0.0.1:6380/0` và `CELERY_RESULT_BACKEND=redis://127.0.0.1:6380/1` trong `BE/.env`.

## Cấu trúc

```text
.
├── BE/                  # Django API và background worker
├── FE/                  # React SPA
├── docker-compose.yml   # Toàn bộ stack local/container
├── .env.example         # Biến môi trường cấp Compose
└── README.md
```

Quy ước: không commit `.env`, secret, database dump, file upload, `node_modules`, build artifact hay virtual environment.
