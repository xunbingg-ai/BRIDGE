<template>
  <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-5">
      <h2 class="text-lg font-semibold text-slate-900">大模型接入管理</h2>
      <p class="mt-1 text-sm text-slate-400">配置 API 地址、请求头、密钥，并测试模型响应速度。</p>
    </div>

    <form class="space-y-4" @submit.prevent="save">
      <label class="block text-sm">
        <span class="mb-1 block text-slate-600">配置名称</span>
        <input v-model="form.name" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" />
      </label>

      <label class="block text-sm">
        <span class="mb-1 block text-slate-600">Base URL</span>
        <input v-model="form.baseUrl" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" placeholder="https://api.openai.com/v1" />
      </label>

      <label class="block text-sm">
        <span class="mb-1 block text-slate-600">API Key</span>
        <input v-model="form.apiKey" type="password" class="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" :placeholder="form.hasApiKey ? '已保存密钥，留空则不修改' : '请输入 API Key'" />
      </label>

      <label class="block text-sm">
        <span class="mb-1 block text-slate-600">自定义请求头 JSON</span>
        <textarea v-model="headersText" rows="4" class="w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 font-mono text-xs outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" placeholder='{"X-Provider": "example"}' />
      </label>

      <div class="grid gap-4 md:grid-cols-2">
        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">主模型</span>
          <select v-model="form.model" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
            <option value="">请选择主模型</option>
            <option v-for="model in models" :key="model" :value="model">{{ model }}</option>
          </select>
        </label>

        <label class="block text-sm">
          <span class="mb-1 block text-slate-600">备用模型</span>
          <select v-model="form.backupModel" class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
            <option value="">请选择备用模型</option>
            <option v-for="model in models" :key="model" :value="model">{{ model }}</option>
          </select>
        </label>
      </div>

      <p v-if="errorMessage" class="text-sm text-rose-600">{{ errorMessage }}</p>
      <p v-if="successMessage" class="text-sm text-emerald-600">{{ successMessage }}</p>

      <div class="flex flex-wrap gap-2">
        <button type="button" class="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60" :disabled="loading" @click="fetchModels">
          {{ loadingModels ? '获取中…' : '获取模型列表' }}
        </button>
        <button type="submit" class="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60" :disabled="loading">
          {{ saving ? '保存中…' : '保存配置' }}
        </button>
        <button type="button" class="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60" :disabled="testingPrimary || !form.model" @click="testModel(form.model)">
          {{ testingPrimary ? '测试中…' : '测试主模型' }}
        </button>
        <button type="button" class="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-60" :disabled="testingBackup || !form.backupModel" @click="testModel(form.backupModel)">
          {{ testingBackup ? '测试中…' : '测试备用模型' }}
        </button>
      </div>
    </form>

    <div v-if="testResult" class="mt-5 rounded-xl bg-slate-50 p-4">
      <div class="mb-2 flex items-center justify-between text-sm">
        <span class="font-medium text-slate-700">模型：{{ testResult.model }}</span>
        <span class="font-semibold text-blue-600">{{ testResult.latencyMs }} ms</span>
      </div>
      <p v-if="testResult.content" class="text-sm leading-6 text-slate-600">{{ testResult.content }}</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { LlmConfig, LlmTestResult } from '~/types'
import { apiFetch } from '~/composables/useApi'

const models = ref<string[]>([])
const loading = ref(false)
const loadingModels = ref(false)
const saving = ref(false)
const testingPrimary = ref(false)
const testingBackup = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const testResult = ref<LlmTestResult | null>(null)
const headersText = ref('{}')

const form = reactive<LlmConfig>({
  name: '默认模型配置',
  baseUrl: 'https://api.openai.com/v1',
  apiKey: '',
  hasApiKey: false,
  headers: {},
  model: null,
  backupModel: null,
})

function parseHeaders() {
  try {
    const parsed = JSON.parse(headersText.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('请求头必须是 JSON 对象')
    }
    return parsed
  } catch (error: any) {
    errorMessage.value = error.message || '请求头 JSON 格式错误'
    throw error
  }
}

async function loadConfig() {
  const data = await apiFetch<{ config: LlmConfig }>('/admin/llm-config')
  const config = data.config || {}
  form.name = config.name || '默认模型配置'
  form.baseUrl = config.baseUrl || 'https://api.openai.com/v1'
  form.apiKey = ''
  form.hasApiKey = Boolean(config.hasApiKey)
  form.headers = config.headers || {}
  form.model = config.model || null
  form.backupModel = config.backupModel || null
  headersText.value = JSON.stringify(form.headers, null, 2)
}

async function fetchModels() {
  loadingModels.value = true
  errorMessage.value = ''
  try {
    const data = await apiFetch<{ models: string[] }>('/admin/llm-config/models', {
      method: 'POST',
      body: {
        baseUrl: form.baseUrl,
        apiKey: form.apiKey,
        headers: parseHeaders(),
      },
    })
    models.value = data.models || []
    successMessage.value = `获取到 ${models.value.length} 个模型`
  } catch (error: any) {
    errorMessage.value = error.message || '获取模型列表失败'
  } finally {
    loadingModels.value = false
  }
}

async function save() {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await apiFetch('/admin/llm-config', {
      method: 'PUT',
      body: {
        name: form.name,
        baseUrl: form.baseUrl,
        apiKey: form.apiKey,
        headers: parseHeaders(),
        model: form.model,
        backupModel: form.backupModel,
      },
    })
    await loadConfig()
    successMessage.value = '配置已保存'
  } catch (error: any) {
    errorMessage.value = error.message || '保存失败'
  } finally {
    saving.value = false
  }
}

async function testModel(model: string | null) {
  if (!model) return
  errorMessage.value = ''
  successMessage.value = ''
  testResult.value = null
  if (model === form.model) testingPrimary.value = true
  if (model === form.backupModel) testingBackup.value = true

  try {
    const data = await apiFetch<{ result: LlmTestResult }>('/admin/llm-config/test', {
      method: 'POST',
      body: {
        baseUrl: form.baseUrl,
        apiKey: form.apiKey,
        headers: parseHeaders(),
        model,
      },
    })
    testResult.value = data.result
  } catch (error: any) {
    errorMessage.value = error.message || '测试失败'
  } finally {
    testingPrimary.value = false
    testingBackup.value = false
  }
}

onMounted(loadConfig)
</script>
