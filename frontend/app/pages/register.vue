<template>
  <div class="mx-auto flex min-h-[calc(100vh-10rem)] max-w-md items-center justify-center">
    <div class="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div class="mb-6 text-center">
        <h1 class="text-2xl font-semibold text-slate-900">注册</h1>
        <p class="mt-2 text-sm text-slate-500">创建学生账号，开始 OSCE 练习</p>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">用户名</span>
          <input v-model="form.username" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">密码</span>
          <input v-model="form.password" type="password" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">确认密码</span>
          <input v-model="confirmPassword" type="password" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">真实姓名</span>
          <input v-model="form.realName" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">邮箱</span>
          <input v-model="form.email" type="email" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">手机号</span>
          <input v-model="form.phone" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>

        <button
          type="submit"
          class="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
          :disabled="authStore.loading"
        >
          {{ authStore.loading ? '注册中…' : '注册' }}
        </button>
      </form>

      <p class="mt-5 text-center text-sm text-slate-500">
        已有账号？
        <NuxtLink to="/login" class="font-medium text-blue-600 hover:underline">返回登录</NuxtLink>
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
const authStore = useAuthStore()
const errorMessage = ref('')
const confirmPassword = ref('')
const form = reactive({
  username: '',
  password: '',
  realName: '',
  email: '',
  phone: '',
})

async function submit() {
  errorMessage.value = ''
  if (form.password !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  try {
    await authStore.register(form)
    navigateTo('/')
  } catch (error: any) {
    errorMessage.value = error.message || '注册失败'
  }
}
</script>
