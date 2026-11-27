import * as THREE from "three";
import { OrbitControls } from "/static/vendor/OrbitControls.js";

const $ = (id) => document.getElementById(id);
const form = $("job-form");
const statusBox = $("status");
const files = [];
let fileSeq = 0;
let lastMesh = null;
let lastJob = null;
let lastMetrics = null;
let lastSection = null;
let sourceData = null;
let sectionEndpoints = null;
const mapView = { zoom: 1, x: 0, y: 0 };
let mapDrawFrame = 0;
let previewSeq = 0;
let previewTimer = null;
let schemaSeq = 0;
let areaRules = [];
let pendingAreaRules = null;
let currentAreas = [];
let pendingGlobalRules = null;
let pendingRuleOrder = null;
let ruleOrder = ["points", "contours", "faults", "areas", "global",
                 "bounds", "completer"];
const pendingFields = {};

/* ---------- tabs ---------- */
function showTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.tab === name);
  });
  $("map-pane").classList.toggle("is-hidden", name !== "map");
  $("result-pane").classList.toggle("is-hidden", name !== "result");
  if (name === "map") drawMap(lastMesh);
  requestAnimationFrame(resizeView);
}
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => showTab(tab.dataset.tab));
});

/* ---------- dropped files ---------- */
function inferRole(name) {
  const lower = name.toLowerCase();
  if (/(surface|trend|func|grid|поверхность)/.test(lower)) return "surfaces";
  if (/(area|polygon|mask|полигон|площад)/.test(lower)) return "areas";
  if (/(contour|isoline|iso_|izol|isol|изолин)/.test(lower)) return "contours";
  if (/(fault|flt|break|разлом)/.test(lower)) return "faults";
  return "points";
}

function addFiles(fileList) {
  lastJob = null;
  for (const file of fileList) {
    files.push({ id: ++fileSeq, file, role: inferRole(file.name), enabled: true });
  }
  renderFiles();
  schedulePreview();
}

function renderFiles() {
  const list = $("file-list");
  list.innerHTML = "";
  for (const item of files) {
    const row = document.createElement("div");
    row.className = "file-row";
    const enabled = document.createElement("input");
    enabled.type = "checkbox";
    enabled.className = "file-enabled";
    enabled.checked = item.enabled;
    enabled.title = "include this source";
    enabled.addEventListener("change", () => {
      item.enabled = enabled.checked;
      lastJob = null;
      schedulePreview();
    });
    const name = document.createElement("span");
    name.className = "file-name";
    name.textContent = item.file.name;
    name.title = item.file.name;
    const role = document.createElement("select");
    role.className = "file-role";
    role.dataset.id = item.id;
    for (const [value, label] of [["points", "points"], ["contours", "contours"],
                                  ["faults", "faults"], ["areas", "areas"],
                                  ["surfaces", "surfaces"]]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = item.role === value;
      role.appendChild(option);
    }
    role.addEventListener("change", () => { item.role = role.value; lastJob = null; schedulePreview(); });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove";
    remove.title = "remove";
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      const index = files.findIndex((entry) => entry.id === item.id);
      if (index >= 0) files.splice(index, 1);
      lastJob = null;
      renderFiles();
      schedulePreview();
    });
    row.append(enabled, name, role, remove);
    list.appendChild(row);
  }
  $("map-title").textContent = files.length ? `${files.length} source file${files.length > 1 ? "s" : ""}` : "Source data";
  if (!files.length) {
    sourceData = null;
    drawMap(null);
  }
}

$("browse").addEventListener("click", () => $("files").click());
$("files").addEventListener("change", (event) => addFiles(event.target.files));
const dropzone = $("dropzone");
for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-over");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-over");
  });
}
dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));
dropzone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    $("files").click();
  }
});

function activeFiles() {
  return files.filter((item) => item.enabled);
}

function appendFieldSettings(body) {
  for (const key of ["x_field", "y_field", "z_field", "weight_field"]) {
    if ($(key).value.trim()) body.append(key, $(key).value.trim());
  }
  for (const key of ["min_value", "max_value"]) {
    if ($(key).value !== "") body.append(key, $(key).value);
  }
  if ($("exclude_zero").checked) body.append("exclude_zero", "true");
}

function setFieldValue(key, value) {
  const select = $(key);
  if ([...select.options].some((option) => option.value === value)) {
    select.value = value;
  } else {
    pendingFields[key] = value;
  }
}

function populateFieldOptions(schema) {
  const names = new Set();
  for (const role of ["points", "faults", "contours", "areas"]) {
    for (const name of schema[role] || []) names.add(name);
  }
  const definitions = [
    ["x_field", "geometry"],
    ["y_field", "geometry"],
    ["z_field", "auto / coordinate z"],
    ["weight_field", "1"],
  ];
  for (const [key, fallback] of definitions) {
    const select = $(key);
    const current = select.value || pendingFields[key] || "";
    select.innerHTML = "";
    const auto = document.createElement("option");
    auto.value = "";
    auto.textContent = fallback;
    select.appendChild(auto);
    for (const name of [...names].sort()) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      select.appendChild(option);
    }
    if ([...select.options].some((option) => option.value === current)) {
      select.value = current;
    } else {
      select.value = "";
    }
    delete pendingFields[key];
  }
  const zSelect = $("z_field");
  const contourFiles = activeFiles().some((item) => item.role === "contours");
  if (!zSelect.value && contourFiles && names.size === 1) {
    zSelect.value = [...names][0];
  }
}

function currentGlobalRules() {
  const rules = [];
  if ($("mean-enabled").checked) {
    rules.push({ mode: "mean", value: Number($("mean-value").value) });
  }
  if ($("wmean-enabled").checked) {
    rules.push({ mode: "wmean", value: Number($("wmean-value").value),
                 surface: $("wmean-surface").value });
  }
  if ($("trend-enabled").checked) {
    rules.push({ mode: "trend", surface: $("trend-surface").value,
                 weight: Number($("trend-weight").value || 1),
                 order: Number($("trend-order").value || 10) });
  }
  return rules;
}

function appendGlobalRules(body) {
  const rules = currentGlobalRules();
  if (rules.length) body.append("global_rules", JSON.stringify(rules));
}

function refreshSurfaceOptions(surfaces) {
  const options = (surfaces || []).map((item) => ({ key: item.key, name: item.name }));
  for (const id of ["wmean-surface", "trend-surface"]) {
    const select = $(id);
    const current = select.value;
    select.innerHTML = '<option value="">surface</option>';
    for (const option of options) {
      const node = document.createElement("option");
      node.value = option.key;
      node.textContent = option.name;
      select.appendChild(node);
    }
    if ([...select.options].some((node) => node.value === current)) select.value = current;
  }
  $("surface-count").textContent = String(options.length);
  if (pendingGlobalRules) {
    applyGlobalRules(pendingGlobalRules);
    pendingGlobalRules = null;
  }
  if (pendingRuleOrder) {
    ruleOrder = pendingRuleOrder.filter((group) => RULE_LABELS[group]);
    for (const group of Object.keys(RULE_LABELS)) {
      if (!ruleOrder.includes(group)) ruleOrder.push(group);
    }
    pendingRuleOrder = null;
    renderRuleOrder();
  }
}

