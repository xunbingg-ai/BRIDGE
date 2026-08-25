<template>
  <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-slate-900">CSV 批量导入</h2>
      <p class="mt-1 text-sm text-slate-400">先下载模板，本地批量填写后上传。</p>
    </div>

    <div class="mb-5 flex flex-wrap gap-3">
      <button
        type="button"
        class="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700"
        @click="downloadTemplate"
      >
        下载 CSV 模板
      </button>

      <label class="cursor-pointer rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
        选择 CSV 文件
        <input type="file" accept=".csv,text/csv" class="hidden" @change="handleFile" />
      </label>
    </div>

    <div v-if="fileName" class="mb-4 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600">
      已选择：{{ fileName }}
    </div>

    <p v-if="uploading" class="text-sm text-slate-500">上传解析中…</p>
    <p v-else-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>

    <div v-else-if="result" class="space-y-3">
      <div class="flex flex-wrap gap-3 text-sm">
        <span class="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">新增 {{ result.inserted }} 条</span>
        <span class="rounded-full bg-blue-50 px-3 py-1 text-blue-700">更新 {{ result.updated }} 条</span>
        <span class="rounded-full bg-rose-50 px-3 py-1 text-rose-700">错误 {{ result.errors?.length || 0 }} 条</span>
      </div>

      <ul v-if="result.errors?.length" class="space-y-1 text-sm text-rose-600">
        <li v-for="error in result.errors" :key="error.line">
          第 {{ error.line }} 行：{{ error.message }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { apiFetch } from '~/composables/useApi'

interface ImportResult {
  inserted: number
  updated: number
  errors: { line: number; message: string }[]
}

const emit = defineEmits<{ imported: [] }>()

const fileName = ref('')
const uploading = ref(false)
const errorMessage = ref('')
const result = ref<ImportResult | null>(null)

function downloadTemplate() {
  if (typeof window === 'undefined') return
  const headers = [
    'case_no',
    'title',
    'department',
    'brief',
    'patient_scenario',
    'reference_answer',
  ]
  const sample = [
    '',
    '示例病例：发热伴咳嗽',
    'internal',
    '30岁，男性，发热咳嗽',
    '### 一般情况\n张先生（化名），男，30岁，上班族，汉族。\n### 主诉\n发热、咳嗽3天。',
    '诊断：社区获得性肺炎；治疗：抗感染、对症支持。',
  ]
  const csv = [headers.join(','), sample.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(',')].join('\n')
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'case_template.csv'
  anchor.click()
  URL.revokeObjectURL(url)
}

async function handleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  fileName.value = file.name
  result.value = null
  errorMessage.value = ''
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const data = await apiFetch<ImportResult>('/admin/cases/import', {
      method: 'POST',
      body: formData,
    })
    result.value = data
    emit('imported')
  } catch (error: any) {
    errorMessage.value = error.message || '上传失败'
  } finally {
    uploading.value = false
    input.value = ''
  }
}
</script>
