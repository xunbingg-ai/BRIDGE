<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
    @click.self="$emit('close')"
  >
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <div class="mb-5 flex items-center justify-between">
        <h3 class="text-lg font-semibold">修改信息</h3>
        <button type="button" class="rounded-lg p-1 text-slate-400 hover:bg-slate-100" @click="$emit('close')">
          ✕
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">真实姓名</span>
          <input v-model="form.realName" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">邮箱</span>
          <input v-model="form.email" type="email" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">手机号</span>
          <input v-model="form.phone" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>

        <button
          type="submit"
          class="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
          :disabled="loading"
        >
          {{ loading ? '保存中…' : '保存' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { User } from '~/types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const authStore = useAuthStore()
const loading = ref(false)
const errorMessage = ref('')
const form = reactive({
  realName: '',
  email: '',
  phone: '',
})

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return
    const user = authStore.user as User | null
    form.realName = user?.realName || ''
    form.email = user?.email || ''
    form.phone = user?.phone || ''
    errorMessage.value = ''
  },
)

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    await authStore.updateProfile({
      realName: form.realName,
      email: form.email,
      phone: form.phone,
    })
    emit('close')
  } catch (error: any) {
    errorMessage.value = error.message || '保存失败'
  } finally {
    loading.value = false
  }
}
</script>