function applyGlobalRules(rules) {
  const byMode = new Map((rules || []).map((rule) => [rule.mode, rule]));
  const mean = byMode.get("mean");
  const wmean = byMode.get("wmean");
  const trend = byMode.get("trend");
  $("mean-enabled").checked = Boolean(mean);
  if (mean) $("mean-value").value = mean.value ?? "";
  $("wmean-enabled").checked = Boolean(wmean);
  if (wmean) {
    $("wmean-value").value = wmean.value ?? "";
    if (wmean.surface) $("wmean-surface").value = wmean.surface;
  }
  $("trend-enabled").checked = Boolean(trend);
  if (trend) {
    $("trend-weight").value = trend.weight ?? 1;
    $("trend-order").value = trend.order ?? 10;
    if (trend.surface) $("trend-surface").value = trend.surface;
  }
}

const RULE_LABELS = {
  points: "points", contours: "contours", faults: "fault lines",
  areas: "area rules", global: "mean / trend", bounds: "global bounds",
  completer: "completer",
};

function renderRuleOrder() {
  const list = $("rule-order-list");
  list.innerHTML = "";
  ruleOrder.forEach((group, index) => {
    const row = document.createElement("div");
    row.className = "rule-order-row";
    const label = document.createElement("span");
    label.textContent = RULE_LABELS[group] || group;
    const up = document.createElement("button");
    up.type = "button";
    up.textContent = "↑";
    up.disabled = index === 0;
    up.addEventListener("click", () => {
      [ruleOrder[index - 1], ruleOrder[index]] = [ruleOrder[index], ruleOrder[index - 1]];
      renderRuleOrder();
    });
    const down = document.createElement("button");
    down.type = "button";
    down.textContent = "↓";
    down.disabled = index === ruleOrder.length - 1;
    down.addEventListener("click", () => {
      [ruleOrder[index + 1], ruleOrder[index]] = [ruleOrder[index], ruleOrder[index + 1]];
      renderRuleOrder();
    });
    row.append(label, up, down);
    list.appendChild(row);
  });
}

function appendRuleOrder(body) {
  body.append("rule_order", JSON.stringify(ruleOrder));
}

function appendAreaRules(body) {
  if (areaRules.length) body.append("area_rules", JSON.stringify(areaRules));
}

function refreshAreaRules(areas) {
  const list = $("area-rule-list");
  currentAreas = areas || [];
  const previous = new Map(areaRules.map((rule) => [rule.name, rule]));
  const previousOrder = new Map(((pendingAreaRules || areaRules) || [])
    .map((rule, index) => [rule.name, index]));
  const pending = pendingAreaRules;
  pendingAreaRules = null;
  areaRules = (areas || []).map((area, index) => {
    const old = previous.get(area.name);
    const supplied = pending && pending[index] ? pending[index] : null;
    const properties = area.properties || {};
    const fallback = properties.value !== undefined
      ? { mode: "constant", value: properties.value }
      : { mode: "none" };
    return Object.assign({ name: area.name }, fallback, old || {}, supplied || {});
  });
  areaRules.sort((a, b) => {
    const left = previousOrder.has(a.name) ? previousOrder.get(a.name) : Number.MAX_SAFE_INTEGER;
    const right = previousOrder.has(b.name) ? previousOrder.get(b.name) : Number.MAX_SAFE_INTEGER;
    return left - right;
  });
  $("area-rule-count").textContent = String(areaRules.length);
  list.innerHTML = "";
  if (!areaRules.length) {
    const empty = document.createElement("span");
    empty.className = "hint";
    empty.textContent = "No areas loaded.";
    list.appendChild(empty);
    return;
  }
  areaRules.forEach((rule, index) => {
    const row = document.createElement("div");
    row.className = "area-rule";
    const title = document.createElement("b");
    title.textContent = rule.name;
    title.title = rule.name;
    row.appendChild(title);
    const controls = document.createElement("div");
    controls.className = "area-rule-controls";
    const up = document.createElement("button");
    up.type = "button";
    up.textContent = "↑";
    up.title = "move rule up";
    up.disabled = index === 0;
    up.addEventListener("click", () => {
      [areaRules[index - 1], areaRules[index]] = [areaRules[index], areaRules[index - 1]];
      refreshAreaRules(currentAreas);
    });
    const down = document.createElement("button");
    down.type = "button";
    down.textContent = "↓";
    down.title = "move rule down";
    down.disabled = index === areaRules.length - 1;
    down.addEventListener("click", () => {
      [areaRules[index + 1], areaRules[index]] = [areaRules[index], areaRules[index + 1]];
      refreshAreaRules(currentAreas);
    });
    controls.append(up, down);
    row.appendChild(controls);

    const modeField = document.createElement("label");
    modeField.textContent = "mode";
    const mode = document.createElement("select");
    for (const value of ["none", "constant", "bounds", "undef", "mean", "add"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value === "undef" ? "undef / mask" : value;
      mode.appendChild(option);
    }
    mode.value = rule.mode || "none";
    mode.addEventListener("change", () => {
      rule.mode = mode.value;
      renderAreaRuleFields(row, rule);
    });
    modeField.appendChild(mode);
    row.appendChild(modeField);

    const fields = document.createElement("div");
    fields.className = "area-rule-fields";
    row.appendChild(fields);
    renderAreaRuleFields(row, rule);
    list.appendChild(row);
  });
}

function renderAreaRuleFields(row, rule) {
  const old = row.querySelector(".area-rule-fields");
  if (!old) return;
  old.innerHTML = "";
  const add = (label, property) => {
    const wrapper = document.createElement("label");
    wrapper.textContent = label;
    const input = document.createElement("input");
    input.type = "number";
    input.step = "any";
    input.value = rule[property] ?? "";
    input.addEventListener("input", () => {
      rule[property] = input.value === "" ? null : Number(input.value);
    });
    wrapper.appendChild(input);
    old.appendChild(wrapper);
  };
  if (rule.mode === "constant" || rule.mode === "mean" || rule.mode === "add") {
    add("value", "value");
  }
  if (rule.mode === "add") add("weight", "weight");
  if (rule.mode === "bounds") {
    add("lower", "lower");
    add("upper", "upper");
  }
}

async function refreshSchema() {
  const active = activeFiles();
  if (!active.length) return;
  const seq = ++schemaSeq;
  const body = new FormData();
  for (const item of active) body.append(item.role, item.file);
  try {
    const response = await fetch("/api/schema", { method: "POST", body });
    if (seq !== schemaSeq || !response.ok) return;
    populateFieldOptions(await response.json());
  } catch (error) {
    // Preview will report the actual file error; schema is best-effort.
  }
}

function applyAutoCell() {
  const auto = $("cell_size_auto").checked;
  $("cell_size").disabled = auto;
}

function schedulePreview() {
  clearTimeout(previewTimer);
  if (!activeFiles().length) {
    sourceData = null;
    $("map-stats").textContent = "";
    drawMap(null);
    refreshPointEditor();
    refreshLineEditor();
    refreshAreaRules(data.areas || []);
    refreshSurfaceOptions(data.surfaces || []);
    return;
  }
  refreshSchema().finally(() => {
    previewTimer = setTimeout(runPreview, 300);
  });
}

async function runPreview() {
  const seq = ++previewSeq;
  $("map-title").textContent = "Previewing sources…";
  const body = new FormData();
  for (const item of activeFiles()) body.append(item.role, item.file);
  appendFieldSettings(body);
  try {
    const response = await fetch("/api/preview", { method: "POST", body });
    if (seq !== previewSeq) return;
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join("; ") : data.detail;
      sourceData = null;
      drawMap(null);
      $("map-title").textContent = "Preview failed";
      $("map-stats").textContent = detail || "Could not read the files.";
      return;
    }
    sourceData = data;
    $("map-title").textContent = "Source data";
    drawMap(data);
    refreshPointEditor();
    refreshLineEditor();
    refreshAreaRules(data.areas || []);
    refreshSurfaceOptions(data.surfaces || []);
  } catch (error) {
    if (seq !== previewSeq) return;
    sourceData = null;
    drawMap(null);
    $("map-title").textContent = "Preview failed";
    $("map-stats").textContent = String(error);
  }
}

