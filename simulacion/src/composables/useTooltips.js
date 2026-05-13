import { reactive } from 'vue'
import * as THREE from 'three'

export function useTooltips() {
  const tooltipPositions = reactive({})

  function initForCaja(id) {
    tooltipPositions[id] = { x: 0, y: 0, visible: false }
  }

  function getStyle(id) {
    const p = tooltipPositions[id]
    if (!p || !p.visible) return { display: 'none' }
    return {
      position: 'fixed',
      left: p.x + 'px',
      top: p.y + 'px',
      transform: 'translate(-50%, -160%)',
      pointerEvents: 'none',
      zIndex: 40,
    }
  }

  function updatePosition(mesh, id, camera, renderer) {
    if (!mesh || !camera || !renderer) return
    const worldPos = new THREE.Vector3()
    mesh.getWorldPosition(worldPos)

    const projected = worldPos.clone().project(camera)
    const rect = renderer.domElement.getBoundingClientRect()

    tooltipPositions[id].x = Math.round(((projected.x + 1) / 2) * rect.width + rect.left)
    tooltipPositions[id].y = Math.round(((-projected.y + 1) / 2) * rect.height + rect.top) - 48
    tooltipPositions[id].visible = true
  }

  return { tooltipPositions, initForCaja, getStyle, updatePosition }
}
