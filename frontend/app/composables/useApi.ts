export async function apiFetch<T>(
  path: string,
  options: Record<string, any> = {},
): Promise<T> {
  const config = useRuntimeConfig()
  const token = typeof window !== 'undefined' ? localStorage.getItem('oscae_token') : ''
  const headers: Record<string, string> = { ...(options.headers || {}) }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  try {
    return await $fetch<T>(path, {
      baseURL: config.public.apiBase,
      ...options,
      headers,
    })
  } catch (error: any) {
    const message = error?.data?.message || error?.message || '网络请求失败'
    throw new Error(message)
  }
}
