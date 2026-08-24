<template>
  <div class="mx-auto max-w-7xl">
    <div v-if="sessionStore.phase === 'scoring'" class="rounded-2xl border border-slate-200 bg-white py-24 text-center shadow-sm">
      <div class="mb-4 text-4xl">⏳</div>
      <h1 class="text-xl font-semibold text-slate-900">正在打分中</h1>
      <p class="mt-2 text-sm text-slate-500">评分完成后页面会自动刷新</p>
    </div>

    <div v-else-if="sessionStore.phase === 'completed'" class="grid min-h-[calc(100vh-10rem)] gap-6 lg:grid-cols-[420px_1fr]">
      <ScoreBox :score="sessionStore.current?.score || null" :report="sessionStore.current?.report || null" />
      <AnswerBox :answer="sessionStore.current?.referenceAnswer || ''" />
    </div>

    <div v-else class="rounded-2xl border border-slate-200 bg-white py-24 text-center shadow-sm">
      <p class="text-sm text-slate-500">{{ statusMessage }}</p>
      <NuxtLink to="/" class="mt-3 inline-block text-sm font-medium text-blue-600 hover:underline">返回首页</NuxtLink>
    </div>
  </div>
</template>

<script lang="ts" setup>
import ScoreBox from '~/components/Report/ScoreBox.vue'
import AnswerBox from '~/components/Report/AnswerBox.vue'

definePageMeta({
  middleware: ['auth'],
})

const route = useRoute()
const sessionStore = useSessionStore()
const sessionId = computed(() => Number(route.params.sessionid))
let pollTimer: ReturnType<typeof setInterval> | null = null

const statusMessage = computed(() => {
  if (sessionStore.phase === 'patient') return '该会话仍处于问询阶段。'
  if (sessionStore.phase === 'examiner') return '该会话尚未提交审查。'
  return '报告不可用。'
})

async function loadReport() {
  await sessionStore.loadSession(sessionId.value)
}

onMounted(async () => {
  try {
    await loadReport()
    pollTimer = setInterval(async () => {
      if (sessionStore.phase === 'scoring') {
        await loadReport()
      } else if (sessionStore.phase === 'completed') {
        if (pollTimer) clearInterval(pollTimer)
      }
    }, 2000)
  } catch (error: any) {
    alert(error.message || '加载报告失败')
    navigateTo('/')
  }
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
