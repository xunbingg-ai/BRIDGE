<template>
  <div ref="scrollRef" class="flex-1 space-y-4 overflow-y-auto rounded-2xl bg-slate-50 p-4">
    <div v-if="messages.length === 0" class="flex h-full items-center justify-center">
      <div class="text-center text-sm text-slate-400">
        <p class="mb-2 text-3xl">🩺</p>
        <p>开始你的 OSCE 问诊练习</p>
      </div>
    </div>

    <ChatBox
      v-for="message in messages"
      :key="`${message.id || message.created_at}-${message.content}`"
      :message="message"
    />

    <div v-if="loading" class="flex justify-start">
      <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
        正在输入…
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import ChatBox from '~/components/Session/ChatBox.vue'
import type { ChatMessage } from '~/types'

const props = defineProps<{
  messages: ChatMessage[]
  loading?: boolean
}>()

const scrollRef = ref<HTMLElement | null>(null)

watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  },
  { deep: false },
)
</script>
