<template>
  <div class="flex items-end gap-3 border-t border-slate-200 bg-white p-4">
    <textarea
      v-model="text"
      rows="1"
      placeholder="输入你的问诊内容，Enter 发送，Shift+Enter 换行"
      class="max-h-40 min-h-12 flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
      :disabled="disabled"
      @keydown.enter.exact.prevent="send"
      @keydown.enter.shift.exact.prevent="text += '\n'"
    />
    <button
      type="button"
      class="rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="disabled || !text.trim()"
      @click="send"
    >
      发送
    </button>
  </div>
</template>

<script lang="ts" setup>
const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ send: [content: string] }>()

const text = ref('')

function send() {
  const content = text.value.trim()
  if (!content || props.disabled) return
  emit('send', content)
  text.value = ''
}
</script>