async function refreshPointEditor() {
  const list = $("point-list");
  const rows = [];
  const active = activeFiles();
  for (const item of active) {
    if (item.role !== "points") continue;
    const suffix = item.file.name.split(".").pop().toLowerCase();
    let text;
    try {
      text = await item.file.text();
    } catch (error) {
      continue;
    }
    if (["csv", "txt", "xyz"].includes(suffix)) {
      const lines = text.split(/\r?\n/);
      for (let index = 0; index < lines.length; index += 1) {
        const line = lines[index].trim();
        if (!line || line.startsWith("#")) continue;
        const values = line.replace(/[,;]/g, " ").split(/\s+/).map(Number);
        if (values.length < 3 || values.some(Number.isNaN)) continue;
        rows.push({ item, format: "csv", lineIndex: index, x: values[0], y: values[1], z: values[2] });
      }
    } else if (["geojson", "json"].includes(suffix)) {
      try {
        const doc = JSON.parse(text);
        const features = doc.type === "FeatureCollection" ? doc.features || [] : [doc];
        for (let featureIndex = 0; featureIndex < features.length; featureIndex += 1) {
          const geometry = features[featureIndex].geometry || {};
          const coordinates = geometry.coordinates || [];
          const points = geometry.type === "Point" ? [coordinates] : geometry.type === "MultiPoint" ? coordinates : [];
          const props = features[featureIndex].properties || {};
          for (let pointIndex = 0; pointIndex < points.length; pointIndex += 1) {
            const coordinate = points[pointIndex];
            const z = coordinate.length > 2 ? coordinate[2] : props.z;
            rows.push({ item, format: "geojson", featureIndex, pointIndex,
                        multi: geometry.type === "MultiPoint", doc,
                        x: coordinate[0], y: coordinate[1], z });
          }
        }
      } catch (error) {
        rows.push({ item, format: "error", label: "invalid GeoJSON" });
      }
    } else {
      rows.push({ item, format: "opaque", label: "SHP: edit in the source file" });
    }
  }
  $("point-count").textContent = String(rows.length);
  list.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("span");
    empty.className = "hint";
    empty.textContent = "No editable point sources.";
    list.appendChild(empty);
    return;
  }
  for (const row of rows.slice(0, 200)) {
    const div = document.createElement("div");
    div.className = "point-row";
    const label = document.createElement("span");
    const coords = row.format === "csv" || row.format === "geojson"
      ? `${Number(row.x).toFixed(3)}, ${Number(row.y).toFixed(3)} · ${row.z == null ? "?" : Number(row.z).toFixed(3)}`
      : row.label;
    label.textContent = coords;
    label.title = coords;
    const source = document.createElement("span");
    source.textContent = row.item.file.name;
    source.title = row.item.file.name;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.title = "remove point";
    remove.textContent = "×";
    remove.disabled = row.format === "opaque" || row.format === "error";
    remove.addEventListener("click", () => deletePoint(row));
    div.append(label, source, remove);
    list.appendChild(div);
  }
}

async function deletePoint(row) {
  if (row.format === "csv") {
    const lines = (await row.item.file.text()).split(/\r?\n/);
    lines.splice(row.lineIndex, 1);
    row.item.file = new File([lines.join("\n")], row.item.file.name, { type: row.item.file.type || "text/plain" });
  } else if (row.format === "geojson") {
    const doc = row.doc.type === "FeatureCollection"
      ? row.doc
      : { type: "FeatureCollection", features: [row.doc] };
    if (row.multi) {
      const geometry = doc.features[row.featureIndex].geometry;
      geometry.coordinates.splice(row.pointIndex, 1);
      if (!geometry.coordinates.length) doc.features.splice(row.featureIndex, 1);
    } else {
      doc.features.splice(row.featureIndex, 1);
    }
    row.item.file = new File([JSON.stringify(doc)], row.item.file.name, { type: "application/geo+json" });
  } else {
    return;
  }
  lastJob = null;
  renderFiles();
  schedulePreview();
  await refreshPointEditor();
}

async function refreshLineEditor() {
  const list = $("line-list");
  const rows = [];
  for (const item of activeFiles()) {
    if (item.role !== "contours" && item.role !== "faults") continue;
    const suffix = item.file.name.split(".").pop().toLowerCase();
    let text;
    try {
      text = await item.file.text();
    } catch (error) {
      continue;
    }
    if (["csv", "txt", "xyz"].includes(suffix)) {
      const lines = text.split(/\r?\n/);
      const groups = new Map();
      for (let index = 0; index < lines.length; index += 1) {
        const line = lines[index].trim();
        if (!line || line.startsWith("#")) continue;
        const values = line.replace(/[,;]/g, " ").split(/\s+/).map(Number);
        if (values.length < 2 || values.some(Number.isNaN)) continue;
        const group = values.length > (item.role === "contours" ? 3 : 2)
          ? Number(values[item.role === "contours" ? 3 : 2]) : 0;
        if (!groups.has(group)) groups.set(group, []);
        groups.get(group).push(index);
      }
      for (const [group, indexes] of groups) {
        if (indexes.length >= 2) rows.push({ item, format: "csv", group, indexes,
                                             role: item.role });
      }
    } else if (["geojson", "json"].includes(suffix)) {
      try {
        const doc = JSON.parse(text);
        const features = doc.type === "FeatureCollection" ? doc.features || [] : [doc];
        for (let featureIndex = 0; featureIndex < features.length; featureIndex += 1) {
          const geometry = features[featureIndex].geometry || {};
          const parts = geometry.type === "LineString" ? [geometry.coordinates]
            : geometry.type === "MultiLineString" ? geometry.coordinates : [];
          for (let partIndex = 0; partIndex < parts.length; partIndex += 1) {
            if ((parts[partIndex] || []).length >= 2) {
              rows.push({ item, format: "geojson", doc, featureIndex, partIndex,
                          multi: geometry.type === "MultiLineString",
                          role: item.role });
            }
          }
        }
      } catch (error) {
        rows.push({ item, format: "error", label: "invalid GeoJSON" });
      }
    } else {
      rows.push({ item, format: "opaque", label: "SHP: edit in the source file" });
    }
  }
  $("line-count").textContent = String(rows.length);
  list.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("span");
    empty.className = "hint";
    empty.textContent = "No editable line sources.";
    list.appendChild(empty);
    return;
  }
  for (const row of rows.slice(0, 120)) {
    const div = document.createElement("div");
    div.className = "line-row";
    const label = document.createElement("span");
    const text = row.format === "csv"
      ? `${row.role} line ${row.group} · ${row.indexes.length} pts`
      : row.format === "geojson"
        ? `${row.role} feature ${row.featureIndex + 1}`
        : row.label;
    label.textContent = text;
    label.title = text;
    const source = document.createElement("span");
    source.textContent = row.item.file.name;
    source.title = row.item.file.name;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.title = "remove line";
    remove.textContent = "×";
    remove.disabled = row.format === "opaque" || row.format === "error";
    remove.addEventListener("click", () => deleteLine(row));
    div.append(label, source, remove);
    list.appendChild(div);
  }
}

