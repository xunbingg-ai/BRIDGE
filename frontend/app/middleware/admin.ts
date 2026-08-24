export default defineNuxtRouteMiddleware(() => {
  const authStore = useAuthStore()
  if (authStore.user?.role !== 'admin') {
    return navigateTo('/')
  }
})
