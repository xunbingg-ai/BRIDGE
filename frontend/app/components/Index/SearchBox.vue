<template>
  <div>
    <div class="flex gap-2">
      <input
        v-model="search"
        type="search"
        placeholder="搜索病例标题、摘要或编号"
        class="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
        @keyup.enter="applySearch"
      />
      <button
        type="button"
        class="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
        @click="applySearch"
      >
        搜索
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
const casesStore = useCasesStore()
const search = ref(casesStore.search)

let timer: ReturnType<typeof setTimeout> | null = null

watch(search, (value) => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    casesStore.fetchCases({ search: value, page: 1 })
  }, 350)
})

function applySearch() {
  if (timer) clearTimeout(timer)
  casesStore.fetchCases({ search: search.value, page: 1 })
}

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>
