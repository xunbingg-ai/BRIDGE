export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt'],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:5000/api',
    },
  },
  // 浏览器端向同源 /api 发请求，由 Nuxt 服务端代理到后端(127.0.0.1:5000)。
  // 这样本地、校园 IP、ngrok 公网隧穿只需一个公网入口，无需暴露后端端口。
  routeRules: {
    '/api/**': { proxy: 'http://127.0.0.1:5000/api/**' },
  },
})
