<template>
  <main class="placeholder-page">
    <section>
      <RouterLink class="back-link" :to="{ name: 'menu' }">Volver al menu</RouterLink>
      <h1>Simulacion</h1>
      <p>Esta vista esta preparada para conectar aqui la simulacion de SmartQ.</p>
    </section>
  </main>
</template>

<style scoped>
.placeholder-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  background: #f5f8f3;
  color: #173326;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

section {
  width: min(680px, 100%);
}

.back-link {
  color: #00843d;
  font-weight: 800;
  text-decoration: none;
}

h1 {
  margin: 18px 0 8px;
  font-size: clamp(2.2rem, 7vw, 4rem);
}

p {
  margin: 0;
  color: #506459;
  font-size: 1.05rem;
}
</style>
