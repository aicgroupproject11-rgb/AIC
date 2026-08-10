import { RouterProvider } from 'react-router-dom'

import { router } from './router.tsx'

export function App() {
  return <RouterProvider router={router} />
}

