<template>
  <main class="menu-page">
    <section class="menu-shell">
      <div class="brand-block">
        <img class="menu-logo" src="/assets/logomercadona2.png" alt="Mercadona" />
        <span class="kicker">SmartQ</span>
        <h1>Panel principal</h1>
        <p>Selecciona el area que quieres abrir para continuar con la gestion del sistema.</p>
      </div>

      <div class="actions-list">
        <RouterLink class="menu-action simulation" :to="{ name: 'simulacion' }">
          <span class="action-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" style="width: 28px; height: 28px;">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" />
            </svg>
          </span>
          <span>
            <strong>Monitor de colas</strong>
            <small>Visualiza el flujo de clientes y el estado de las colas.</small>
          </span>
        </RouterLink>

        <RouterLink class="menu-action staff" :to="{ name: 'gestion-empleados' }">
          <span class="action-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="width: 28px; height: 28px;">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          </span>
          <span>
            <strong>Gestion de empleados</strong>
            <small>Consulta turnos, asignaciones y disponibilidad del personal.</small>
          </span>
        </RouterLink>
        <RouterLink class="menu-action graficas" :to="{ name: 'graficas-view' }">
          <span class="action-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" style="width: 28px; height: 28px;">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
          </span>
          <span>
            <strong>Graficas y métricas</strong>
            <small>Consulta tiempos de espera, tendencias y metricas por caja.</small>
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
  display: grid;
  gap: 16px;
}

.menu-logo {
  justify-self: center;
  width: min(400px, 100vw);
  max-height: 170px;
  object-fit: contain;
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

h1 {
  margin: 0;
  font-size: clamp(2.4rem, 6vw, 4.5rem);
  line-height: 1;
}

p {
  margin: 0;
  color: #506459;
  font-size: 1.08rem;
  line-height: 1.6;
}

.actions-list {
  display: grid;
  gap: 14px;
}

.menu-action {
  min-height: 118px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 22px 24px;
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

.graficas .action-icon {
  background: #173326;
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

  .menu-action {
    min-height: 128px;
    padding: 20px;
  }
}
</style>
