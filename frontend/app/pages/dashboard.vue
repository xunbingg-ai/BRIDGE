<template>
  <div class="grid min-h-[calc(100vh-10rem)] gap-6 lg:grid-cols-2">
    <ProfileBox class="h-[calc(100vh-10rem)]" />
    <HistoryBox class="h-[calc(100vh-10rem)]" />
  </div>
</template>

<script lang="ts" setup>
import ProfileBox from '~/components/Dashboard/ProfileBox.vue'
import HistoryBox from '~/components/Dashboard/HistoryBox.vue'

definePageMeta({
  middleware: ['auth'],
})
</script>
