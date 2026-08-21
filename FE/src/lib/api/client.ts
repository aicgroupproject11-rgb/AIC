import { env } from '../../config/env.ts'

export class ApiError extends Error {
  readonly status: number

  constructor(
    status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type ErrorPayload = {
  detail?: string
  error?: {
    message?: string
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    try {
      const payload = (await response.json()) as ErrorPayload
      return (
        payload.error?.message ??
        payload.detail ??
        `API request failed with status ${response.status}`
      )
    } catch {
      return `API request failed with status ${response.status}`
    }
  }

  const text = await response.text()
  return text || `API request failed with status ${response.status}`
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData

  const response = await fetch(`${env.apiBaseUrl}/${path.replace(/^\//, '')}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body && !isFormData ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response))
  }

  return response.json() as Promise<T>
}
