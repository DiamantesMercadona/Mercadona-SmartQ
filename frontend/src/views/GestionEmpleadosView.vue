<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const employees = ref([])
const loading = ref(false)
const savingEmployee = ref(false)
const savingSchedule = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const newEmployee = reactive({
  name: '',
  surname: '',
  braceletId: '',
})

const draggedAssignment = ref(null)
const dragOverTarget = ref(null)

const weekSchedule = reactive([
  {
    day: 'Lunes',
    dbDay: 'lunes',
    morning: [],
    afternoon: [],
  },
  {
    day: 'Martes',
    dbDay: 'martes',
    morning: [],
    afternoon: [],
  },
  {
    day: 'Miercoles',
    dbDay: 'miercoles',
    morning: [],
    afternoon: [],
  },
  {
    day: 'Jueves',
    dbDay: 'jueves',
    morning: [],
    afternoon: [],
  },
  {
    day: 'Viernes',
    dbDay: 'viernes',
    morning: [],
    afternoon: [],
  },
  {
    day: 'Sabado',
    dbDay: 'sabado',
    morning: [],
    afternoon: [],
  },
])

const totalAssignments = computed(() =>
  weekSchedule.reduce((total, day) => total + day.morning.length + day.afternoon.length, 0),
)

const normalizeEmployee = (employee) => ({
  id: Number(employee.id),
  name: employee.name ?? employee.nombre ?? '',
  surname: employee.surname ?? employee.apellidos ?? '',
  braceletId: employee.braceletId ?? employee.id_pulsera ?? '',
})

const normalizeOrder = (order) => {
  const parsedOrder = typeof order === 'string' ? JSON.parse(order || '[]') : order

  return (Array.isArray(parsedOrder) ? parsedOrder : [])
    .map((item) => Number(typeof item === 'object' ? item.id : item))
    .filter(Boolean)
}

const getEmployee = (id) => employees.value.find((employee) => employee.id === Number(id))

const shiftSelections = reactive(
  Object.fromEntries(
    weekSchedule.flatMap((day) => [
      [`${day.day}-morning`, ''],
      [`${day.day}-afternoon`, ''],
    ]),
  ),
)

const selectionKey = (day, shift) => `${day.day}-${shift}`

const getAvailableEmployees = (day, shift) =>
  employees.value.filter((employee) => !day[shift].includes(employee.id))

