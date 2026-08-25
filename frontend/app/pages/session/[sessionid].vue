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
    </div>

    <div class="flex h-[calc(100vh-13rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <ChatContainer :messages="sessionStore.messages" :loading="sessionStore.replyLoading" />

      <InputBox
        v-if="sessionStore.phase === 'patient' || sessionStore.phase === 'examiner'"
        :disabled="sessionStore.replyLoading"
        @send="handleSend"
      />
    </div>

    <div class="mt-4 flex justify-end">
      <button
        v-if="sessionStore.phase === 'patient'"
        type="button"
        class="rounded-xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:opacity-50"
        :disabled="sessionStore.replyLoading"
        @click="handleEndInquiry"
      >
        结束问询
      </button>

      <button
        v-else-if="sessionStore.phase === 'examiner'"
        type="button"
        class="rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
        :disabled="sessionStore.submitting || sessionStore.replyLoading"
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
  } catch (error: any) {
    alert(error.message || '加载会话失败')
    navigateTo('/')
  }
})
</script>
