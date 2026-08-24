<template>
  <div>
    <NavBar />

    <div class="mb-5 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-slate-900">病例列表</h1>
      <span class="text-sm text-slate-400">共 {{ casesStore.total }} 个病例</span>
    </div>

    <div v-if="casesStore.loading && casesStore.items.length === 0" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="index in 6"
        :key="index"
        class="h-44 animate-pulse rounded-2xl border border-slate-200 bg-white"
      />
    </div>

    <div v-else-if="casesStore.items.length === 0" class="rounded-2xl border border-dashed border-slate-200 bg-white py-16 text-center">
      <p class="text-sm text-slate-400">没有找到相关病例</p>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <CaseBox v-for="caseItem in casesStore.items" :key="caseItem.caseId" :case-item="caseItem" />
    </div>

    <div v-if="casesStore.loadingMore" class="py-6 text-center text-sm text-slate-400">
      加载更多…
    </div>

    <div v-else-if="!casesStore.hasMore && casesStore.items.length" class="py-6 text-center text-sm text-slate-400">
      已经到底啦
    </div>

    <div ref="loadMoreTrigger" class="h-1" />
  </div>
</template>

<script lang="ts" setup>
import NavBar from '~/components/Index/NavBar.vue'
import CaseBox from '~/components/Index/CaseBox.vue'

const casesStore = useCasesStore()
const loadMoreTrigger = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

function shouldLoadMore() {
  return (
    casesStore.hasMore &&
    !casesStore.loading &&
    !casesStore.loadingMore &&
    loadMoreTrigger.value &&
    loadMoreTrigger.value.getBoundingClientRect().top < window.innerHeight + 240
  )
}

function maybeLoadMore() {
  if (shouldLoadMore()) {
    casesStore.loadMore()
  }
}

function handleScroll() {
  if (shouldLoadMore()) {
    casesStore.loadMore()
  }
}

onMounted(async () => {
  if (casesStore.items.length === 0) {
    await casesStore.fetchCases()
  }

  window.addEventListener('scroll', handleScroll, { passive: true })

  if ('IntersectionObserver' in window && loadMoreTrigger.value) {
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && shouldLoadMore()) {
          casesStore.loadMore()
        }
      },
      { rootMargin: '240px' },
    )
    observer.observe(loadMoreTrigger.value)
  }

  await nextTick()
  maybeLoadMore()
})

watch(
  () => [casesStore.items.length, casesStore.total],
  async () => {
    await nextTick()
    maybeLoadMore()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
  observer?.disconnect()
})
</script>
