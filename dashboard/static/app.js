const $ = (id) => document.getElementById(id);
let cameraBusy = false;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderParking(state) {
  const positions = state.context.positions_occupied;
  $("parking-grid").innerHTML = positions.map((occupied, index) => `
    <div class="parking-bay ${occupied ? "occupied" : ""}">
      <span class="bay-number">BAY ${String(index + 1).padStart(2, "0")}</span>
      <div class="car-shape" aria-hidden="true"></div>
      <span class="bay-status">${occupied ? "Occupied" : "Available"}</span>
    </div>`).join("");
  $("occupancy-count").textContent = `${state.parking.occupied} / ${positions.length}`;
}

function renderActuators(context) {
  const actuators = [
    ["Fan", context.fan, context.fan ? "ON" : "OFF"],
    ["Light", context.light, context.light ? "ON" : "OFF"],
    ["Entrance", context.entrance_gate, context.entrance_gate ? "OPEN" : "CLOSED"],
    ["Exit", context.exit_gate, context.exit_gate ? "OPEN" : "CLOSED"],
  ];
  $("actuator-list").innerHTML = actuators.map(([name, active, label]) => `
    <div class="actuator ${active ? "active" : ""}">
      <div class="actuator-state"></div><strong>${name}</strong><small>${label}</small>
    </div>`).join("");
}

function renderActivity(events, commands) {
  const activity = [
    ...events.map((item) => ({ ...item, kind: "input" })),
    ...commands.map((item) => ({ ...item, kind: "output", accepted: true })),
  ].sort((left, right) => right.time.localeCompare(left.time));
  if (!activity.length) {
    $("activity-list").innerHTML = '<p class="empty-state">Waiting for sensor messages…</p>';
    return;
  }
  $("activity-list").innerHTML = activity.slice(0, 12).map((item) => `
    <div class="activity-item">
      <span class="activity-time">${escapeHtml(item.time.split("T")[1] || item.time)}</span>
      <span class="activity-topic">${escapeHtml(item.topic)}<small>${escapeHtml(JSON.stringify(item.payload))}</small></span>
      <span class="activity-tag ${item.accepted ? "" : "rejected"}">${item.kind === "output" ? "OUTPUT" : item.accepted ? "INPUT" : "IGNORED"}</span>
    </div>`).join("");
}

function render(state) {
  const context = state.context;
  const connected = state.broker.connected;
  $("connection-pill").className = `connection-pill ${connected ? "online" : "offline"}`;
  $("connection-text").textContent = connected ? "MQTT Connected" : "MQTT Offline";
  $("broker-address").textContent = `Broker: ${state.broker.address}:${state.broker.port}`;
  $("temperature").textContent = context.temperature === null ? "—" : `${context.temperature.toFixed(1)}°`;
  $("lux").textContent = context.lux === null ? "—" : context.lux.toFixed(0);
  const plates = Object.keys(context.current_vehicles);
  $("vehicle-count").textContent = plates.length;
  $("vehicle-list").textContent = plates.length ? plates.join(", ") : "No registered vehicles";
  $("available-spaces").textContent = state.parking.available;
  $("garage-status").textContent = state.parking.full ? "Garage full" : "Garage available";
  $("enter-button").disabled = state.parking.full || cameraBusy;
  $("exit-button").disabled = cameraBusy;
  renderParking(state);
  renderActuators(context);
  renderActivity(state.events, state.commands);
  $("last-command").textContent = state.last_command
    ? `${state.last_command.topic} → ${JSON.stringify(state.last_command.payload)}`
    : "No commands yet";
}

async function refresh() {
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    if (!response.ok) throw new Error(`State request failed (${response.status})`);
    render(await response.json());
  } catch (error) {
    $("connection-pill").className = "connection-pill offline";
    $("connection-text").textContent = "Dashboard Offline";
  }
}

async function inspect(direction) {
  cameraBusy = true;
  $("enter-button").disabled = true;
  $("exit-button").disabled = true;
  const message = $("api-message");
  message.className = "api-message";
  message.textContent = `Starting ${direction} inspection. Hold the license plate steady for 3 seconds…`;
  try {
    const response = await fetch(`/api/camera/${direction}`, { method: "POST" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || `Camera request failed (${response.status})`);
    message.className = "api-message success";
    message.textContent = `Recognized ${body.result.license_plate}. Event published.`;
  } catch (error) {
    message.className = "api-message error";
    message.textContent = error.message;
  } finally {
    cameraBusy = false;
    await refresh();
  }
}

$("enter-button").addEventListener("click", () => inspect("enter"));
$("exit-button").addEventListener("click", () => inspect("exit"));
refresh();
setInterval(refresh, 1000);
