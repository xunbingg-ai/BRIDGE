<template>
  <div
    class="flex w-fit max-w-[85%] flex-col gap-1"
    :class="message.role === 'user' ? 'ml-auto items-end' : 'items-start'"
  >
    <div
      v-if="message.role === 'system'"
      class="w-full rounded-lg bg-slate-100 px-4 py-3 text-center text-xs font-medium text-slate-500"
    >
      {{ message.content }}
    </div>

    <div
      v-else
      class="rounded-2xl px-4 py-3"
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
        class="markdown-body"
        v-html="renderedMarkdown"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChatMessage } from '~/types'

const props = defineProps<{ message: ChatMessage }>()

const renderedMarkdown = computed(() => {
  if (typeof window === 'undefined') return ''
  const raw = marked.parse(props.message.content || '', { async: false })
  return DOMPurify.sanitize(raw)
})
</script>
