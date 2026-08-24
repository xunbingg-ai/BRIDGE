<template>
  <div class="h-full rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-5 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-slate-900">历史练习记录</h2>
      <span class="text-sm text-slate-400">共 {{ total }} 条</span>
    </div>

    <div v-if="loading" class="flex h-48 items-center justify-center text-sm text-slate-400">
      加载中…
    </div>

    <div v-else-if="items.length === 0" class="flex h-48 items-center justify-center text-sm text-slate-400">
      暂无练习记录
    </div>

    <ul v-else class="space-y-3 overflow-y-auto">
      <li
        v-for="item in items"
        :key="item.sessionId"
        class="rounded-xl border border-slate-100 p-4 transition hover:border-blue-200"
      >
        <div class="mb-2 flex items-start justify-between gap-3">
          <div>
            <p class="font-medium text-slate-900">{{ item.caseTitle }}</p>
            <p class="mt-1 text-xs text-slate-400">
              {{ departmentLabel(item.department) }} · {{ formatDate(item.createAt) }}
            </p>
          </div>
          <span class="rounded-full px-2 py-1 text-xs" :class="statusClass(item.status)">
            {{ statusLabel(item.status) }}
          </span>
        </div>

        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold text-blue-600">
            {{ item.totalScore == null ? '—' : `${item.totalScore} 分` }}
          </span>
          <NuxtLink
            v-if="item.status === 'completed' || item.status === 'scoring'"
            :to="`/report/${item.sessionId}`"
            class="text-sm font-medium text-slate-600 hover:text-blue-600"
          >
            查看报告 →
          </NuxtLink>
        </div>
      </li>
    </ul>
  </div>
</template>

<script lang="ts" setup>
import type { SessionHistoryItem } from '~/types'
import { apiFetch } from '~/composables/useApi'

const items = ref<SessionHistoryItem[]>([])
const total = ref(0)
const loading = ref(false)

const departmentMap: Record<string, string> = {
  internal: '内科',
  surgery: '外科',
  obgyn: '妇产',
  pediatrics: '儿科',
  general: '全科',
  psychiatry: '精神',
}

function departmentLabel(value: string) {
  return departmentMap[value] || value
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    patient: '问询中',
    examiner: '考官阶段',
    scoring: '评分中',
    completed: '已完成',
    expired: '已超时',
  }
  return map[status] || status
}

function statusClass(status: string) {
  const map: Record<string, string> = {
    patient: 'bg-blue-50 text-blue-600',
    examiner: 'bg-amber-50 text-amber-600',
    scoring: 'bg-violet-50 text-violet-600',
    completed: 'bg-emerald-50 text-emerald-600',
    expired: 'bg-rose-50 text-rose-600',
  }
  return map[status] || 'bg-slate-100 text-slate-500'
}

async function loadHistory() {
  loading.value = true
  try {
    const data = await apiFetch<{ items: SessionHistoryItem[]; total: number }>('/sessions', {
      query: { page: 1, pageSize: 50 },
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)
</script>
