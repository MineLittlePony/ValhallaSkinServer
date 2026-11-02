<script setup lang="ts">
import type { icons } from '@iconify-json/line-md/icons.json'

type Icons = `i-line-md:${keyof typeof icons}` | (string & {})

const { href, icon, role = 'link' } = defineProps <{
  href: string
  icon?: Icons
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
