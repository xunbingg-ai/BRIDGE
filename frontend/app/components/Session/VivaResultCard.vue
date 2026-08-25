<template>
  <div class="viva-result-card w-full rounded-2xl border border-emerald-200 bg-emerald-50/40 p-4 shadow-sm">
    <div class="mb-2 flex items-center gap-2">
      <span class="rounded-full bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white">
        🔍 {{ title }}
      </span>
      <span class="text-xs text-slate-500">检查结果（本题已揭晓）</span>
    </div>
    <div class="markdown-body" v-html="renderedContent" />
  </div>
</template>

<script lang="ts" setup>
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ title: string; content: string }>()

const renderedContent = computed(() => {
  if (typeof window === 'undefined') return ''
  return DOMPurify.sanitize(marked.parse(props.content || '', { async: false }))
})
</script>
