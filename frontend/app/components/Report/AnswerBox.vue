<template>
  <div class="h-full overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-slate-900">参考答案</h2>
      <span class="rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-600">病例标准答案</span>
    </div>

    <div class="markdown-body" v-html="renderedAnswer" />
  </div>
</template>

<script lang="ts" setup>
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ answer: string }>()

const renderedAnswer = computed(() => {
  if (typeof window === 'undefined') return ''
  const raw = marked.parse(props.answer || '暂无参考答案', { async: false })
  return DOMPurify.sanitize(raw)
})
</script>
