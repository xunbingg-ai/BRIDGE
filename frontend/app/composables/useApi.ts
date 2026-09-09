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

  // 前后端同机（后端固定 5000）。
  // 浏览器端默认走向前端同源 /api，由 Nuxt 的 nitro routeRules 代理到后端(127.0.0.1:5000)，
  // 因此本地、校园 IP、以及 ngrok 公网隧穿（单公网入口）都能取到正确的 API 地址。
  // 若通过 NUXT_PUBLIC_API_BASE 显式指定了绝对后端地址，则浏览器端直接访问该地址。
  const DEFAULT_API_BASE = 'http://127.0.0.1:5000/api'
  let apiBase = config.public.apiBase || DEFAULT_API_BASE
  if (typeof window !== 'undefined' && apiBase === DEFAULT_API_BASE) {
    apiBase = `${window.location.origin}/api`
  }

  try {
    return await $fetch<T>(path, {
      baseURL: apiBase,
      ...options,
      headers,
    })
  } catch (error: any) {
    const message = error?.data?.message || error?.message || '网络请求失败'
    throw new Error(message)
  }
}
