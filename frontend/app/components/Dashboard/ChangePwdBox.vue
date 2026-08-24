<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
    @click.self="$emit('close')"
  >
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <div class="mb-5 flex items-center justify-between">
        <h3 class="text-lg font-semibold">修改密码</h3>
        <button type="button" class="rounded-lg p-1 text-slate-400 hover:bg-slate-100" @click="$emit('close')">
          ✕
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">当前密码</span>
          <input v-model="form.oldPassword" type="password" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">新密码</span>
          <input v-model="form.newPassword" type="password" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">确认新密码</span>
          <input v-model="confirmPassword" type="password" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>

        <button
          type="submit"
          class="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
          :disabled="loading"
        >
          {{ loading ? '提交中…' : '修改密码' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script lang="ts" setup>
const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ close: [] }>()

const authStore = useAuthStore()
const loading = ref(false)
const errorMessage = ref('')
const confirmPassword = ref('')
const form = reactive({
  oldPassword: '',
  newPassword: '',
})

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      form.oldPassword = ''
      form.newPassword = ''
      confirmPassword.value = ''
      errorMessage.value = ''
    }
  },
)

async function submit() {
  if (form.newPassword !== confirmPassword.value) {
    errorMessage.value = '两次输入的新密码不一致'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    await authStore.changePassword(form.oldPassword, form.newPassword)
    emit('close')
    alert('密码修改成功')
  } catch (error: any) {
    errorMessage.value = error.message || '修改失败'
  } finally {
    loading.value = false
  }
}
</script>
