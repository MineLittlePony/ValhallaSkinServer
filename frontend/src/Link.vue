<script setup lang="ts">
const { href, icon, role = 'link' } = defineProps<{
  href: string
  icon?: string
  role?: string
}>()
</script>

<template>
  <a class="btn flex items-center justify-center gap-2" :role="role" :href="href">
    <div v-if="icon" :class="icon" />
    <div v-if="$slots.default" :class="icon && 'sm:block hidden'">
      <slot />
    </div>
  </a>
</template>
