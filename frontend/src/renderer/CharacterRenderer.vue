<script setup lang="ts">
import * as THREE from 'three'
import { reactive, shallowRef, useTemplateRef, watch } from 'vue'

const { image: _image } = defineProps<{
  image: string
}>()

const canvas = useTemplateRef('canvas')

const angles = reactive({
  head: 0,
  headYaw: 0,
  leftArm: 0,
  leftArmYaw: 0,
  rightArm: 0,
  rightArmYaw: 0,
  leftLeg: 0,
  leftLegYaw: 0,
  rightLeg: 0,
  rightLegYaw: 0,
})

const headMeshRef = shallowRef<THREE.Mesh>()
const neckMeshRef = shallowRef<THREE.Mesh>()
const leftArmMeshRef = shallowRef<THREE.Mesh>()
const rightArmMeshRef = shallowRef<THREE.Mesh>()
const leftLegMeshRef = shallowRef<THREE.Mesh>()
const rightLegMeshRef = shallowRef<THREE.Mesh>()

watch(angles, (angles) => {
  if (neckMeshRef.value) {
    neckMeshRef.value.rotation.y = angles.headYaw
  }
  if (headMeshRef.value) {
    headMeshRef.value.rotation.x = angles.head
  }
  if (leftArmMeshRef.value) {
    leftArmMeshRef.value.rotation.x = angles.leftArm
    leftArmMeshRef.value.rotation.z = angles.leftArmYaw
  }
  if (rightArmMeshRef.value) {
    rightArmMeshRef.value.rotation.x = angles.rightArm
    rightArmMeshRef.value.rotation.z = angles.rightArmYaw
  }
  if (leftLegMeshRef.value) {
    leftLegMeshRef.value.rotation.x = angles.leftLeg
    leftLegMeshRef.value.rotation.z = angles.leftLegYaw
  }
  if (rightLegMeshRef.value) {
    rightLegMeshRef.value.rotation.x = angles.rightLeg
    rightLegMeshRef.value.rotation.z = angles.rightLegYaw
  }
})

watch(canvas, (canvas) => {
  if (canvas !== null) {
    initMeshes(canvas)
  }
}, { once: true })

function initMeshes(canvas: HTMLCanvasElement) {
  const camera = new THREE.PerspectiveCamera(70, canvas.clientWidth / canvas.clientHeight, 0.1, 1000)
  camera.position.z = 40

  const scene = new THREE.Scene()
  const mesh = new THREE.Mesh()
  const material = new THREE.MeshNormalMaterial()
  {
    const body = new THREE.BoxGeometry(8, 12, 4)
    const bodyMesh = new THREE.Mesh(body, material)
    mesh.add(bodyMesh)
    {
      const neckMesh = neckMeshRef.value = new THREE.Mesh()

      const head = new THREE.BoxGeometry(8, 8, 8)
      const headMesh = headMeshRef.value = new THREE.Mesh(head, material)

      headMesh.pivot = new THREE.Vector3(0, 4, 0)
      headMesh.position.y = -10
      headMesh.rotation.x = angles.head
      neckMesh.rotation.y = angles.headYaw
      neckMesh.add(headMesh)
      mesh.add(neckMesh)
    }
    {
      const rightArm = new THREE.BoxGeometry(4, 12, 4)
      const rightArmMesh = rightArmMeshRef.value = new THREE.Mesh(rightArm, material)
      rightArmMesh.pivot = new THREE.Vector3(0, -4, 0)
      rightArmMesh.position.x = 6
      bodyMesh.add(rightArmMesh)
    }
    {
      const leftArm = new THREE.BoxGeometry(4, 12, 4)
      const leftArmMesh = leftArmMeshRef.value = new THREE.Mesh(leftArm, material)
      leftArmMesh.pivot = new THREE.Vector3(0, -4, 0)
      leftArmMesh.position.x = -6
      bodyMesh.add(leftArmMesh)
    }
    {
      const rightLeg = new THREE.BoxGeometry(4, 12, 4)
      const rightLegMesh = rightLegMeshRef.value = new THREE.Mesh(rightLeg, material)
      rightLegMesh.pivot = new THREE.Vector3(0, -6, 0)
      rightLegMesh.position.y = 12
      rightLegMesh.position.x = 2
      rightLegMesh.rotation.x = angles.rightLeg
      bodyMesh.add(rightLegMesh)
    }
    {
      const leftLeg = new THREE.BoxGeometry(4, 12, 4)
      const leftLegMesh = leftLegMeshRef.value = new THREE.Mesh(leftLeg, material)
      leftLegMesh.pivot = new THREE.Vector3(0, -6, 0)
      leftLegMesh.position.y = 12
      leftLegMesh.position.x = -2
      bodyMesh.add(leftLegMesh)
    }
  }

  scene.add(mesh)
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
  renderer.setSize(canvas.clientWidth, canvas.clientHeight)
  renderer.setAnimationLoop(animate)

  function animate(time: number) {
    // mesh.rotation.x = time / 2000
    mesh.rotation.x = 1.1 * Math.PI
    mesh.rotation.y = 0.25 * Math.PI
    mesh.rotation.y = time / 2000

    renderer.render(scene, camera)
  }
}

