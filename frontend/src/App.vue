<script setup lang="ts">
import { useFetch } from '@vueuse/core'
import clsx from 'clsx'

import Link from './Link.vue'
import CharacterRenderer from './renderer/CharacterRenderer.vue'
import './App.css'

type SkinType = 'skin' | 'elytra' | 'cape' | (string & {})

type Textures = Record<SkinType, {
  url: string
  metadata: Record<string, string>
}>

const rootClass = clsx(
  'dark:bg-stone-800 light:bg-slate-300 dark:text-neutral-200 light:text-neutral-800',
  'grid grid-rows-[auto_1fr_auto] min-h-screen *:px-4 *:py-2',
)

const { isFetching, data, error } = useFetch('/api/v1/textures').json<Textures>()
</script>

<template>
  <div :class="rootClass">
    <header class="flex items-center gap-4 rounded-lb-xl rounded-rb-xl dark:bg-zinc-900 light:bg-stone-100">
      <Link icon="i-line-md:home" href="https://minelittlepony-mod.com/">
        Home
      </Link>
      <div v-if="isFetching">
        Loading authentication data
      </div>
      <Link v-else-if="error" icon="i-line-md:login" href="/api/v1/auth/xbox">
        Sign in
      </Link>

      <Link v-else-if="data" icon="i-line-md:logout" href="/api/v1/auth/logout">
        Sign out
      </Link>

      <div class="flex-grow" />
      <Link
        icon="i-line-md:github"
        class="text-lg"
        href="https://github.com/MineLittlePony/ValhallaSkinServer"
        aria-label="View Website on GitHub"
      />
    </header>
    <main>
      <CharacterRenderer v-if="data" :image="data.skin?.url" />
    </main>
    <footer className="flex items-center justify-center gap-2">
      &copy; &ndash; MineLittlePony Team
    </footer>
  </div>
</template>
