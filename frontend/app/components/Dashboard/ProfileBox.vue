<template>
  <div class="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-6 flex items-center gap-4">
      <div class="flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 text-xl font-bold text-blue-600">
        {{ initial }}
      </div>
      <div>
        <h2 class="text-lg font-semibold text-slate-900">
          {{ authStore.user?.realName || authStore.user?.username }}
        </h2>
        <p class="text-sm text-slate-500">@{{ authStore.user?.username }}</p>
      </div>
    </div>

    <dl class="mb-6 space-y-3 text-sm">
      <div class="flex justify-between gap-4">
        <dt class="text-slate-400">邮箱</dt>
        <dd class="text-right font-medium text-slate-700">{{ authStore.user?.email || '未填写' }}</dd>
      </div>
      <div class="flex justify-between gap-4">
        <dt class="text-slate-400">手机号</dt>
        <dd class="text-right font-medium text-slate-700">{{ authStore.user?.phone || '未填写' }}</dd>
      </div>
      <div class="flex justify-between gap-4">
        <dt class="text-slate-400">注册时间</dt>
        <dd class="text-right font-medium text-slate-700">{{ formattedDate }}</dd>
      </div>
    </dl>

    <div class="mt-auto grid gap-2">
      <button
        type="button"
        class="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        @click="infoVisible = true"
      >
        修改信息
      </button>
      <button
        type="button"
        class="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        @click="pwdVisible = true"
      >
        修改密码
      </button>
      <button
        type="button"
        class="rounded-lg bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-600 transition hover:bg-rose-100"
        @click="authStore.logout()"
      >
        退出登录
      </button>
    </div>

    <ChangeInfoBox :visible="infoVisible" @close="infoVisible = false" />
    <ChangePwdBox :visible="pwdVisible" @close="pwdVisible = false" />
  </div>
</template>

<script lang="ts" setup>
import ChangeInfoBox from '~/components/Dashboard/ChangeInfoBox.vue'
import ChangePwdBox from '~/components/Dashboard/ChangePwdBox.vue'

const authStore = useAuthStore()
const infoVisible = ref(false)
const pwdVisible = ref(false)

const initial = computed(() => {
  const name = authStore.user?.realName || authStore.user?.username || 'O'
  return name.slice(0, 1).toUpperCase()
})

const formattedDate = computed(() => {
  const value = authStore.user?.createdAt
  if (!value) return '-'
  return new Date(value).toLocaleDateString('zh-CN')
})
</script>
