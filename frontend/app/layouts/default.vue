<template>
  <div class="flex min-h-screen flex-col">
    <AppBar />
    <main class="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
      <slot />
    </main>
  </div>
</template>

<script lang="ts" setup>
import AppBar from '~/components/Public/AppBar.vue'
</script>
