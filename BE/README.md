# AIC Backend

Backend Django phục vụ keyframe/video và gọi hybrid search engine. Xem pipeline dữ liệu và index tại [tài liệu hệ thống](../docs/SEARCH_PIPELINE.md).

## Cấu trúc

```text
BE/
├── apps/                  # Mỗi domain nghiệp vụ là một Django app độc lập
├── common/                # Permission, exception, utility và hạ tầng dùng chung
├── data_processing/
│   ├── cli.py
│   ├── download_dataset.py
│   ├── pipeline.py
│   ├── manifest.csv
│   ├── collection.json
│   └── README.md
├── search_engine/        # Domain router, object BoW, PCA/R-tree, exact rerank
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

Chuẩn bị search index:

```bash
python -m data_processing.cli prepare --data-root data_processing
python manage.py build_kis_index
python -m search_engine.cli search "người đi xe đạp #L21" --top-k 10
```

Sau khi server chạy, dùng `POST /api/kis/search/inspect/` với cùng payload của search để xem query normalization, domain routing và các R-tree được truy vấn. Chi tiết contract nằm trong Swagger và [tài liệu pipeline](../docs/SEARCH_PIPELINE.md).

## Thêm module nghiệp vụ

Ví dụ tạo app `users`:

```bash
python manage.py startapp users apps/users
```