async function deleteLine(row) {
  if (row.format === "csv") {
    const lines = (await row.item.file.text()).split(/\r?\n/);
    for (const index of [...row.indexes].sort((a, b) => b - a)) lines.splice(index, 1);
    row.item.file = new File([lines.join("\n")], row.item.file.name, { type: row.item.file.type || "text/plain" });
  } else if (row.format === "geojson") {
    const doc = row.doc.type === "FeatureCollection"
      ? row.doc
      : { type: "FeatureCollection", features: [row.doc] };
    if (row.multi) {
      const geometry = doc.features[row.featureIndex].geometry;
      geometry.coordinates.splice(row.partIndex, 1);
      if (!geometry.coordinates.length) doc.features.splice(row.featureIndex, 1);
    } else {
      doc.features.splice(row.featureIndex, 1);
    }
    row.item.file = new File([JSON.stringify(doc)], row.item.file.name, { type: "application/geo+json" });
  } else {
    return;
  }
  lastJob = null;
  renderFiles();
  schedulePreview();
  await refreshLineEditor();
}

/* ---------- 3D ---------- */
const sceneRoot = $("scene");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe7f0f5);
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 10000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(1, 1);
sceneRoot.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
scene.add(new THREE.HemisphereLight(0xffffff, 0x55707e, 1.3));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(1, 2, 1.4);
scene.add(sun);
const group = new THREE.Group();
scene.add(group);
let exaggeration = 1;

function autoExaggeration(mesh) {
  const extent = mesh.extent || {};
  let width = Number(extent.max_x) - Number(extent.min_x);
  let height = Number(extent.max_y) - Number(extent.min_y);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const [x, y] of mesh.vertices || []) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
    width = maxX - minX;
    height = maxY - minY;
  }
  const horizontal = Math.max(width, height, 1);
  const relief = Math.max(Number(mesh.zmax) - Number(mesh.zmin), 1e-9);
  const target = horizontal * 0.30;
  return Math.max(1, Math.min(5000, target / relief));
}

function formatExaggeration(value) {
  if (value >= 100) return String(Math.round(value));
  if (value >= 10) return value.toFixed(0);
  if (value >= 1) return value.toFixed(1);
  return value.toFixed(2);
}

function setExaggeration(value, moveSlider = true) {
  exaggeration = Math.max(0.01, Math.min(5000, Number(value) || 1));
  group.scale.y = exaggeration;
  $("exaggeration-value").textContent = `×${formatExaggeration(exaggeration)}`;
  if (moveSlider) {
    $("exaggeration").value = String(Math.log10(exaggeration));
  }
}

function resizeView() {
  if (!$("result-pane").classList.contains("is-hidden")) {
    const width = sceneRoot.clientWidth || 1;
    const height = sceneRoot.clientHeight || 1;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }
  drawMap(lastMesh);
}
window.addEventListener("resize", resizeView);

function colorFor(value, lo, hi) {
  const t = Math.max(0, Math.min(1, (value - lo) / (hi - lo || 1)));
  if (t < 0.33) {
    const u = t / 0.33;
    return new THREE.Color(0.15 + 0.09 * u, 0.36 + 0.17 * u, 0.51 + 0.05 * u);
  }
  if (t < 0.66) {
    const u = (t - 0.33) / 0.33;
    return new THREE.Color(0.24 + 0.4 * u, 0.53 + 0.1 * u, 0.56 - 0.15 * u);
  }
  const u = (t - 0.66) / 0.34;
  return new THREE.Color(0.64 + 0.16 * u, 0.66 - 0.25 * u, 0.41 - 0.3 * u);
}

function addSurface(mesh) {
  const positions = [];
  for (const [x, y, z] of mesh.vertices) positions.push(x, z, -y);
  const indices = [];
  for (const face of mesh.faces) indices.push(...face);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  const colors = [];
  for (const [, , z] of mesh.vertices) {
    const color = colorFor(z, mesh.zmin, mesh.zmax);
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  const surface = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.72, metalness: 0.03,
    side: THREE.DoubleSide, flatShading: false,
  }));
  surface.name = "surface";
  group.add(surface);
}

function addPoints(points, zmin, zmax) {
  const positions = [], colors = [];
  for (const [x, y, z] of points) {
    positions.push(x, z, -y);
    const c = colorFor(z, zmin, zmax);
    colors.push(c.r, c.g, c.b);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  const material = new THREE.PointsMaterial({ size: 0.16, vertexColors: true, sizeAttenuation: true });
  const dots = new THREE.Points(geometry, material);
  dots.name = "points";
  group.add(dots);
}

function addContours(contours) {
  for (const contour of contours) {
    const positions = [];
    for (const [x, y, z] of contour.points) positions.push(x, z, -y);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    group.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0x205f48 })));
  }
}

function attachFaultsToSurface(mesh) {
  const vertices = mesh.vertices;
  if (!vertices.length) return;
  const stepX = mesh.extent?.step_x || 1;
  const stepY = mesh.extent?.step_y || 1;
  let minX = Infinity, minY = Infinity;
  for (const vertex of vertices) {
    if (vertex[0] < minX) minX = vertex[0];
    if (vertex[1] < minY) minY = vertex[1];
  }
  const grid = new Map();
  for (const v of vertices) {
    grid.set(`${Math.round((v[0] - minX) / stepX)}:${Math.round((v[1] - minY) / stepY)}`, v[2]);
  }
  for (const fault of mesh.faults) {
    const positions = [];
    for (const [x, y] of fault.points) {
      const key = `${Math.round((x - minX) / stepX)}:${Math.round((y - minY) / stepY)}`;
      positions.push(x, grid.get(key) ?? mesh.zmin, -y);
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    group.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0xb52d1e })));
  }
}

