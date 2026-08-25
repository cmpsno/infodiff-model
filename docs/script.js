/* Information Diffusion — playback engine for precomputed diffusion runs
 * on Zachary's Karate Club. All simulation is done ahead of
 * time in Python (model/generate_simulation.py); this file only renders
 * the network once and steps through the recorded activation frames. */

(async function () {
  const NETWORK_W = 820;
  const NETWORK_H = 620;
  const FACTION_SIZE = 17; // both real-world factions happen to be 17/17

  const data = await d3.json("simulation.json");
  const { graph, scenarios } = data;
  const scenarioKeys = Object.keys(scenarios);
  const modelDefinitions = data.models || {
    [data.model]: {
      name: data.model.replaceAll("_", " "),
      short_name: data.model,
      parameter: data.p === undefined ? "" : `p = ${data.p}`,
      description: "A precomputed information-diffusion model.",
    },
  };
  const modelKeys = Object.keys(modelDefinitions);

  // ---- state ----------------------------------------------------------
  let currentModel = modelKeys[0];
  let currentKey =
    scenarioKeys.find((key) => (scenarios[key].model || data.model) === currentModel) ||
    scenarioKeys[0];
  let stepIndex = 0; // 0 = seed step
  let activeSet = new Set();
  let playing = false;
  let timer = null;
  let crossedFractureAt = null;

  // ---- DOM refs ---------------------------------------------------------
  const el = {
    modelSelect: document.getElementById("model-select"),
    scenarioSelect: document.getElementById("scenario-select"),
    play: document.getElementById("play-btn"),
    step: document.getElementById("step-btn"),
    reset: document.getElementById("reset-btn"),
    speed: document.getElementById("speed-range"),
    stepNum: document.getElementById("step-num"),
    stepOf: document.getElementById("step-of"),
    barHi: document.getElementById("bar-hi"),
    barOfficer: document.getElementById("bar-officer"),
    countHi: document.getElementById("count-hi"),
    countOfficer: document.getElementById("count-officer"),
    story: document.getElementById("story-line"),
    eyebrowModel: document.getElementById("eyebrow-model"),
    modelTitle: document.getElementById("model-title"),
    modelDescription: document.getElementById("model-description"),
    modelDetail: document.getElementById("model-detail"),
    footerModel: document.getElementById("footer-model"),
  };

  function scenarioModel(key) {
    return scenarios[key].model || data.model;
  }

  function setOptions(select, entries) {
    select.replaceChildren(
      ...entries.map(([value, label]) => new Option(label, value))
    );
  }

  setOptions(
    el.modelSelect,
    modelKeys.map((key) => [key, modelDefinitions[key].name])
  );

  function refreshScenarioOptions() {
    const matchingKeys = scenarioKeys.filter(
      (key) => scenarioModel(key) === currentModel
    );
    setOptions(
      el.scenarioSelect,
      matchingKeys.map((key) => [key, scenarios[key].name])
    );
    return matchingKeys;
  }

  // ---- network layout (drawn once, reused across scenarios) -----------
  const svg = d3.select("#network").attr("viewBox", `0 0 ${NETWORK_W} ${NETWORK_H}`);
  const linkLayer = svg.append("g").attr("class", "links");
  const nodeLayer = svg.append("g").attr("class", "nodes");

  const nodesById = new Map(graph.nodes.map((n) => [n.id, { ...n }]));
  const links = graph.links.map((l) => ({ source: l.source, target: l.target }));

  const sim = d3
    .forceSimulation(Array.from(nodesById.values()))
    .force(
      "link",
      d3.forceLink(links).id((d) => d.id).distance(58).strength(0.5)
    )
    .force("charge", d3.forceManyBody().strength(-190))
    .force("center", d3.forceCenter(NETWORK_W / 2, NETWORK_H / 2))
    .force("collision", d3.forceCollide(20))
    .stop();

  for (let i = 0; i < 340; i++) sim.tick(); // settle synchronously, no flash of motion

  const linkSel = linkLayer
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("class", "link")
    .attr("x1", (d) => d.source.x)
    .attr("y1", (d) => d.source.y)
    .attr("x2", (d) => d.target.x)
    .attr("y2", (d) => d.target.y);

  const nodeSel = nodeLayer
    .selectAll("g.node")
    .data(Array.from(nodesById.values()))
    .join("g")
    .attr("class", "node")
    .attr("transform", (d) => `translate(${d.x},${d.y})`);

  nodeSel
    .append("circle")
    .attr("class", (d) => `ring faction-${d.faction === "Hi" ? "hi" : "officer"}`)
    .attr("r", 12);

  nodeSel.append("circle").attr("class", "fill").attr("r", 8);

  nodeSel
    .append("text")
    .attr("dy", 22)
    .text((d) => d.id);

  // ---- mini cumulative-reach chart --------------------------------------
  const CW = 260,
    CH = 110,
    CM = { top: 8, right: 10, bottom: 18, left: 24 };
  const chartSvg = d3.select("#chart").attr("viewBox", `0 0 ${CW} ${CH}`);
  const chartG = chartSvg.append("g");
  const xScale = d3.scaleLinear().range([CM.left, CW - CM.right]);
  const yScale = d3
    .scaleLinear()
    .domain([0, graph.nodes.length])
    .range([CH - CM.bottom, CM.top]);

  const axisG = chartG.append("g").attr("class", "chart-axis");
  const areaPath = chartG
    .append("path")
    .attr("fill", "var(--gold-soft)")
    .attr("stroke", "none");
  const linePath = chartG
    .append("path")
    .attr("fill", "none")
    .attr("stroke", "var(--gold)")
    .attr("stroke-width", 1.6);
  const marker = chartG
    .append("circle")
    .attr("r", 3.2)
    .attr("fill", "var(--ink)");

  function renderChart(scenario) {
    const series = scenario.cumulative_reach; // length = steps.length
    xScale.domain([0, Math.max(1, series.length - 1)]);

    const line = d3
      .line()
      .x((_, i) => xScale(i))
      .y((v) => yScale(v));
    const area = d3
      .area()
      .x((_, i) => xScale(i))
      .y0(yScale(0))
      .y1((v) => yScale(v));

    linePath.attr("d", line(series));
    areaPath.attr("d", area(series));

    axisG.selectAll("*").remove();
    axisG
      .append("line")
      .attr("x1", CM.left)
      .attr("x2", CW - CM.right)
      .attr("y1", CH - CM.bottom)
      .attr("y2", CH - CM.bottom)
      .attr("stroke", "var(--line)");
    axisG
      .append("text")
      .attr("x", CM.left)
      .attr("y", CH - 4)
      .attr("font-family", "var(--font-mono)")
      .attr("font-size", 9)
      .attr("fill", "var(--muted)")
      .text("step 0");
    axisG
      .append("text")
      .attr("x", CW - CM.right)
      .attr("y", CH - 4)
      .attr("text-anchor", "end")
      .attr("font-family", "var(--font-mono)")
      .attr("font-size", 9)
      .attr("fill", "var(--muted)")
      .text(`step ${series.length - 1}`);
  }

  function updateChartMarker(scenario) {
    const series = scenario.cumulative_reach;
    const v = series[stepIndex];
    marker.attr("cx", xScale(stepIndex)).attr("cy", yScale(v));
  }

  // ---- playback core ----------------------------------------------------
  function scenario() {
    return scenarios[currentKey];
  }

  function totalSteps() {
    return scenario().steps.length - 1;
  }

  function recomputeActiveSet() {
    activeSet = new Set();
    for (let i = 0; i <= stepIndex; i++) {
      scenario().steps[i].forEach((id) => activeSet.add(id));
    }
  }

  function render() {
    const s = scenario();
    recomputeActiveSet();

    nodeSel.select("circle.fill").classed("active", (d) => activeSet.has(d.id));
    nodeSel
      .select("circle.ring")
      .classed("seed", (d) => s.seeds.includes(d.id));

    linkSel.classed(
      "pulsed",
      (d) => activeSet.has(d.source.id) && activeSet.has(d.target.id)
    );

    let hiCount = 0,
      officerCount = 0;
    activeSet.forEach((id) => {
      if (nodesById.get(id).faction === "Hi") hiCount++;
      else officerCount++;
    });

    el.stepNum.textContent = stepIndex;
    el.stepOf.textContent = `/ ${totalSteps()}`;
    el.barHi.style.width = `${(hiCount / FACTION_SIZE) * 100}%`;
    el.barOfficer.style.width = `${(officerCount / FACTION_SIZE) * 100}%`;
    el.countHi.textContent = `${hiCount}/${FACTION_SIZE}`;
    el.countOfficer.textContent = `${officerCount}/${FACTION_SIZE}`;

    if (crossedFractureAt === null && hiCount > 0 && officerCount > 0) {
      crossedFractureAt = stepIndex;
    }
    el.story.textContent =
      crossedFractureAt !== null && crossedFractureAt <= stepIndex
        ? `${s.story} It reached both factions by step ${crossedFractureAt}.`
        : s.story;

    updateChartMarker(s);
    el.play.textContent = playing ? "Pause" : "Play";
    el.step.disabled = stepIndex >= totalSteps();
  }

  function goToStep(i) {
    stepIndex = Math.max(0, Math.min(i, totalSteps()));
    render();
    if (stepIndex >= totalSteps()) stopPlaying();
  }

  function stepForward() {
    if (stepIndex >= totalSteps()) {
      stopPlaying();
      return;
    }
    goToStep(stepIndex + 1);
  }

  function startPlaying() {
    if (stepIndex >= totalSteps()) stepIndex = 0;
    playing = true;
    scheduleTick();
    render();
  }

  function stopPlaying() {
    playing = false;
    if (timer) clearTimeout(timer);
    timer = null;
    render();
  }

  function scheduleTick() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      stepForward();
      if (playing && stepIndex < totalSteps()) scheduleTick();
      else playing = false;
    }, Number(el.speed.value));
  }

  function loadScenario(key) {
    stopPlaying();
    currentKey = key;
    stepIndex = 0;
    crossedFractureAt = null;
    renderChart(scenario());
    render();
  }

  function loadModel(key) {
    currentModel = key;
    const matchingKeys = refreshScenarioOptions();
    const definition = modelDefinitions[currentModel];
    const displayName = definition.name;

    el.modelSelect.value = currentModel;
    el.eyebrowModel.textContent = displayName.toLowerCase();
    el.modelTitle.textContent = displayName;
    el.modelDescription.textContent = definition.description;
    el.modelDetail.textContent =
      "Every run is precomputed with fixed random seeds, so comparisons are " +
      "repeatable. Regenerate the data with model/generate_simulation.py to " +
      "change parameters or seed sets.";
    el.footerModel.textContent = `${displayName.toLowerCase()} · ${definition.parameter} · ${graph.nodes.length} nodes, ${graph.links.length} edges`;

    loadScenario(matchingKeys[0]);
  }

  // ---- events -------------------------------------------------------
  el.modelSelect.addEventListener("change", (e) => loadModel(e.target.value));
  el.scenarioSelect.addEventListener("change", (e) => loadScenario(e.target.value));
  el.play.addEventListener("click", () => (playing ? stopPlaying() : startPlaying()));
  el.step.addEventListener("click", () => {
    stopPlaying();
    stepForward();
  });
  el.reset.addEventListener("click", () => loadScenario(currentKey));
  el.speed.addEventListener("input", () => {
    if (playing) scheduleTick();
  });

  loadModel(currentModel);
})();
