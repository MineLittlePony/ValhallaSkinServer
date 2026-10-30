import type { FetchOptions, FetchRequest, MappedResponseType, ResponseType } from 'ofetch'
import { $fetch } from 'ofetch'
import { useEffect, useState } from 'preact/hooks'

export type ApiResponse<T>
  = | { state: 'pending' }
    | { state: 'error', error: unknown }
    | { state: 'success', data: T }

export function useApiRequest<T = any, R extends ResponseType = 'json'>(
  path: FetchRequest,
  options?: Omit<FetchOptions<R, T>, 'signal'>,
): ApiResponse<MappedResponseType<R, T>> {
  const [apiData, setApiData] = useState<ApiResponse<MappedResponseType<R, T>>>({ state: 'pending' })

  useEffect(() => {
    const abrt = new AbortController()
    const asyncFunc = async (): Promise<MappedResponseType<R, T>> => {
      return await $fetch<T, R>(path, {
        ...options,
        signal: abrt.signal,
      })
    }

    asyncFunc()
      .then(data => setApiData({ state: 'success', data }))
      .catch(error => setApiData({ state: 'error', error }))

    return () => abrt.abort()
  }, [path, options])

  return apiData
}