function clearGroup() {
  while (group.children.length) {
    const child = group.children.pop();
    child.geometry?.dispose?.();
    child.material?.dispose?.();
  }
}

function fitView() {
  const box = new THREE.Box3().setFromObject(group);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(1.1, 0.7, 1.3).multiplyScalar(size * 0.9));
  camera.near = Math.max(size * 1e-5, 1e-4);
  camera.far = Math.max(size * 20, 1000);
  camera.updateProjectionMatrix();
  controls.minDistance = Math.max(size * 0.01, 1e-3);
  controls.maxDistance = size * 10;
  camera.lookAt(center);
  controls.update();
}

/* ---------- 2D source map ---------- */
function sourceBounds(mesh) {
  const xs = [], ys = [];
  for (const point of mesh.points || []) { xs.push(point[0]); ys.push(point[1]); }
  for (const contour of mesh.contours || []) for (const point of contour.points) { xs.push(point[0]); ys.push(point[1]); }
  for (const fault of mesh.faults || []) for (const point of fault.points) { xs.push(point[0]); ys.push(point[1]); }
  for (const area of mesh.areas || []) for (const point of area.points) { xs.push(point[0]); ys.push(point[1]); }
  if (!xs.length) return null;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const value of xs) { if (value < minX) minX = value; if (value > maxX) maxX = value; }
  for (const value of ys) { if (value < minY) minY = value; if (value > maxY) maxY = value; }
  return { minX, maxX, minY, maxY };
}

