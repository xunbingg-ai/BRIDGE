<template>
  <div class="mx-auto flex min-h-[calc(100vh-10rem)] max-w-md items-center justify-center">
    <div class="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div class="mb-6 text-center">
        <h1 class="text-2xl font-semibold text-slate-900">登录</h1>
        <p class="mt-2 text-sm text-slate-500">登录后开始 OSCE 病例练习</p>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">用户名</span>
          <input
            v-model="form.username"
            class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            autocomplete="username"
          />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">密码</span>
          <input
            v-model="form.password"
            type="password"
            class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            autocomplete="current-password"
          />
        </label>

        <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>

        <button
          type="submit"
          class="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
          :disabled="authStore.loading"
        >
          {{ authStore.loading ? '登录中…' : '登录' }}
        </button>
      </form>

      <p class="mt-5 text-center text-sm text-slate-500">
        还没有账号？
        <NuxtLink to="/register" class="font-medium text-blue-600 hover:underline">立即注册</NuxtLink>
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
const authStore = useAuthStore()
const route = useRoute()
const errorMessage = ref('')
const form = reactive({
  username: '',
  password: '',
})

function redirectTarget() {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/'
}

async function submit() {
  errorMessage.value = ''
  try {
    await authStore.login(form.username, form.password)
    navigateTo(redirectTarget())
  } catch (error: any) {
    errorMessage.value = error.message || '登录失败'
  }
}
</script>