function toDegrees(radians: number): number {
  return Math.round(radians * 180 / Math.PI)
}
</script>

<template>
  <div>
    <div class="grid cols-6 w-200 gap-1">
      Head Yaw: <span :title="`${String(angles.headYaw / Math.PI)}* PI`">{{ toDegrees(angles.headYaw) }}&deg;</span>
      <input
        v-model.number="angles.headYaw"
        type="range"
        :min="-Math.PI * 0.16" :max="Math.PI * 0.16"
        :step="Math.PI / 64"
      >
      Head Pitch: <span>{{ toDegrees(angles.head) }}&deg;</span>
      <input
        v-model.number="angles.head"
        type="range"
        :min="-Math.PI * 0.5" :max="Math.PI * 0.5"
        :step="Math.PI / 32"
      >
      Right Arm: <span>{{ toDegrees(angles.rightArm) }}&deg;</span>
      <input
        v-model.number="angles.rightArm"
        type="range"
        :min="Math.PI * -0.75" :max="Math.PI * 0.75"
        :step="Math.PI / 64"
      >
      Right Arm Yaw: <span>{{ toDegrees(angles.rightArmYaw) }}&deg;</span>
      <input
        v-model.number="angles.rightArmYaw"
        type="range"
        :min="Math.PI * -0.75" :max="Math.PI * 0.75"
        :step="Math.PI / 64"
      >
      Left Arm: <span>{{ toDegrees(angles.leftArm) }}&deg;</span>
      <input
        v-model.number="angles.leftArm"
        type="range"
        :min="Math.PI * -0.75" :max="Math.PI * 0.75"
        :step="Math.PI / 64"
      >
      Left Arm Yaw: <span>{{ toDegrees(angles.leftArmYaw) }}&deg;</span>
      <input
        v-model.number="angles.leftArmYaw"
        type="range"
        :min="Math.PI * -0.75" :max="Math.PI * 0.75"
        :step="Math.PI / 64"
      >
      Right Leg: <span>{{ toDegrees(angles.rightLeg) }}&deg;</span>
      <input
        v-model.number="angles.rightLeg"
        type="range"
        :min="-Math.PI * 0.5" :max="Math.PI * 0.5"
        :step="Math.PI / 16"
      >
      Right Leg Yaw: <span>{{ toDegrees(angles.rightLegYaw) }}&deg;</span>
      <input
        v-model.number="angles.rightLegYaw"
        type="range"
        :min="-Math.PI * 0.5" :max="Math.PI * 0.5"
        :step="Math.PI / 16"
      >
      Left Leg: <span>{{ toDegrees(angles.leftLeg) }}&deg;</span>
      <input
        v-model.number="angles.leftLeg"
        type="range"
        :min="-Math.PI * 0.5" :max="Math.PI * 0.5"
        :step="Math.PI / 16"
      >
      Left Leg Yaw: <span>{{ toDegrees(angles.leftLegYaw) }}&deg;</span>
      <input
        v-model.number="angles.leftLegYaw"
        type="range"
        :min="-Math.PI * 0.5" :max="Math.PI * 0.5"
        :step="Math.PI / 16"
      >
    </div>
    <canvas ref="canvas" class="h-160 w-120" />
  </div>
</template>
