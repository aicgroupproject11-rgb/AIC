import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section>
      <p className="text-sm font-semibold text-blue-700">404</p>
      <h1 className="mt-2 text-3xl font-bold">Không tìm thấy trang</h1>
      <Link className="mt-6 inline-block text-blue-700 underline" to="/">
        Về trang chủ
      </Link>
    </section>
  )
}

