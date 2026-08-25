<template>
  <div
    class="flex w-full flex-col gap-1.5"
    :class="message.role === 'user' ? 'items-end' : 'items-start'"
  >
    <div
      v-if="message.role === 'system'"
      class="w-full rounded-lg bg-slate-100 px-4 py-3 text-center text-xs font-medium text-slate-500"
    >
      {{ message.content }}
    </div>

    <div
      v-else
      class="w-fit max-w-[85%] rounded-2xl px-4 py-3"
      :class="
        message.role === 'user'
          ? 'bg-blue-600 text-white'
          : 'border border-slate-200 bg-white text-slate-800'
      "
    >
      <div
        v-if="message.role === 'user'"
        class="whitespace-pre-wrap text-sm leading-6"
      >
        {{ message.content }}
      </div>
      <div
        v-else
        class="markdown-body chat-bubble-md"
        v-html="renderedMarkdown"
      />
    </div>

    <!-- viva 分节 tag 触发：解密「体格检查 / 辅助检查」结果卡片（仅考官消息携带该标记） -->
    <template v-if="message.role === 'assistant' && parts.length">
      <VivaResultCard
        v-if="parts.includes('pe') && peFindings"
        title="体格检查结果"
        :content="peFindings"
      />
      <VivaResultCard
        v-if="parts.includes('investigations') && investigations"
        title="辅助检查结果"
        :content="investigations"
      />
    </template>
  </div>
</template>

<script lang="ts" setup>
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import VivaResultCard from '~/components/Session/VivaResultCard.vue'
import { extractVivaParts, stripVivaTags } from '~/utils/viva'
import type { ChatMessage } from '~/types'

const props = defineProps<{
  message: ChatMessage
  peFindings?: string
  investigations?: string
}>()

const parts = computed(() => extractVivaParts(props.message.content || ''))

const renderedMarkdown = computed(() => {
  if (typeof window === 'undefined') return ''
  const cleaned = stripVivaTags(props.message.content || '')
  const raw = marked.parse(cleaned, { async: false })
  return DOMPurify.sanitize(raw)
})
</script>
