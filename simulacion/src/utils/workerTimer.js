// Timers backed by a Web Worker to avoid browser throttling in background tabs/windows.
// Browsers throttle main-thread setTimeout/setInterval to ≥1 s (or more) when unfocused;
// workers are not subject to the same restrictions.

const workerCode = `
const pending = new Map();

const tick = () => {
  const now = Date.now();
  for (const [id, entry] of pending) {
    if (now >= entry.target) {
      if (entry.delay != null) {
        entry.target = now + entry.delay;  // interval: reschedule
      } else {
        pending.delete(id);               // timeout: fire once
      }
      self.postMessage(id);
    }
  }
};

setInterval(tick, 50);

self.onmessage = ({ data: { type, id, delay } }) => {
  if (type === 'set')      pending.set(id, { target: Date.now() + delay });
  else if (type === 'interval') pending.set(id, { target: Date.now() + delay, delay });
  else if (type === 'clear')    pending.delete(id);
};
`

const worker = new Worker(
  URL.createObjectURL(new Blob([workerCode], { type: 'application/javascript' })),
)

const oneshotCallbacks = new Map()
const intervalCallbacks = new Map()
let nextId = 0

worker.onmessage = ({ data: id }) => {
  const fn = intervalCallbacks.get(id) ?? oneshotCallbacks.get(id)
  if (oneshotCallbacks.has(id)) oneshotCallbacks.delete(id)
  if (fn) fn()
}

export function workerSetTimeout(fn, delay) {
  const id = ++nextId
  oneshotCallbacks.set(id, fn)
  worker.postMessage({ type: 'set', id, delay })
  return id
}

export function workerClearTimeout(id) {
  if (id == null) return
  oneshotCallbacks.delete(id)
  worker.postMessage({ type: 'clear', id })
}

export function workerSetInterval(fn, delay) {
  const id = ++nextId
  intervalCallbacks.set(id, fn)
  worker.postMessage({ type: 'interval', id, delay })
  return id
}

export function workerClearInterval(id) {
  if (id == null) return
  intervalCallbacks.delete(id)
  worker.postMessage({ type: 'clear', id })
}
