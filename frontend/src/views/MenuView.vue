<template>
  <main class="menu-page">
    <section class="menu-shell">
      <div class="brand-block">
        <span class="kicker">SmartQ</span>
        <h1>Panel principal</h1>
        <p>Selecciona el area que quieres abrir para continuar con la gestion del sistema.</p>
      </div>

      <div class="actions-grid">
        <RouterLink class="menu-action simulation" :to="{ name: 'simulacion' }">
          <span class="action-icon">S</span>
          <span>
            <strong>Simulacion</strong>
            <small>Visualiza el flujo de clientes y el estado de las colas.</small>
          </span>
        </RouterLink>

        <RouterLink class="menu-action staff" :to="{ name: 'gestion-empleados' }">
          <span class="action-icon">E</span>
          <span>
            <strong>Gestion de empleados</strong>
            <small>Consulta turnos, asignaciones y disponibilidad del personal.</small>
          </span>
        </RouterLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.menu-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgba(0, 132, 61, 0.16), transparent 30%),
    linear-gradient(135deg, #f5f8f3 0%, #e9f1ea 48%, #f8faf8 100%);
  color: #173326;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.menu-shell {
  width: min(920px, 100%);
  display: grid;
  gap: 28px;
}

.brand-block {
  max-width: 620px;
}

.kicker {
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

h1 {
  margin: 18px 0 10px;
  font-size: clamp(2.4rem, 6vw, 4.5rem);
  line-height: 1;
}

p {
  margin: 0;
  color: #506459;
  font-size: 1.08rem;
  line-height: 1.6;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.menu-action {
  min-height: 180px;
  display: flex;
  align-items: flex-end;
  gap: 18px;
  padding: 24px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 22px 50px rgba(23, 51, 38, 0.12);
  color: inherit;
  text-decoration: none;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.menu-action:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 132, 61, 0.42);
  box-shadow: 0 28px 60px rgba(23, 51, 38, 0.16);
}

.menu-action:focus-visible {
  outline: 3px solid rgba(0, 132, 61, 0.28);
  outline-offset: 4px;
}

.action-icon {
  flex: 0 0 54px;
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: white;
  font-size: 1.35rem;
  font-weight: 900;
}

.simulation .action-icon {
  background: #00843d;
}

.staff .action-icon {
  background: #d71920;
}

strong {
  display: block;
  margin-bottom: 8px;
  font-size: 1.25rem;
}

small {
  display: block;
  color: #627267;
  font-size: 0.94rem;
  line-height: 1.45;
}

@media (max-width: 680px) {
  .menu-page {
    place-items: start;
    padding: 24px 18px;
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }

  .menu-action {
    min-height: 150px;
    padding: 20px;
  }
}
</style>
