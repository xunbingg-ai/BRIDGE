<template>
  <div class="flex min-h-[calc(100vh-10rem)] items-center justify-center">
    <div class="text-center">
      <p class="mb-3 text-sm font-medium text-blue-600">{{ errorMessage || '正在创建会话…' }}</p>
      <NuxtLink to="/" class="text-sm text-slate-400 hover:text-blue-600">返回首页</NuxtLink>
    </div>
  </div>
</template>

<script lang="ts" setup>
const route = useRoute()
const sessionStore = useSessionStore()
const errorMessage = ref('')

definePageMeta({
  middleware: ['auth'],
})

onMounted(async () => {
  const caseId = Number(route.query.caseid)
  if (!caseId) {
    errorMessage.value = '缺少病例参数'
    return
  }

  try {
    const sessionId = await sessionStore.startSession(caseId)
    navigateTo(`/session/${sessionId}`, { replace: true })
  } catch (error: any) {
    errorMessage.value = error.message || '创建会话失败'
  }
})
</script>
