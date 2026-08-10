# Frontend Base

## Cấu trúc

```text
FE/
├── src/
│   ├── app/          # Bootstrap, provider và route registry
│   ├── components/   # UI dùng lại, không phụ thuộc domain
│   ├── config/       # Parse và validate biến môi trường
│   ├── features/     # Module nghiệp vụ theo vertical slice
│   ├── hooks/        # React hooks dùng chung
│   ├── layouts/      # Khung trang
│   ├── lib/          # API client và adapter hạ tầng
│   ├── pages/        # Trang cấp route
│   ├── styles/       # Global CSS và design tokens
│   └── types/        # Kiểu dữ liệu dùng chung
├── .env.example
├── Dockerfile
├── nginx.conf
└── package.json
```

Một feature mới nên tự chứa `components`, `hooks`, `schemas`, `services` và `types` của nó trong `src/features/<feature-name>/`. Chỉ chuyển code sang thư mục dùng chung khi thực sự có ít nhất hai feature sử dụng.

## Chạy local

Yêu cầu Node `24.11.1` và npm `11.6.x`.

```bash
cd FE
nvm use
npm ci
cp .env.example .env
npm run dev
```

Mở <http://localhost:5173>. Mặc định frontend gọi API tại `http://localhost:8000/api`; thay `VITE_API_BASE_URL` nếu backend dùng địa chỉ khác.

## Kiểm tra và build

```bash
npm run lint
npm run build
npm run preview
```
