<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-slate-900">管理员控制台</h1>
        <p class="mt-1 text-sm text-slate-400">管理病例与大模型接入配置</p>
      </div>
    </div>

    <div class="mb-6 flex flex-wrap gap-2">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="rounded-full border px-4 py-2 text-sm transition"
        :class="
          activeTab === tab.value
            ? 'border-blue-600 bg-blue-600 text-white'
            : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-600'
        "
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </button>
    </div>

    <CaseManager v-if="activeTab === 'cases'" :key="caseManagerKey" />
    <CsvUploader v-else-if="activeTab === 'csv'" @imported="caseManagerKey += 1" />
    <LlmManager v-else />
  </div>
</template>

<script lang="ts" setup>
import CaseManager from '~/components/admin/CaseManager.vue'
import CsvUploader from '~/components/admin/CsvUploader.vue'
import LlmManager from '~/components/admin/LlmManager.vue'

definePageMeta({
  middleware: ['auth', 'admin'],
})

const activeTab = ref<'cases' | 'csv' | 'llm'>('cases')
const caseManagerKey = ref(0)

const tabs = [
  { label: '病例管理', value: 'cases' },
  { label: 'CSV 批量导入', value: 'csv' },
  { label: '大模型管理', value: 'llm' },
]
</script>