function drawMap(sources) {
  const canvas = $("map");
  if (!canvas) return;
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const width = canvas.clientWidth, height = canvas.clientHeight;
  if (!width || !height) return;
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#e7f0f5";
  ctx.fillRect(0, 0, width, height);

  const data = sources || sourceData;
  const bounds = data ? sourceBounds(data) : null;
  $("map-empty").style.display = bounds ? "none" : "flex";
  $("map-stats").textContent = data
    ? `${data.points.length} points · ${data.contours.length} contours · ${data.faults.length} faults · ${(data.areas || []).length} areas · ${(data.surfaces || []).length} surfaces`
    : files.map((item) => `${item.role}: ${item.file.name}`).join(" · ");
  if (!bounds) return;

  const pad = 46;
  const spanX = Math.max(bounds.maxX - bounds.minX, 1e-9);
  const spanY = Math.max(bounds.maxY - bounds.minY, 1e-9);
  const scale = Math.min((width - pad * 2) / spanX, (height - pad * 2) / spanY);
  const tx = (x) => pad + (x - bounds.minX) * scale + ((width - pad * 2) - spanX * scale) / 2;
  const ty = (y) => height - pad - (y - bounds.minY) * scale - ((height - pad * 2) - spanY * scale) / 2;

  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, width, height);
  ctx.clip();
  ctx.translate(mapView.x, mapView.y);
  ctx.scale(mapView.zoom, mapView.zoom);

  ctx.strokeStyle = "#d2e1e8";
  ctx.lineWidth = 1 / mapView.zoom;
  for (let i = 0; i <= 6; i += 1) {
    const x = pad + i * (width - pad * 2) / 6;
    const y = pad + i * (height - pad * 2) / 6;
    ctx.beginPath(); ctx.moveTo(x, pad); ctx.lineTo(x, height - pad); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(width - pad, y); ctx.stroke();
  }
  ctx.strokeStyle = "#9eb5c1";
  ctx.lineWidth = 1 / mapView.zoom;
  ctx.strokeRect(pad, pad, width - pad * 2, height - pad * 2);

  for (const area of data.areas || []) {
    ctx.beginPath();
    area.points.forEach(([x, y], index) => {
      if (index === 0) ctx.moveTo(tx(x), ty(y)); else ctx.lineTo(tx(x), ty(y));
    });
    ctx.closePath();
    ctx.fillStyle = "rgba(180, 71, 47, 0.12)";
    ctx.fill();
    ctx.strokeStyle = "#b4472f";
    ctx.lineWidth = 1.5 / mapView.zoom;
    ctx.stroke();
  }

  if ($("map-surface").checked && data === lastMesh && data.faces?.length) {
    ctx.save();
    ctx.globalAlpha = 0.38;
    const stride = Math.max(1, Math.ceil(data.faces.length / 30000));
    for (let index = 0; index < data.faces.length; index += stride) {
      const face = data.faces[index];
      const points = face.map((vertexIndex) => data.vertices[vertexIndex]);
      if (points.some((point) => !point)) continue;
      const z = (points[0][2] + points[1][2] + points[2][2]) / 3;
      const color = colorFor(z, data.zmin, data.zmax);
      ctx.fillStyle = `rgb(${Math.round(color.r * 255)},${Math.round(color.g * 255)},${Math.round(color.b * 255)})`;
      ctx.beginPath();
      points.forEach(([x, y], pointIndex) => {
        if (pointIndex === 0) ctx.moveTo(tx(x), ty(y)); else ctx.lineTo(tx(x), ty(y));
      });
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  if (sectionEndpoints && data === lastMesh) {
    ctx.beginPath();
    ctx.moveTo(tx(sectionEndpoints[0]), ty(sectionEndpoints[1]));
    ctx.lineTo(tx(sectionEndpoints[2]), ty(sectionEndpoints[3]));
    ctx.strokeStyle = "#1b6388";
    ctx.lineWidth = 1.8 / mapView.zoom;
    ctx.setLineDash([6 / mapView.zoom, 5 / mapView.zoom]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  for (const contour of data.contours || []) {
    ctx.beginPath();
    contour.points.forEach(([x, y], index) => {
      if (index === 0) ctx.moveTo(tx(x), ty(y)); else ctx.lineTo(tx(x), ty(y));
    });
    ctx.strokeStyle = "#24634c";
    ctx.lineWidth = 2 / mapView.zoom;
    ctx.stroke();
  }
  for (const fault of data.faults || []) {
    ctx.beginPath();
    fault.points.forEach(([x, y], index) => {
      if (index === 0) ctx.moveTo(tx(x), ty(y)); else ctx.lineTo(tx(x), ty(y));
    });
    ctx.strokeStyle = "#b4472f";
    ctx.lineWidth = 2.5 / mapView.zoom;
    ctx.stroke();
  }
  ctx.fillStyle = "#132733";
  for (const [x, y] of data.points || []) {
    ctx.beginPath();
    ctx.arc(tx(x), ty(y), 3 / mapView.zoom, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
  ctx.fillStyle = "#607987";
  ctx.font = "11px sans-serif";
  ctx.fillText(`x: ${bounds.minX.toFixed(2)} … ${bounds.maxX.toFixed(2)}`, pad + 6, height - pad - 8);
  ctx.textAlign = "right";
  ctx.fillText(`y: ${bounds.minY.toFixed(2)} … ${bounds.maxY.toFixed(2)}`, width - pad - 6, height - pad - 8);
  ctx.textAlign = "left";
}

function setupSection(mesh) {
  if (!mesh.extent) return;
  const e = mesh.extent;
  const midY = e.min_y + e.step_y * (mesh.shape[0] - 1) / 2;
  $("sec-x0").value = e.min_x.toFixed(3);
  $("sec-y0").value = midY.toFixed(3);
  $("sec-x1").value = (e.min_x + e.step_x * (mesh.shape[1] - 1)).toFixed(3);
  $("sec-y1").value = midY.toFixed(3);
}

function sectionProfile(mesh, x0, y0, x1, y1, count = 180) {
  const e = mesh.extent;
  if (!e) return null;
  const stepX = e.step_x || 1, stepY = e.step_y || 1;
  const minX = e.min_x, minY = e.min_y;
  const zmap = new Map();
  for (const v of mesh.vertices) {
    zmap.set(`${Math.round((v[0] - minX) / stepX)}:${Math.round((v[1] - minY) / stepY)}`, v[2]);
  }
  const values = [];
  const distances = [];
  const length = Math.hypot(x1 - x0, y1 - y0);
  for (let i = 0; i < count; i += 1) {
    const t = i / (count - 1);
    const x = x0 + (x1 - x0) * t;
    const y = y0 + (y1 - y0) * t;
    let z = null;
    const baseX = Math.round((x - minX) / stepX);
    const baseY = Math.round((y - minY) / stepY);
    for (const [dx, dy] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]]) {
      const value = zmap.get(`${baseX + dx}:${baseY + dy}`);
      if (value !== undefined) { z = value; break; }
    }
    if (z !== null) { values.push(z); distances.push(length * t); }
  }
  return values.length ? { values, distances, length } : null;
}

function drawSection() {
  const mesh = lastMesh;
  if (!mesh) return;
  const coords = ["sec-x0", "sec-y0", "sec-x1", "sec-y1"].map((id) => Number($(id).value));
  if (coords.some((value) => !Number.isFinite(value))) {
    $("section-note").textContent = "Enter four finite coordinates.";
    return;
  }
  const profile = sectionProfile(mesh, coords[0], coords[1], coords[2], coords[3]);
  if (!profile) {
    $("section-note").textContent = "No defined surface along this line.";
    return;
  }
  sectionEndpoints = coords;
  lastSection = { a: coords.slice(0, 2), b: coords.slice(2, 4),
                  profile: { values: profile.values, distances: profile.distances,
                             length: profile.length } };
  drawMap(mesh);
  const canvas = $("section-canvas");
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const width = canvas.clientWidth || 280, height = 120;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const pad = 12;
  const zmin = Math.min(...profile.values), zmax = Math.max(...profile.values);
  const sx = (d) => pad + d / (profile.length || 1) * (width - pad * 2);
  const sy = (z) => height - pad - (z - zmin) / (zmax - zmin || 1) * (height - pad * 2);
  ctx.beginPath();
  profile.values.forEach((z, index) => {
    const x = sx(profile.distances[index]), y = sy(z);
    if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.lineTo(sx(profile.distances[profile.distances.length - 1]), height - pad);
  ctx.lineTo(sx(profile.distances[0]), height - pad);
  ctx.closePath();
  ctx.fillStyle = "#cfe2ea";
  ctx.fill();
  ctx.beginPath();
  profile.values.forEach((z, index) => {
    const x = sx(profile.distances[index]), y = sy(z);
    if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#1b6388";
  ctx.lineWidth = 2;
  ctx.stroke();
  $("section-note").textContent = `${profile.values.length} samples · z ${zmin.toFixed(2)} … ${zmax.toFixed(2)} · length ${profile.length.toFixed(2)}`;
}

function clampMapView() {
  const canvas = $("map");
  const width = canvas?.clientWidth || 0;
  const height = canvas?.clientHeight || 0;
  if (mapView.zoom <= 1) {
    // Keep a zoomed-out map centred instead of pinned to the top-left.
    mapView.x = (width - width * mapView.zoom) / 2;
    mapView.y = (height - height * mapView.zoom) / 2;
    return;
  }
  const minX = width - width * mapView.zoom;
  const minY = height - height * mapView.zoom;
  mapView.x = Math.max(minX, Math.min(0, mapView.x));
  mapView.y = Math.max(minY, Math.min(0, mapView.y));
}

function scheduleMapDraw() {
  if (mapDrawFrame) return;
  mapDrawFrame = requestAnimationFrame(() => {
    mapDrawFrame = 0;
    drawMap(lastMesh || sourceData);
  });
}

function applyMapView() {
  const canvas = $("map");
  if (!canvas) return;
  clampMapView();
  canvas.dataset.zoom = String(mapView.zoom);
  canvas.dataset.pan = `${mapView.x},${mapView.y}`;
  scheduleMapDraw();
}

function setMapZoom(next, anchorX, anchorY) {
  const canvas = $("map");
  const oldZoom = mapView.zoom;
  const newZoom = Math.max(0.25, Math.min(6, next));
  const width = canvas?.clientWidth || 0;
  const height = canvas?.clientHeight || 0;
  const ax = anchorX == null ? width / 2 : anchorX;
  const ay = anchorY == null ? height / 2 : anchorY;
  const worldX = (ax - mapView.x) / oldZoom;
  const worldY = (ay - mapView.y) / oldZoom;
  mapView.zoom = newZoom;
  mapView.x = ax - worldX * newZoom;
  mapView.y = ay - worldY * newZoom;
  applyMapView();
}

function resetMapView() {
  mapView.zoom = 1;
  mapView.x = 0;
  mapView.y = 0;
  applyMapView();
}

$("cell_size_auto").addEventListener("change", applyAutoCell);
for (const key of ["x_field", "y_field", "z_field", "weight_field", "exclude_zero"]) {
  $(key).addEventListener("change", schedulePreview);
}
for (const key of ["min_value", "max_value"]) {
  $(key).addEventListener("input", schedulePreview);
}
$("map-zoom-in").addEventListener("click", () => setMapZoom(mapView.zoom * 1.35));
$("map-zoom-out").addEventListener("click", () => setMapZoom(mapView.zoom / 1.35));
$("map-reset").addEventListener("click", resetMapView);

let mapDrag = null;
$("map").addEventListener("pointerdown", (event) => {
  if (mapView.zoom <= 1) return;
  mapDrag = { startX: event.clientX, startY: event.clientY,
              originX: mapView.x, originY: mapView.y };
  $("map").setPointerCapture(event.pointerId);
});
$("map").addEventListener("pointermove", (event) => {
  if (!mapDrag) return;
  mapView.x = mapDrag.originX + event.clientX - mapDrag.startX;
  mapView.y = mapDrag.originY + event.clientY - mapDrag.startY;
  applyMapView();
});
$("map").addEventListener("pointerup", () => { mapDrag = null; });
$("map").addEventListener("pointercancel", () => { mapDrag = null; });
$("map").addEventListener("wheel", (event) => {
  event.preventDefault();
  const host = $("map-pane").getBoundingClientRect();
  setMapZoom(mapView.zoom * (event.deltaY < 0 ? 1.12 : 1 / 1.12),
             event.clientX - host.left, event.clientY - host.top);
}, { passive: false });

/* ---------- results ---------- */
function setQuality(metrics) {
  const quality = $("quality");
  quality.innerHTML = "";
  const report = metrics.rule_report || {};
  const rules = report.rules || [];
  const note = document.createElement("span");
  note.textContent = `${rules.length} rule${rules.length === 1 ? "" : "s"} · tol ${metrics.tol ?? "–"} · ${metrics.solver ?? "–"}`;
  quality.appendChild(note);
  for (const rule of rules) {
    const item = document.createElement("div");
    item.className = "rule";
    const name = document.createElement("b");
    name.textContent = rule.name;
    name.title = rule.name;
    const values = document.createElement("div");
    const residual = rule.residual === null || rule.residual === undefined
      ? "no residual"
      : `residual ${Number(rule.residual).toExponential(2)}`;
    const penalty = `penalty ${rule.penalty_iterations ?? 0}`;
    const violations = rule.violations > 0 ? `violations ${rule.violations}` : "no violations";
    for (const text of [residual, penalty, violations]) {
      const span = document.createElement("span");
      span.textContent = text;
      if (text.startsWith("violations")) span.className = "bad";
      values.appendChild(span);
    }
    item.append(name, values);
    quality.appendChild(item);
  }
}

function setMetrics(data) {
  const m = data.metrics || {};
  lastMetrics = m;
  if (m.auto_cell && m.cell_size) $("cell_size").value = Number(m.cell_size).toPrecision(4);
  setQuality(m);
  $("metrics").innerHTML = [
    ["points", m.points], ["contours", m.contours], ["faults", m.faults],
    ["areas", m.areas], ["grid", m.grid ? `${m.grid[0]} × ${m.grid[1]}` : "–"],
    ["defined", m.defined], ["undefined", m.undefined],
  ].map(([key, value]) => `<div class="metric"><span>${key}</span><b>${value ?? "–"}</b></div>`).join("");
  $("downloads").innerHTML = [
    data.downloads.dat ? `<a href="${data.downloads.dat}">download .dat</a>` : "",
    data.downloads.gltf ? `<a href="${data.downloads.gltf}">download glTF</a>` : "",
  ].join("");
}

function renderResult(data, mesh) {
  lastMesh = mesh;
  sourceData = mesh;
  setMetrics(data);
  clearGroup();
  addSurface(mesh);
  addPoints(mesh.points, mesh.zmin, mesh.zmax);
  addContours(mesh.contours || []);
  attachFaultsToSurface(mesh);
  setExaggeration(autoExaggeration(mesh));
  $("hud-title").textContent = `${mesh.shape[0]} × ${mesh.shape[1]} grid`;
  $("zmin").textContent = mesh.zmin.toFixed(2);
  $("zmax").textContent = mesh.zmax.toFixed(2);
  sectionEndpoints = null;
  lastSection = null;
  setupSection(mesh);
  drawMap(mesh);
  $("result-badge").hidden = false;
  showTab("result");
  resizeView();
  fitView();
}

async function poll(id) {
  const response = await fetch(`/api/jobs/${id}`);
  const data = await response.json();
  if (data.status === "error") {
    statusBox.textContent = data.error;
    statusBox.className = "status error";
    $("solve").disabled = false;
    return;
  }
  if (data.status !== "done") {
    statusBox.textContent = data.status === "running" ? "Solving…" : "Queued…";
    setTimeout(() => poll(id), 600);
    return;
  }
  statusBox.textContent = "Rendering…";
  statusBox.className = "status";
  lastJob = data;
  const mesh = await (await fetch(`/api/jobs/${id}/mesh`)).json();
  renderResult(data, mesh);
  statusBox.textContent = "Done.";
  $("solve").disabled = false;
}

function projectBody() {
  const body = new FormData();
  for (const item of activeFiles()) body.append(item.role, item.file);
  appendFieldSettings(body);
  appendAreaRules(body);
  appendGlobalRules(body);
  appendRuleOrder(body);
  body.append("name", $("project_name").value.trim() || "Untitled");
  for (const key of ["cell_size", "tol", "d1", "d2", "solver"]) body.append(key, $(key).value);
  if ($("cell_size_auto").checked) body.append("cell_size_auto", "true");
  for (const key of ["lower", "upper", "min_x", "max_x", "min_y", "max_y"]) {
    if ($(key).value !== "") body.append(key, $(key).value);
  }
  if (lastJob?.id) body.append("job_id", lastJob.id);
  return body;
}

async function refreshProjects() {
  const list = $("project-list");
  try {
    const data = await (await fetch("/api/projects")).json();
    list.innerHTML = "";
    if (!data.projects.length) {
      list.innerHTML = '<span class="hint">No saved projects yet.</span>';
      return;
    }
    for (const project of data.projects) {
      const row = document.createElement("div");
      row.className = "project-row";
      const open = document.createElement("button");
      open.type = "button";
      open.className = "project-open";
      const date = new Date((project.updated || 0) * 1000).toLocaleString();
      const strong = document.createElement("strong");
      strong.textContent = project.name;
      const small = document.createElement("small");
      small.textContent = date + (project.has_result ? " · result" : "");
      open.append(strong, small);
      open.addEventListener("click", () => loadProject(project.id));
      const exportLink = document.createElement("a");
      exportLink.className = "project-export";
      exportLink.href = `/api/projects/${project.id}/archive`;
      exportLink.title = "export project";
      exportLink.textContent = "↓";
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "project-delete";
      remove.title = "delete project";
      remove.textContent = "×";
      remove.addEventListener("click", async () => {
        await fetch(`/api/projects/${project.id}`, { method: "DELETE" });
        refreshProjects();
      });
      row.append(open, exportLink, remove);
      list.appendChild(row);
    }
  } catch (error) {
    list.innerHTML = `<span class="hint">Could not load projects: ${error}</span>`;
  }
}

async function saveProject() {
  if (!activeFiles().length) {
    statusBox.textContent = "Enable at least one source file before saving.";
    statusBox.className = "status error";
    return;
  }
  statusBox.textContent = "Saving project…";
  statusBox.className = "status";
  const response = await fetch("/api/projects", { method: "POST", body: projectBody() });
  if (!response.ok) {
    const error = await response.json();
    statusBox.textContent = error.detail || "Could not save project";
    statusBox.className = "status error";
    return;
  }
  const project = await response.json();
  $("project_name").value = project.name;
  statusBox.textContent = project.has_result ? "Project saved with result." : "Project saved.";
  await refreshProjects();
}

async function loadProject(id) {
  statusBox.textContent = "Loading project…";
  statusBox.className = "status";
  const meta = await (await fetch(`/api/projects/${id}`)).json();
  files.length = 0;
  fileSeq = 0;
  for (const source of meta.sources) {
    const response = await fetch(source.url);
    if (!response.ok) throw new Error(`source ${source.name} failed`);
    const blob = await response.blob();
    files.push({ id: ++fileSeq, role: source.role, enabled: true,
                 file: new File([blob], source.name.split("/").pop()) });
  }
  $("project_name").value = meta.name;
  $("cell_size_auto").checked = Boolean(meta.settings.cell_size_auto);
  for (const key of ["cell_size", "tol", "lower", "upper", "d1", "d2", "solver",
                     "min_x", "max_x", "min_y", "max_y"]) {
    const value = meta.settings[key];
    if (value !== null && value !== undefined) $(key).value = value;
  }
  for (const key of ["x_field", "y_field", "z_field", "weight_field"]) {
    setFieldValue(key, meta.settings[key] || "");
  }
  for (const key of ["min_value", "max_value"]) {
    const value = meta.settings[key];
    $(key).value = value === null || value === undefined ? "" : value;
  }
  $("exclude_zero").checked = Boolean(meta.settings.exclude_zero);
  pendingAreaRules = meta.settings.area_rules || null;
  pendingGlobalRules = meta.settings.global_rules || null;
  pendingRuleOrder = meta.settings.rule_order || null;
  applyAutoCell();
  renderFiles();
  schedulePreview();
  lastJob = null;
  if (meta.has_result && meta.downloads.mesh) {
    const [mesh, metrics] = await Promise.all([
      fetch(meta.downloads.mesh).then((response) => response.json()),
      fetch(`/api/projects/${id}/metrics`).then((response) => response.json()),
    ]);
    renderResult({ metrics, downloads: meta.downloads }, mesh);
    statusBox.textContent = `Loaded “${meta.name}” with result.`;
  } else {
    showTab("map");
    statusBox.textContent = `Loaded “${meta.name}”. Solve to get a surface.`;
  }
  statusBox.className = "status";
  await refreshProjects();
}

$("save-project").addEventListener("click", saveProject);

function downloadReport() {
  const settings = {};
  for (const key of ["cell_size", "tol", "solver", "d1", "d2", "lower", "upper",
                     "min_x", "max_x", "min_y", "max_y",
                     "x_field", "y_field", "z_field", "weight_field",
                     "min_value", "max_value"]) {
    const value = $(key).value;
    settings[key] = value === "" ? null : (key === "solver" ? value : Number(value));
  }
  settings.exclude_zero = $("exclude_zero").checked;
  settings.cell_size_auto = $("cell_size_auto").checked;
  settings.area_rules = areaRules;
  settings.global_rules = currentGlobalRules();
  settings.rule_order = ruleOrder;
  const report = {
    format: "surfit-workbench-report",
    version: 1,
    created: new Date().toISOString(),
    project: $("project_name").value.trim() || "Untitled",
    settings,
    sources: files.map((item) => ({ name: item.file.name, role: item.role, enabled: item.enabled })),
    metrics: lastMetrics,
    section: lastSection,
  };
  const blob = new Blob([JSON.stringify(report, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "surfit-report.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

$("import-project").addEventListener("click", () => $("project-archive").click());
$("project-archive").addEventListener("change", async (event) => {
  const archive = event.target.files[0];
  if (!archive) return;
  statusBox.textContent = "Importing project…";
  statusBox.className = "status";
  const body = new FormData();
  body.append("archive", archive);
  const response = await fetch("/api/projects/import", { method: "POST", body });
  if (!response.ok) {
    const error = await response.json();
    statusBox.textContent = error.detail || "Could not import project";
    statusBox.className = "status error";
  } else {
    const project = await response.json();
    statusBox.textContent = `Imported “${project.name}”.`;
    await refreshProjects();
    await loadProject(project.id);
  }
  event.target.value = "";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeFiles().length) {
    statusBox.textContent = "Enable at least one points or contours file.";
    statusBox.className = "status error";
    return;
  }
  $("solve").disabled = true;
  statusBox.textContent = "Uploading…";
  statusBox.className = "status";
  const body = new FormData();
  for (const item of activeFiles()) body.append(item.role, item.file);
  appendFieldSettings(body);
  appendAreaRules(body);
  appendGlobalRules(body);
  appendRuleOrder(body);
  for (const key of ["cell_size", "tol", "d1", "d2", "solver"]) body.append(key, $(key).value);
  if ($("cell_size_auto").checked) body.append("cell_size_auto", "true");
  for (const key of ["lower", "upper", "min_x", "max_x", "min_y", "max_y"]) {
    if ($(key).value !== "") body.append(key, $(key).value);
  }
  const response = await fetch("/api/jobs", { method: "POST", body });
  if (!response.ok) {
    const error = await response.json();
    const detail = Array.isArray(error.detail)
      ? error.detail.map((item) => item.msg).join("; ")
      : error.detail;
    statusBox.textContent = detail || "Upload failed";
    statusBox.className = "status error";
    $("solve").disabled = false;
    return;
  }
  poll((await response.json()).id);
});

$("draw-section").addEventListener("click", drawSection);
$("map-surface").addEventListener("change", () => drawMap(lastMesh));
$("download-report").addEventListener("click", downloadReport);

function fullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement || null;
}

function updateFullscreenButton() {
  const active = fullscreenElement() === $("result-pane");
  const button = $("fullscreen");
  button.textContent = active ? "Exit fullscreen" : "Fullscreen";
  button.setAttribute("aria-pressed", String(active));
}

async function toggleFullscreen() {
  const pane = $("result-pane");
  try {
    if (fullscreenElement()) {
      const exit = document.exitFullscreen || document.webkitExitFullscreen;
      if (exit) await exit.call(document);
    } else {
      const request = pane.requestFullscreen || pane.webkitRequestFullscreen;
      if (request) await request.call(pane);
    }
  } catch (error) {
    console.warn("fullscreen unavailable", error);
  }
  updateFullscreenButton();
  requestAnimationFrame(resizeView);
}

$("fullscreen").addEventListener("click", toggleFullscreen);
document.addEventListener("fullscreenchange", () => {
  updateFullscreenButton();
  requestAnimationFrame(resizeView);
});
document.addEventListener("webkitfullscreenchange", () => {
  updateFullscreenButton();
  requestAnimationFrame(resizeView);
});

if (!document.fullscreenEnabled && !document.webkitFullscreenEnabled) {
  $("fullscreen").hidden = true;
}

$("exaggeration").addEventListener("input", (event) => {
  setExaggeration(10 ** Number(event.target.value), false);
});
$("exaggeration-auto").addEventListener("click", () => {
  if (!lastMesh) return;
  setExaggeration(autoExaggeration(lastMesh));
  fitView();
});
$("reset").addEventListener("click", fitView);

renderer.setAnimationLoop(() => {
  controls.update();
  if (!$("result-pane").classList.contains("is-hidden")) renderer.render(scene, camera);
});
renderFiles();
refreshProjects();
renderRuleOrder();
applyAutoCell();
resizeView();
