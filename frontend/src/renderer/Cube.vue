<script setup lang="ts">
import { computed } from 'vue'

const { width, height, depth, x, y, z, scale = 20, image, u, v } = defineProps<{
  width: number
  height: number
  depth: number
  x: number
  y: number
  z: number
  scale?: number
  image: string
  u: number
  v: number
  usize: number
  vsize: number
}>()

const imageUrl = computed(() => `url(${image})`)
</script>

<template>
  <div cube>
    <span face top />
    <span face bottom />

    <span face right />
    <span face left />

    <span face back />
    <span face front />
  </div>
</template>

<style scoped lang="postcss">
[cube] {
  @apply image-render-edge;
  position: relative;
  /*transform-origin: calc((v-bind(x) + v-bind(width) / 2) * 1px) calc(v-bind(y) + v-bind(height) / 2)
    calc(v-bind(z) + v-bind(depth) / 2);*/
  transform: scale3d(v-bind(scale), v-bind(scale), v-bind(scale))
    translate3d(calc(v-bind(x) * 1px), calc(v-bind(y) * 1px), calc(v-bind(z) * 1px));
}
[face] {
  @apply absolute
        bg-emerald-4 bg-center bg-no-repeat image-render-edge will-change-transform;
  /*@apply backface-hidden;*/
  background-image: v-bind(imageUrl);
  background-size: calc(v-bind(usize) * 1px) calc(v-bind(vsize) * 1px);
}

[top] {
  width: calc(v-bind(width) * 1px);
  height: calc(v-bind(depth) * 1px);
  transform: rotateX(90deg) translateZ(calc(v-bind(height) / 2 * 1px));
  background-position: calc(v-bind(u) * 1px - v-bind(depth) * 1px) calc(v-bind(v) * 1px);
}
[bottom] {
  width: calc(v-bind(width) * 1px);
  height: calc(v-bind(depth) * 1px);
  transform: rotateX(90deg) translateZ(calc(v-bind(width) / 2 * -1px));
  background-position: calc(v-bind(u) * 1px - (v-bind(width) + v-bind(depth)) * 1px) calc(v-bind(v) * 1px);
}

[left] {
  width: calc(v-bind(depth) * 1px);
  height: calc(v-bind(height) * 1px);
  transform: rotateY(90deg) translateZ(calc(v-bind(height) / 2 * 1px));
  background-position: calc(v-bind(u) * 1px - (v-bind(depth) + v-bind(width)) * 1px)
    calc(v-bind(v) * 1px - v-bind(depth) * 1px);
}
[right] {
  width: calc(v-bind(depth) * 1px);
  height: calc(v-bind(height) * 1px);
  transform: rotateY(-90deg) translateZ(calc(v-bind(depth) / 2 * 1px));
  background-position: calc(v-bind(u) * 1px) calc(v-bind(v) * 1px - v-bind(depth) * 1px);
}

[back] {
  width: calc(v-bind(width) * 1px);
  height: calc(v-bind(height) * 1px);
  transform: rotateY(180deg) translateZ(calc(v-bind(depth) / 2 * 1px));
  background-position: calc(v-bind(u) * 1px - 24px) calc(v-bind(v) * 1px - 8px);
}
[front] {
  width: calc(v-bind(width) * 1px);
  height: calc(v-bind(height) * 1px);
  transform: rotateY(0deg) translateZ(calc(v-bind(depth) / 2 * 1px));
  background-position: calc(v-bind(u) * 1px - 8px) calc(v-bind(v) * 1px - 8px);
}
</style>
