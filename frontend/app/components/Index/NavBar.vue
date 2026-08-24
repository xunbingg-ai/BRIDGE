<template>
  <div class="mb-5">
    <div class="flex flex-wrap gap-2">
      <button
        v-for="item in categories"
        :key="item.value"
        type="button"
        class="rounded-full border px-4 py-2 text-sm transition"
        :class="
          casesStore.department === item.value
            ? 'border-blue-600 bg-blue-600 text-white'
            : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-600'
        "
        @click="selectCategory(item.value)"
      >
        {{ item.label }}
      </button>
    </div>

    <SearchBox class="mt-4" />
  </div>
</template>

<script lang="ts" setup>
import SearchBox from '~/components/Index/SearchBox.vue'

const casesStore = useCasesStore()

const categories = [
  { label: '全部', value: 'all' },
  { label: '内科', value: 'internal' },
  { label: '外科', value: 'surgery' },
  { label: '妇产', value: 'obgyn' },
  { label: '儿科', value: 'pediatrics' },
  { label: '全科', value: 'general' },
  { label: '精神', value: 'psychiatry' },
]

function selectCategory(value: string) {
  casesStore.fetchCases({ department: value, search: casesStore.search, page: 1 })
}
</script>
