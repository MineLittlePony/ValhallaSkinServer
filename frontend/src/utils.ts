import { useEffect, useState } from 'preact/hooks'

type ApiResponse<T>
  = | { state: 'pending' }
    | { state: 'error', error: unknown }
    | { state: 'success', data: T }

export function useApiRequest<T>(path: string): ApiResponse<T> {
  const [apiData, setApiData] = useState<ApiResponse<T>>({ state: 'pending' })

  useEffect(() => {
    const abrt = new AbortController()
    fetch(path, { signal: abrt.signal })
      .then((resp) => {
        if (!resp.ok) {
          resp.json().then(error => setApiData({ state: 'error', error }))
        }
        else {
          resp.json().then(data => setApiData({ state: 'success', data }))
        }
      })
    return () => abrt.abort()
  }, [path])
  return apiData
}
