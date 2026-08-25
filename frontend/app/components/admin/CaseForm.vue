<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
    @click.self="$emit('close')"
  >
    <div class="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
      <div class="mb-5 flex items-center justify-between">
        <h3 class="text-lg font-semibold">{{ caseData?.caseId ? '修改病例' : '新增病例' }}</h3>
        <button type="button" class="rounded-lg p-1 text-slate-400 hover:bg-slate-100" @click="$emit('close')">
          ✕
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div class="grid gap-4 md:grid-cols-2">
          <label class="block text-sm">
            <span class="mb-1 block text-slate-600">病例编号</span>
            <input v-model="form.caseNo" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" placeholder="留空则自动生成" />
          </label>

          <label class="block text-sm">
            <span class="mb-1 block text-slate-600">标题</span>
            <input v-model="form.title" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
          </label>

          <label class="block text-sm">
            <span class="mb-1 block text-slate-600">门类</span>
            <select v-model="form.department" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
              <option v-for="item in departments" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </label>
        </div>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">卡片开场信息（年龄 + 性别 + 一个核心症状，不带时间/过度描述）</span>
          <textarea v-model="form.brief" rows="2" class="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" placeholder="如：32岁，女性，妊娠35周，头痛" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">病人剧本（完整病历，仅供 AI 病人角色扮演）</span>
          <textarea v-model="form.patientScenario" rows="6" class="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">参考答案</span>
          <textarea v-model="form.referenceAnswer" rows="5" class="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
        </label>

        <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>

        <div class="flex justify-end gap-2">
          <button type="button" class="rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50" @click="$emit('close')">
            取消
          </button>
          <button type="submit" class="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60" :disabled="loading">
            {{ loading ? '保存中…' : '保存' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { CaseDetail } from '~/types'
import { apiFetch } from '~/composables/useApi'

const props = defineProps<{
  visible: boolean
  caseData: CaseDetail | null
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

const departments = [
  { label: '内科', value: 'internal' },
  { label: '外科', value: 'surgery' },
  { label: '妇产', value: 'obgyn' },
  { label: '儿科', value: 'pediatrics' },
  { label: '全科', value: 'general' },
  { label: '精神', value: 'psychiatry' },
]

const loading = ref(false)
const errorMessage = ref('')
const form = reactive({
  caseNo: '',
  title: '',
  department: 'internal',
  brief: '',
  patientScenario: '',
  referenceAnswer: '',
})

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return
    errorMessage.value = ''
    form.caseNo = props.caseData?.caseNo || ''
    form.title = props.caseData?.title || ''
    form.department = props.caseData?.department || 'internal'
    form.brief = props.caseData?.brief || ''
    form.patientScenario = props.caseData?.patientScenario || ''
    form.referenceAnswer = props.caseData?.referenceAnswer || ''
  },
)

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    if (props.caseData?.caseId) {
      await apiFetch(`/admin/cases/${props.caseData.caseId}`, {
        method: 'PUT',
        body: { ...form },
      })
    } else {
      await apiFetch('/admin/cases', {
        method: 'POST',
        body: { ...form },
      })
    }
    emit('saved')
    emit('close')
  } catch (error: any) {
    errorMessage.value = error.message || '保存失败'
  } finally {
    loading.value = false
  }
}
</script>
