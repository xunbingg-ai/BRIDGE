<template>
  <div class="mx-auto max-w-4xl">
    <div class="mb-4 flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <div>
        <h1 class="font-semibold text-slate-900">
          {{ sessionStore.current?.caseTitle || 'OSCE 会话' }}
        </h1>
        <p class="mt-1 text-xs text-slate-400">
          当前阶段：{{ phaseLabel }}
        </p>
      </div>
      <div
        class="rounded-xl px-4 py-2 text-right"
        :class="timerClass"
      >
        <p class="text-xs text-slate-400">剩余时间</p>
        <p class="font-mono text-xl font-bold">{{ timerText }}</p>
      </div>
    </div>

    <div class="flex h-[calc(100vh-13rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <ChatContainer :messages="sessionStore.messages" :loading="sessionStore.replyLoading" />

      <InputBox
        v-if="sessionStore.phase === 'patient' || sessionStore.phase === 'examiner'"
        :disabled="sessionStore.replyLoading || timeUp"
        @send="handleSend"
      />
    </div>

    <div class="mt-4 flex justify-end">
      <button
        v-if="sessionStore.phase === 'patient'"
        type="button"
        class="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
        :disabled="sessionStore.replyLoading || timeUp"
        @click="handleEndInquiry"
      >
        结束问询
      </button>

      <button
        v-else-if="sessionStore.phase === 'examiner'"
        type="button"
        class="rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
        :disabled="sessionStore.submitting || sessionStore.replyLoading || timeUp"
        @click="handleSubmit"
      >
        {{ sessionStore.submitting ? '提交中…' : '提交审查' }}
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import ChatContainer from '~/components/Session/ChatContainer.vue'
import InputBox from '~/components/Session/InputBox.vue'

definePageMeta({
  middleware: ['auth'],
})

const route = useRoute()
const sessionStore = useSessionStore()
const secondsLeft = ref(0)
const timeUp = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const sessionId = computed(() => Number(route.params.sessionid))

const phaseLabel = computed(() => {
  const map = {
    patient: 'AI 病人问询阶段',
    examiner: 'AI 考官审查阶段',
    scoring: '评分中',
    completed: '已完成',
    expired: '已超时',
  }
  return map[sessionStore.phase] || sessionStore.phase
})

const timerText = computed(() => {
  const minutes = Math.floor(secondsLeft.value / 60)
  const seconds = secondsLeft.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const timerClass = computed(() => {
  if (timeUp.value) return 'bg-rose-50 text-rose-600'
  if (secondsLeft.value <= 60) return 'bg-amber-50 text-amber-600'
  return 'bg-blue-50 text-blue-600'
})

function startTimer(deadlineAt: string) {
  stopTimer()
  const deadline = new Date(deadlineAt).getTime()
  secondsLeft.value = Math.max(0, Math.floor((deadline - Date.now()) / 1000))

  timer = setInterval(() => {
    secondsLeft.value = Math.max(0, Math.floor((deadline - Date.now()) / 1000))
    if (secondsLeft.value <= 0) {
      timeUp.value = true
      stopTimer()
    }
  }, 1000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

async function handleSend(content: string) {
  try {
    await sessionStore.sendMessage(content)
  } catch (error: any) {
    alert(error.message || '发送失败')
  }
}

async function handleEndInquiry() {
  try {
    await sessionStore.endInquiry()
  } catch (error: any) {
    alert(error.message || '结束问询失败')
  }
}

async function handleSubmit() {
  try {
    await sessionStore.submit()
    navigateTo(`/report/${sessionId.value}`)
  } catch (error: any) {
    alert(error.message || '提交失败')
  }
}

onMounted(async () => {
  try {
    if (!sessionStore.current || sessionStore.current.sessionId !== sessionId.value) {
      await sessionStore.loadSession(sessionId.value)
    }
    if (sessionStore.current?.deadlineAt) {
      startTimer(sessionStore.current.deadlineAt)
    }
  } catch (error: any) {
    alert(error.message || '加载会话失败')
    navigateTo('/')
  }
})

watch(timeUp, (value) => {
  if (!value) return
  if (sessionStore.phase === 'examiner') {
    handleSubmit()
  } else if (sessionStore.phase === 'patient') {
    alert('时间已到，本次问询未完成。')
    navigateTo(`/report/${sessionId.value}`)
  }
})

onBeforeUnmount(stopTimer)
</script>
