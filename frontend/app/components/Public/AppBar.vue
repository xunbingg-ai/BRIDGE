<template>
  <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
    <div class="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
      <NuxtLink to="/" class="flex items-center gap-2 font-semibold text-slate-900">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
          O
        </span>
        <span>OSCE 训练平台</span>
      </NuxtLink>

      <div v-if="authStore.isAuthenticated" class="flex items-center gap-3">
        <span class="hidden text-sm text-slate-500 sm:block">
          {{ authStore.user?.realName || authStore.user?.username }}
        </span>
        <NuxtLink
          v-if="authStore.user?.role === 'admin'"
          to="/admin"
          class="rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-50"
        >
          管理后台
        </NuxtLink>
        <NuxtLink
          to="/dashboard"
          class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          个人中心
        </NuxtLink>
      </div>

      <div v-else class="flex items-center gap-2">
        <NuxtLink
          to="/login"
          class="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
        >
          登录
        </NuxtLink>
        <NuxtLink
          to="/register"
          class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
        >
          注册
        </NuxtLink>
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
const authStore = useAuthStore()
</script>