const requestJson = async (path, options = {}) => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Error HTTP ${response.status}`)
  }

  if (response.status === 204) return null
  return response.json()
}

const loadEmployees = async () => {
  const data = await requestJson('/empleados')
  const list = data?.empleados ?? data?.employees ?? data ?? []
  employees.value = list.map(normalizeEmployee)
}

const loadSchedule = async () => {
  const data = await requestJson('/turnos')
  const shifts = data?.turnos ?? data?.shifts ?? data ?? []

  for (const day of weekSchedule) {
    day.morning = []
    day.afternoon = []
  }

  for (const item of shifts) {
    const day = weekSchedule.find((candidate) => candidate.dbDay === item.dia_semana)
    if (!day) continue

    const shift = item.turno === 'mañana' || item.turno === 'manana' || item.turno === 'morning'
      ? 'morning'
      : 'afternoon'

    day[shift] = normalizeOrder(item.orden ?? item.orden_json ?? item.order)
  }
}

const loadData = async () => {
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await Promise.all([loadEmployees(), loadSchedule()])
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? `${error.message}. Revisa que existan GET /api/v1/empleados y GET /api/v1/turnos.`
        : 'No se han podido cargar empleados y turnos.'
  } finally {
    loading.value = false
  }
}

const addEmployee = async () => {
  const name = newEmployee.name.trim()
  const surname = newEmployee.surname.trim()
  const braceletId = newEmployee.braceletId.trim()

  if (!name || !surname) return

  savingEmployee.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const data = await requestJson('/empleados', {
      method: 'POST',
      body: JSON.stringify({
        nombre: name,
        apellidos: surname,
        id_pulsera: braceletId || null,
      }),
    })

    const created = data?.empleado ?? data?.employee ?? data
    if (created?.id) {
      employees.value.push(normalizeEmployee(created))
    } else {
      await loadEmployees()
    }

    newEmployee.name = ''
    newEmployee.surname = ''
    newEmployee.braceletId = ''
    successMessage.value = 'Empleado guardado.'
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? `${error.message}. Revisa que exista POST /api/v1/empleados.`
        : 'No se ha podido guardar el empleado.'
  } finally {
    savingEmployee.value = false
  }
}

const addEmployeeToShift = (day, shift) => {
  const key = selectionKey(day, shift)
  const employeeId = Number(shiftSelections[key])

  if (!employeeId || day[shift].includes(employeeId)) return

  day[shift].push(employeeId)
  shiftSelections[key] = ''
}

const schedulePayload = () =>
  weekSchedule.flatMap((day) => [
    {
      dia_semana: day.dbDay,
      turno: 'mañana',
      orden: day.morning.map((id) => ({ id })),
    },
    {
      dia_semana: day.dbDay,
      turno: 'tarde',
      orden: day.afternoon.map((id) => ({ id })),
    },
  ])

const saveSchedule = async () => {
  savingSchedule.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await requestJson('/turnos', {
      method: 'PUT',
      body: JSON.stringify({
        turnos: schedulePayload(),
      }),
    })
    successMessage.value = 'Turnos guardados.'
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? `${error.message}. Revisa que exista PUT /api/v1/turnos.`
        : 'No se han podido guardar los turnos.'
  } finally {
    savingSchedule.value = false
  }
}

const setDragData = (event, day, shift, index) => {
  draggedAssignment.value = {
    day,
    shift,
    index,
    employeeId: day[shift][index],
  }

  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(day[shift][index]))
}

const setDragOverTarget = (day, shift, index = day[shift].length) => {
  dragOverTarget.value = {
    key: selectionKey(day, shift),
    index,
  }
}

const isDragOverTarget = (day, shift, index) =>
  dragOverTarget.value?.key === selectionKey(day, shift) && dragOverTarget.value?.index === index

const isDraggedAssignment = (day, shift, index) =>
  draggedAssignment.value?.day === day &&
  draggedAssignment.value?.shift === shift &&
  draggedAssignment.value?.index === index

const clearDragState = () => {
  draggedAssignment.value = null
  dragOverTarget.value = null
}

const dropEmployee = (targetDay, targetShift, targetIndex = targetDay[targetShift].length) => {
  const source = draggedAssignment.value

  if (!source) return

  const sourceList = source.day[source.shift]
  const targetList = targetDay[targetShift]
  const isSameShift = source.day === targetDay && source.shift === targetShift

  if (!isSameShift && targetList.includes(source.employeeId)) {
    clearDragState()
    return
  }

  const [employeeId] = sourceList.splice(source.index, 1)
  const adjustedTargetIndex =
    isSameShift && source.index < targetIndex ? targetIndex - 1 : targetIndex

  targetList.splice(adjustedTargetIndex, 0, employeeId)
  clearDragState()
}

const moveEmployee = (day, shift, index, direction) => {
  const list = day[shift]
  const newIndex = index + direction

  if (newIndex < 0 || newIndex >= list.length) return

  const [employeeId] = list.splice(index, 1)
  list.splice(newIndex, 0, employeeId)
}

const removeEmployeeFromShift = (day, shift, index) => {
  day[shift].splice(index, 1)
}

let toastTimeout = null
watch([errorMessage, successMessage], ([newErr, newSucc]) => {
  if (newErr || newSucc) {
    if (toastTimeout) clearTimeout(toastTimeout)
    toastTimeout = setTimeout(() => {
      errorMessage.value = ''
      successMessage.value = ''
    }, 4000)
  }
})

onMounted(loadData)
</script>

<template>
  <main class="employees-page">
    <section class="page-shell">
      <header class="hero">
        <RouterLink class="back-link" :to="{ name: 'menu' }">
          <span class="back-arrow">←</span> Volver al menú principal
        </RouterLink>
        <span class="kicker">SmartQ</span>
        <div class="hero-content">
          <div>
            <h1>Gestión de empleados</h1>
            <p>
              Consulta y modifica la plantilla de empleados y su asignación de turnos.
            </p>
          </div>

          <div class="summary">
            <strong>{{ employees.length }}</strong>
            <span>empleados registrados</span>
            <strong>{{ totalAssignments }}</strong>
            <span>turnos asignados</span>
          </div>
        </div>
      </header>

      <form class="employee-form" @submit.prevent="addEmployee">
        <h2 class="form-title">Añadir empleados</h2>
        <label>
          Nombre
          <input v-model="newEmployee.name" type="text" placeholder="Ej. Ana" :disabled="savingEmployee" />
        </label>

        <label>
          Apellidos
          <input
            v-model="newEmployee.surname"
            type="text"
            placeholder="Ej. Garcia Perez"
            :disabled="savingEmployee"
          />
        </label>

        <label>
          ID de pulsera
          <input
            v-model="newEmployee.braceletId"
            type="text"
            placeholder="Ej. P-009"
            :disabled="savingEmployee"
          />
        </label>

        <button type="submit" :disabled="savingEmployee">
          <span v-if="savingEmployee" class="btn-spinner"></span>
          <span v-else>Añadir</span>
        </button>
      </form>

      <p v-if="loading" class="status-message">Cargando empleados y turnos...</p>

      <div class="schedule-section-header">
        <h2 class="schedule-section-title">Planificación semanal</h2>
      </div>

      <section class="schedule-grid" aria-label="Turnos semanales">
        <article v-for="day in weekSchedule" :key="day.day" class="day-card">
          <h2>{{ day.day }}</h2>

          <div class="shift-block">
            <div class="shift-heading">
              <h3>Mañana</h3>
              <span>{{ day.morning.length }} empleados</span>
            </div>

            <div class="shift-picker">
              <select v-model="shiftSelections[selectionKey(day, 'morning')]" :disabled="loading">
                <option value="">Seleccionar empleado</option>
                <option
                  v-for="employee in getAvailableEmployees(day, 'morning')"
                  :key="employee.id"
                  :value="employee.id"
                >
                  {{ employee.name }} {{ employee.surname }}
                </option>
              </select>
              <button
                type="button"
                :disabled="loading || !shiftSelections[selectionKey(day, 'morning')]"
                @click="addEmployeeToShift(day, 'morning')"
              >
                Añadir
              </button>
            </div>

            <ol
              class="employee-list"
              :class="{ 'drop-at-end': isDragOverTarget(day, 'morning', day.morning.length) }"
              @dragover.prevent="setDragOverTarget(day, 'morning')"
              @dragleave="dragOverTarget = null"
              @drop="dropEmployee(day, 'morning')"
            >
              <li
                v-for="(employeeId, index) in day.morning"
                :key="employeeId"
                draggable="true"
                :class="{
                  dragging: isDraggedAssignment(day, 'morning', index),
                  'drop-target': isDragOverTarget(day, 'morning', index),
                }"
                @dragstart="setDragData($event, day, 'morning', index)"
                @dragend="clearDragState"
                @dragover.prevent="setDragOverTarget(day, 'morning', index)"
                @drop.stop="dropEmployee(day, 'morning', index)"
              >
                <span class="position">{{ index + 1 }}</span>
                <span class="employee-info">
                  <span class="employee-name">
                    {{ getEmployee(employeeId)?.name }} {{ getEmployee(employeeId)?.surname }}
                  </span>
                  <span v-if="getEmployee(employeeId)?.braceletId" class="bracelet-id">
                    Pulsera {{ getEmployee(employeeId)?.braceletId }}
                  </span>
                </span>
                <div class="order-actions">
                  <button
                    type="button"
                    aria-label="Subir empleado"
                    :disabled="index === 0"
                    @click="moveEmployee(day, 'morning', index, -1)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                  </button>
                  <button
                    type="button"
                    aria-label="Bajar empleado"
                    :disabled="index === day.morning.length - 1"
                    @click="moveEmployee(day, 'morning', index, 1)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="btn-remove-assignment"
                    aria-label="Quitar de turno"
                    @click="removeEmployeeFromShift(day, 'morning', index)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              </li>
            </ol>
          </div>

          <div class="shift-block afternoon">
            <div class="shift-heading">
              <h3>Tarde</h3>
              <span>{{ day.afternoon.length }} empleados</span>
            </div>

            <div class="shift-picker">
              <select v-model="shiftSelections[selectionKey(day, 'afternoon')]" :disabled="loading">
                <option value="">Seleccionar empleado</option>
                <option
                  v-for="employee in getAvailableEmployees(day, 'afternoon')"
                  :key="employee.id"
                  :value="employee.id"
                >
                  {{ employee.name }} {{ employee.surname }}
                </option>
              </select>
              <button
                type="button"
                :disabled="loading || !shiftSelections[selectionKey(day, 'afternoon')]"
                @click="addEmployeeToShift(day, 'afternoon')"
              >
                Añadir
              </button>
            </div>

            <ol
              class="employee-list"
              :class="{ 'drop-at-end': isDragOverTarget(day, 'afternoon', day.afternoon.length) }"
              @dragover.prevent="setDragOverTarget(day, 'afternoon')"
              @dragleave="dragOverTarget = null"
              @drop="dropEmployee(day, 'afternoon')"
            >
              <li
                v-for="(employeeId, index) in day.afternoon"
                :key="employeeId"
                draggable="true"
                :class="{
                  dragging: isDraggedAssignment(day, 'afternoon', index),
                  'drop-target': isDragOverTarget(day, 'afternoon', index),
                }"
                @dragstart="setDragData($event, day, 'afternoon', index)"
                @dragend="clearDragState"
                @dragover.prevent="setDragOverTarget(day, 'afternoon', index)"
                @drop.stop="dropEmployee(day, 'afternoon', index)"
              >
                <span class="position">{{ index + 1 }}</span>
                <span class="employee-info">
                  <span class="employee-name">
                    {{ getEmployee(employeeId)?.name }} {{ getEmployee(employeeId)?.surname }}
                  </span>
                  <span v-if="getEmployee(employeeId)?.braceletId" class="bracelet-id">
                    Pulsera {{ getEmployee(employeeId)?.braceletId }}
                  </span>
                </span>
                <div class="order-actions">
                  <button
                    type="button"
                    aria-label="Subir empleado"
                    :disabled="index === 0"
                    @click="moveEmployee(day, 'afternoon', index, -1)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                  </button>
                  <button
                    type="button"
                    aria-label="Bajar empleado"
                    :disabled="index === day.afternoon.length - 1"
                    @click="moveEmployee(day, 'afternoon', index, 1)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="btn-remove-assignment"
                    aria-label="Quitar de turno"
                    @click="removeEmployeeFromShift(day, 'afternoon', index)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
              </li>
            </ol>
          </div>
        </article>
      </section>

      <div class="save-actions">
        <button type="button" class="btn-save-schedule" :disabled="loading || savingSchedule" @click="saveSchedule">
          <span v-if="savingSchedule" class="btn-spinner"></span>
          <span v-else>Guardar turnos</span>
        </button>
      </div>
    </section>

    <!-- Toast Popup Notifications -->
    <Transition name="toast-fade">
      <div v-if="errorMessage || successMessage" :class="['toast-popup', errorMessage ? 'error' : 'success']">
        <div class="toast-content">
          <span class="toast-icon" v-if="successMessage">
            <svg class="toast-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </span>
          <span class="toast-icon" v-else>
            <svg class="toast-icon-svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
          </span>
          <span class="toast-message">{{ errorMessage || successMessage }}</span>
        </div>
        <div class="toast-timer">
          <svg class="timer-svg" width="20" height="20" viewBox="0 0 24 24">
            <circle class="timer-bg" cx="12" cy="12" r="10" stroke="rgba(255, 255, 255, 0.25)" stroke-width="3" fill="none" />
            <circle class="timer-progress" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" />
          </svg>
        </div>
      </div>
    </Transition>
  </main>
</template>

<style scoped>
.employees-page {
  min-height: 100vh;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgba(0, 132, 61, 0.16), transparent 28%),
    linear-gradient(135deg, #f5f8f3 0%, #e9f1ea 48%, #f8faf8 100%);
  color: #173326;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.page-shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 24px;
}

.hero {
  display: grid;
  gap: 16px;
}

.back-link {
  width: fit-content;
  color: #00843d;
  font-weight: 800;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}

.back-link:hover {
  color: #00662f;
  transform: translateX(-4px);
}

.kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(0, 132, 61, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #007d3a;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

h1 {
  margin: 0 0 10px;
  font-size: clamp(2.4rem, 6vw, 4.5rem);
  line-height: 1;
}

p {
  max-width: 720px;
  margin: 0;
  color: #506459;
  font-size: 1.08rem;
  line-height: 1.6;
}

.summary {
  min-width: 168px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  padding: 18px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 16px 38px rgba(23, 51, 38, 0.1);
}

.summary strong {
  color: #00843d;
  font-size: 1.55rem;
  line-height: 1;
}

.summary span {
  align-self: center;
  color: #627267;
  font-size: 0.92rem;
}

.employee-form {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(220px, 1.2fr) minmax(140px, 0.8fr) auto;
  gap: 14px;
  align-items: end;
  padding: 20px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 44px rgba(23, 51, 38, 0.1);
}

.form-title {
  grid-column: 1 / -1;
  margin: 0 0 4px 0;
  font-size: 1.25rem;
  font-weight: 800;
  color: #173326;
}

label {
  display: grid;
  gap: 8px;
  color: #506459;
  font-size: 0.9rem;
  font-weight: 800;
}

input,
select {
  width: 100%;
  min-height: 46px;
  box-sizing: border-box;
  border: 1px solid rgba(23, 51, 38, 0.18);
  border-radius: 8px;
  padding: 0 14px;
  background: #ffffff;
  color: #173326;
  font: inherit;
}

input:focus,
select:focus {
  border-color: #00843d;
  outline: 3px solid rgba(0, 132, 61, 0.18);
}

button {
  min-height: 42px;
  border: 0;
  border-radius: 8px;
  background: #00843d;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.employee-form button {
  min-height: 46px;
  padding: 0 18px;
}

.secondary-button {
  border: 1px solid rgba(23, 51, 38, 0.16);
  background: #ffffff;
  color: #173326;
}

.status-message {
  margin: 0;
  padding: 14px 16px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
  color: #506459;
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.45;
}

.status-message.error {
  border-color: rgba(215, 25, 32, 0.22);
  background: rgba(215, 25, 32, 0.08);
  color: #9f151a;
}

.status-message.success {
  border-color: rgba(0, 132, 61, 0.22);
  background: rgba(0, 132, 61, 0.08);
  color: #007d3a;
}

.schedule-section-header {
  margin-top: 24px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(23, 51, 38, 0.08);
}

h2.schedule-section-title {
  margin: 0;
  font-size: clamp(1.8rem, 4.5vw, 2.6rem);
  line-height: 1.1;
  color: #173326;
  font-weight: 800;
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.day-card {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 42px rgba(23, 51, 38, 0.1);
  align-content: start;
}

h2 {
  margin: 0;
  font-size: 1.35rem;
}

.shift-block {
  display: grid;
  gap: 10px;
  align-content: start;
}

.shift-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h3 {
  margin: 0;
  color: #00843d;
  font-size: 0.95rem;
  text-transform: uppercase;
}

.afternoon h3 {
  color: #ffa101;
}

.shift-heading span {
  color: #627267;
  font-size: 0.82rem;
  font-weight: 700;
}

.shift-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.shift-picker select {
  min-height: 40px;
  padding: 0 10px;
  font-size: 0.9rem;
}

.shift-picker button {
  min-height: 40px;
  padding: 0 12px;
  background: #007d3a;
  font-size: 0.9rem;
}

.employee-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.employee-list.drop-at-end {
  padding-bottom: 10px;
  border-bottom: 2px dashed rgba(0, 132, 61, 0.34);
}

.employee-list li {
  min-height: 50px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border: 1px solid rgba(23, 51, 38, 0.1);
  border-radius: 8px;
  background: #ffffff;
  cursor: grab;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    opacity 0.16s ease,
    transform 0.16s ease;
}

.employee-list li:active {
  cursor: grabbing;
}

.employee-list li.dragging {
  opacity: 0.48;
  transform: scale(0.99);
}

.employee-list li.drop-target {
  border-color: rgba(0, 132, 61, 0.58);
  box-shadow: inset 4px 0 0 #00843d;
}

.position {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f0f5ef;
  color: #00843d;
  font-weight: 900;
}

.employee-name {
  overflow-wrap: anywhere;
  font-weight: 800;
}

.employee-info {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.bracelet-id {
  color: #627267;
  font-size: 0.78rem;
  font-weight: 800;
}

.order-actions {
  display: flex;
  gap: 6px;
}

.order-actions button {
  width: 34px;
  min-height: 34px;
  background: #173326;
}

.order-actions button.btn-remove-assignment {
  background: #506459;
}

.order-actions button.btn-remove-assignment:hover {
  background: #d71920;
  color: #ffffff;
}

@media (max-width: 980px) {
  .hero-content,
  .employee-form,
  .schedule-grid {
    grid-template-columns: 1fr;
  }

  .summary {
    width: fit-content;
  }
}

@media (max-width: 680px) {
  .employees-page {
    padding: 24px 18px;
  }

  .employee-list li {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .order-actions {
    grid-column: 2;
  }

  .shift-picker {
    grid-template-columns: 1fr;
  }
}

/* Spinner for action buttons */
.btn-spinner {
  display: inline-flex;
  width: 18px;
  height: 18px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.save-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.btn-save-schedule {
  min-height: 48px;
  padding: 0 32px;
  font-size: 1.05rem;
  box-shadow: 0 8px 24px rgba(0, 132, 61, 0.15);
  transition: all 0.2s ease;
}

.btn-save-schedule:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(0, 132, 61, 0.22);
  background: #00662f;
}

/* Toast Transition */
.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-fade-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}

/* Toast Popups */
.toast-popup {
  position: fixed;
  top: 32px;
  right: 32px;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 280px;
  max-width: 420px;
  padding: 14px 20px;
  border-radius: 10px;
  box-shadow: 0 20px 48px rgba(23, 51, 38, 0.16);
  color: #ffffff;
}

.toast-popup.success {
  background: #00843d;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.toast-popup.error {
  background: #d71920;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.toast-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toast-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.toast-message {
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.4;
}

.toast-timer {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.timer-svg {
  transform: rotate(-90deg);
}

.timer-progress {
  stroke-dasharray: 62.8;
  stroke-dashoffset: 0;
  animation: toast-countdown 4s linear forwards;
}

@keyframes toast-countdown {
  from {
    stroke-dashoffset: 0;
  }
  to {
    stroke-dashoffset: 62.8;
  }
}
</style>
