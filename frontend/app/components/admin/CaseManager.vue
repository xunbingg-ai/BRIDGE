<template>
  <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-slate-900">病例管理</h2>
        <p class="mt-1 text-sm text-slate-400">共 {{ total }} 条</p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          v-if="selectedIds.length"
          type="button"
          class="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-60"
          :disabled="deleting"
          @click="batchDelete"
        >
          {{ deleting ? '删除中…' : `删除选中 (${selectedIds.length})` }}
        </button>

        <input
          v-model="search"
          type="search"
          placeholder="搜索标题、摘要或编号"
          class="w-64 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
        />
        <button
          type="button"
          class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          @click="openCreate"
        >
          新增病例
        </button>
      </div>
    </div>

    <div v-if="loading" class="py-12 text-center text-sm text-slate-400">
      加载中…
    </div>

    <div v-else-if="items.length === 0" class="py-12 text-center text-sm text-slate-400">
      暂无病例
    </div>

    <div v-else class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-slate-100 text-xs text-slate-400">
          <tr>
            <th class="w-10 pb-3 pr-2">
              <input
                type="checkbox"
                class="h-4 w-4 rounded border-slate-300 text-blue-600"
                :checked="allSelected"
                @change="toggleAll"
              />
            </th>
            <th class="pb-3 pr-4">编号</th>
            <th class="pb-3 pr-4">标题</th>
            <th class="pb-3 pr-4">门类</th>
            <th class="pb-3 pr-4">难度</th>
            <th class="pb-3 text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.caseId" class="border-b border-slate-50">
            <td class="py-3 pr-2">
              <input
                type="checkbox"
                class="h-4 w-4 rounded border-slate-300 text-blue-600"
                :checked="selectedIds.includes(item.caseId)"
                @change="toggleOne(item.caseId)"
              />
            </td>
            <td class="py-3 pr-4 text-slate-500">{{ item.caseNo }}</td>
            <td class="py-3 pr-4 font-medium text-slate-800">{{ item.title }}</td>
            <td class="py-3 pr-4 text-slate-600">{{ departmentLabel(item.department) }}</td>
            <td class="py-3 pr-4 text-slate-600">{{ difficultyLabel(item.difficulty) }}</td>
            <td class="py-3 text-right">
              <div class="flex justify-end gap-3">
                <button type="button" class="font-medium text-blue-600 hover:underline" @click="openEdit(item)">
                  修改
                </button>
                <button type="button" class="font-medium text-rose-600 hover:underline" :disabled="deleting" @click="deleteOne(item)">
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <CaseForm
      :visible="formVisible"
      :case-data="editingCase"
      @close="formVisible = false"
      @saved="loadCases"
    />
  </div>
</template>

<script lang="ts" setup>
import type { CaseDetail } from '~/types'
import { apiFetch } from '~/composables/useApi'
import CaseForm from '~/components/admin/CaseForm.vue'

const items = ref<CaseDetail[]>([])
const total = ref(0)
const loading = ref(false)
const deleting = ref(false)
const search = ref('')
const formVisible = ref(false)
const editingCase = ref<CaseDetail | null>(null)
const selectedIds = ref<number[]>([])

let searchTimer: ReturnType<typeof setTimeout> | null = null

const departmentMap: Record<string, string> = {
  internal: '内科',
  surgery: '外科',
  obgyn: '妇产',
  pediatrics: '儿科',
  general: '全科',
  psychiatry: '精神',
}

const allSelected = computed(() => items.value.length > 0 && selectedIds.value.length === items.value.length)

function departmentLabel(value: string) {
  return departmentMap[value] || value
}

function difficultyLabel(value: number) {
  const map: Record<number, string> = { 1: '简单', 2: '中等', 3: '困难' }
  return map[value] || '中等'
}

function toggleAll() {
  selectedIds.value = allSelected.value ? [] : items.value.map((item) => item.caseId)
}

function toggleOne(caseId: number) {
  selectedIds.value = selectedIds.value.includes(caseId)
    ? selectedIds.value.filter((id) => id !== caseId)
    : [...selectedIds.value, caseId]
}

async function loadCases() {
  loading.value = true
  try {
    const data = await apiFetch<{ items: CaseDetail[]; total: number }>('/admin/cases', {
      query: { search: search.value, page: 1, pageSize: 100 },
    })
    items.value = data.items
    total.value = data.total
    const currentIds = new Set(items.value.map((item) => item.caseId))
    selectedIds.value = selectedIds.value.filter((id) => currentIds.has(id))
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingCase.value = null
  formVisible.value = true
}

function openEdit(caseItem: CaseDetail) {
  editingCase.value = caseItem
  formVisible.value = true
}

async function deleteOne(caseItem: CaseDetail) {
  if (!window.confirm(`确定删除病例「${caseItem.title}」吗？`)) return
  deleting.value = true
  try {
    await apiFetch(`/admin/cases/${caseItem.caseId}`, { method: 'DELETE' })
    selectedIds.value = selectedIds.value.filter((id) => id !== caseItem.caseId)
    await loadCases()
  } catch (error: any) {
    alert(error.message || '删除失败')
  } finally {
    deleting.value = false
  }
}

async function batchDelete() {
  if (!selectedIds.value.length) return
  if (!window.confirm(`确定删除选中的 ${selectedIds.value.length} 个病例吗？`)) return

  deleting.value = true
  try {
    await apiFetch('/admin/cases/batch-delete', {
      method: 'POST',
      body: { caseIds: selectedIds.value },
    })
    selectedIds.value = []
    await loadCases()
  } catch (error: any) {
    alert(error.message || '批量删除失败')
  } finally {
    deleting.value = false
  }
}

watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadCases, 350)
})

onMounted(loadCases)

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer)
})
</script>
