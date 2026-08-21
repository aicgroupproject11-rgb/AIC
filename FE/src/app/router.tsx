import { createBrowserRouter } from 'react-router-dom'


import { AppLayout } from '../layouts/AppLayout.tsx'
import { HomePage } from '../pages/HomePage.tsx'
import { KISSearchPage } from '../pages/KISSearchPage.tsx'
import { NotFoundPage } from '../pages/NotFoundPage.tsx'


export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'kis/search',
        element: <KISSearchPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])