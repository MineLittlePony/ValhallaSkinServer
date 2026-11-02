<script setup lang="ts">
import { refManualReset, toRefs, useMouse, usePointerLock } from '@vueuse/core'
import { watch } from 'vue'
import Cube from './Cube.vue'

const { image } = defineProps<{
  image: string
}>()

const { lock, unlock, element } = usePointerLock()
const { x, y } = useMouse({ type: 'movement' })

const rotation = refManualReset(() => ({ yaw: 0, pitch: 0 }))
const { yaw, pitch } = toRefs(rotation)

interface Box {
  x: number
  y: number
  z: number
  width: number
  height: number
  depth: number
  u: number
  v: number
  scale?: number
}

const boxes: Box[] = [
  {
    x: 0,
    y: 0,
    z: 0,
    width: 8,
    height: 8,
    depth: 8,
    u: 0,
    v: 0,
  },
  {
    x: 0,
    y: 10,
    z: 0,
    width: 8,
    height: 12,
    depth: 4,
    u: 0,
    v: -12,
  },
  {
    x: 8,
    y: 10,
    z: 0,
    width: 4,
    height: 12,
    depth: 4,
    u: -32,
    v: -12,
  },
  {
    x: -4,
    y: 10,
    z: 0,
    width: 4,
    height: 12,
    depth: 4,
    u: -32,
    v: -44,
  },
]

function resetAll() {
  rotation.reset()
}

watch([x, y], ([x, y]) => {
  if (!element.value)
    return

  yaw.value += x / 2
  pitch.value -= y / 2
  pitch.value = Math.min(Math.max(pitch.value, -60), 60)
})
</script>

<template>
  <div>
    <button
      class="btn"
      @click="resetAll"
    >
      Reset Rotation
    </button>
    <div scene @mousedown.capture="lock" @mouseup="unlock">
      <div viewport>
        <Cube v-for="(box, n) in boxes" :key="n" v-bind="box" :usize="64" :vsize="64" :image="image" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="postcss">
[scene] {
  @apply flex justify-center items-center box-border cursor-all-scroll all:preserve-3d perspective-800;
}
[viewport] {
  transform-origin: center;
  transform: rotateX(calc(v-bind(pitch) * 1deg)) rotateY(calc(-1 * v-bind(yaw) * 1deg));
}
</style>
