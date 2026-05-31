<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

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
              Organiza el personal por turnos de lunes a sábado usando los datos guardados en la
              base de datos.
            </p>
          </div>

          <div class="summary">
            <strong>{{ employees.length }}</strong>
            <span>empleados</span>
            <strong>{{ totalAssignments }}</strong>
            <span>asignaciones</span>
          </div>
        </div>

        <div class="header-actions">
          <button type="button" class="secondary-button" :disabled="loading" @click="loadData">
            <span v-if="loading" class="btn-spinner"></span>
            <span v-else>Recargar datos</span>
          </button>
          <button type="button" :disabled="loading || savingSchedule" @click="saveSchedule">
            <span v-if="savingSchedule" class="btn-spinner"></span>
            <span v-else>Guardar turnos</span>
          </button>
        </div>
      </header>

      <form class="employee-form" @submit.prevent="addEmployee">
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
          ID pulsera
          <input
            v-model="newEmployee.braceletId"
            type="text"
            placeholder="Ej. P-009"
            :disabled="savingEmployee"
          />
        </label>

        <button type="submit" :disabled="savingEmployee">
          <span v-if="savingEmployee" class="btn-spinner"></span>
          <span v-else>Añadir empleado</span>
        </button>
      </form>

      <p v-if="errorMessage" class="status-message error" role="alert">{{ errorMessage }}</p>
      <p v-else-if="successMessage" class="status-message success">{{ successMessage }}</p>
      <p v-else-if="loading" class="status-message">Cargando empleados y turnos...</p>

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
                    ^
                  </button>
                  <button
                    type="button"
                    aria-label="Bajar empleado"
                    :disabled="index === day.morning.length - 1"
                    @click="moveEmployee(day, 'morning', index, 1)"
                  >
                    v
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
                    ^
                  </button>
                  <button
                    type="button"
                    aria-label="Bajar empleado"
                    :disabled="index === day.afternoon.length - 1"
                    @click="moveEmployee(day, 'afternoon', index, 1)"
                  >
                    v
                  </button>
                </div>
              </li>
            </ol>
          </div>
        </article>
      </section>
    </section>
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
}

h2 {
  margin: 0;
  font-size: 1.35rem;
}

.shift-block {
  display: grid;
  gap: 10px;
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
  color: #d71920;
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
</style>
