/* Synchronized, frame-by-frame comparison of precomputed diffusion runs. */
(async function () {
  const W = 820, H = 620;
  const data = await d3.json("simulation.json");
  const { graph, scenarios, models } = data;
  const keys = Object.keys(scenarios), modelKeys = Object.keys(models);
  const el = Object.fromEntries([
    "model-select","scenario-select","play-btn","back-btn","step-btn","reset-btn",
    "export-btn","speed-range","compare-toggle","timeline-range","step-num","step-of",
    "bar-concept","bar-misconception","count-concept","count-misconception","story-line","eyebrow-model",
    "model-title","model-description","model-detail","footer-model","comparison-panel",
    "primary-label","comparison-label"
  ].map(id => [id, document.getElementById(id)]));
  let model = modelKeys[0], key, step = 0, playing = false, timer;
  const nodes = graph.nodes.map(n => ({...n}));
  const layoutLinks = graph.links.map(l => ({...l}));
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(layoutLinks).id(d => d.id).distance(58).strength(.5))
    .force("charge", d3.forceManyBody().strength(-190))
    .force("center", d3.forceCenter(W/2,H/2)).force("collision", d3.forceCollide(20)).stop();
  for (let i=0;i<340;i++) simulation.tick();
  const positions = new Map(nodes.map(n => [n.id,n]));

  function matching(modelName) { return keys.filter(k => scenarios[k].model === modelName); }
  function baseName(s) { return s.name; }
  function pairedScenario() {
    const other = modelKeys.find(m => m !== model);
    return scenarios[matching(other).find(k => baseName(scenarios[k]) === baseName(scenarios[key]))] || null;
  }
  function activeAt(s, at) {
    return new Set(s.steps.slice(0, at+1).flat());
  }
  function activationTime(s, id) {
    return s.activation_times?.[String(id)] ?? s.steps.findIndex(nodes => nodes.includes(id));
  }
  function drawNetwork(selector, s, at) {
    const svg = d3.select(selector); svg.selectAll("*").remove();
    const active = activeAt(s, at), maxStep = Math.max(1, s.steps.length-1);
    const color = d3.scaleSequential().domain([maxStep,0]).interpolator(d3.interpolateYlOrBr);
    svg.append("g").selectAll("line").data(graph.links).join("line")
      .attr("class","link").classed("pulsed",d => active.has(d.source) && active.has(d.target))
      .attr("x1",d=>positions.get(d.source).x).attr("y1",d=>positions.get(d.source).y)
      .attr("x2",d=>positions.get(d.target).x).attr("y2",d=>positions.get(d.target).y)
      .attr("stroke-width",d=>1+Math.min(4,(d.weight||1)-1));
    const groups = svg.append("g").selectAll("g").data(graph.nodes).join("g")
      .attr("class","node").attr("transform",d=>`translate(${positions.get(d.id).x},${positions.get(d.id).y})`);
    groups.append("circle").attr("class",d=>`ring faction-${d.faction}`)
      .classed("seed",d=>s.seeds.includes(d.id)).attr("r",12);
    groups.append("circle").attr("class","fill").attr("r",8)
      .style("fill",d=>active.has(d.id)?color(activationTime(s,d.id)):null)
      .append("title").text(d => {
        const threshold = s.thresholds?.[String(d.id)];
        return `${d.label || ("Node " + d.id)} · mastered step ${activationTime(s,d.id)}${threshold===undefined?"":` · threshold ${threshold.toFixed(2)}`}`;
      });
    groups.append("text").attr("dy",22).text(d=>d.short||d.id);
    if (s.model==="linear_threshold" && s.thresholds) {
      groups.append("text").attr("class","threshold-label").attr("dy",-17)
        .text(d=>Number(s.thresholds[String(d.id)]).toFixed(2));
    }
  }

  const chartSvg=d3.select("#chart"), chartG=chartSvg.append("g");
  function drawChart(primary, comparison) {
    chartG.selectAll("*").remove();
    const series=[primary, comparison].filter(Boolean), maxX=Math.max(...series.map(s=>s.cumulative_reach.length-1),1);
    const x=d3.scaleLinear().domain([0,maxX]).range([24,250]), y=d3.scaleLinear().domain([0,graph.nodes.length]).range([92,8]);
    chartG.append("line").attr("x1",24).attr("x2",250).attr("y1",92).attr("y2",92).attr("stroke","var(--line)");
    series.forEach((s,i)=>chartG.append("path").datum(s.cumulative_reach).attr("fill","none")
      .attr("stroke",i?"var(--officer)":"var(--gold)").attr("stroke-width",2)
      .attr("d",d3.line().x((_,j)=>x(j)).y(v=>y(v))));
    series.forEach((s,i)=>{
      const at=Math.min(step,s.cumulative_reach.length-1);
      chartG.append("circle").attr("r",3.5).attr("fill",i?"var(--officer)":"var(--gold)")
        .attr("cx",x(at)).attr("cy",y(s.cumulative_reach[at]));
    });
  }
  function totalSteps() {
    const other=el["compare-toggle"].checked?pairedScenario():null;
    return Math.max(scenarios[key].steps.length-1, other?.steps.length-1||0);
  }
  function render() {
    const primary=scenarios[key], other=el["compare-toggle"].checked?pairedScenario():null;
    drawNetwork("#network",primary,Math.min(step,primary.steps.length-1));
    el["primary-label"].textContent=models[primary.model].name;
    el["comparison-panel"].hidden=!other;
    if(other){ drawNetwork("#comparison-network",other,Math.min(step,other.steps.length-1)); el["comparison-label"].textContent=models[other.model].name; }
    drawChart(primary,other);
    const active=activeAt(primary,Math.min(step,primary.steps.length-1));
    const factions=d3.rollup(graph.nodes,v=>v.length,d=>d.faction);
    for(const [faction,prefix] of [["concept","concept"],["misconception","misconception"]]){
      const count=graph.nodes.filter(n=>n.faction===faction&&active.has(n.id)).length, total=factions.get(faction)||graph.nodes.length;
      el[`bar-${prefix}`].style.width=`${100*count/total}%`; el[`count-${prefix}`].textContent=`${count}/${total}`;
    }
    el["step-num"].textContent=step; el["step-of"].textContent=`/ ${totalSteps()}`;
    el["timeline-range"].max=totalSteps(); el["timeline-range"].value=step;
    el["back-btn"].disabled=step===0; el["step-btn"].disabled=step>=totalSteps();
    el["play-btn"].textContent=playing?"Pause":"Play"; el["story-line"].textContent=primary.story;
  }
  function stop(){ playing=false; clearTimeout(timer); if(key) render(); }
  function go(value){ step=Math.max(0,Math.min(value,totalSteps())); if(step===totalSteps())playing=false; render(); }
  function tick(){ timer=setTimeout(()=>{go(step+1); if(playing&&step<totalSteps())tick(); else if(autoplay){ timer=setTimeout(()=>{ if(!autoplay) return; step=0; playing=true; render(); tick(); },1600); } },Number(el["speed-range"].value)); }
  function loadModel(value){
    stop(); model=value; const options=matching(model); el["scenario-select"].replaceChildren(...options.map(k=>new Option(scenarios[k].name,k)));
    key=options[0]; step=0; el["model-select"].value=model;
    el["eyebrow-model"].textContent=models[model].name.toLowerCase(); el["model-title"].textContent=models[model].name;
    el["model-description"].textContent=models[model].description;
    el["model-detail"].textContent="Node color records the mastery step. Hover LT nodes to inspect thresholds; misconceptions carry higher thresholds than core concepts.";
    el["footer-model"].textContent=`${models[model].parameter} · ${graph.nodes.length} nodes, ${graph.links.length} edges`; render();
  }
  el["model-select"].replaceChildren(...modelKeys.map(k=>new Option(models[k].name,k)));
  el["model-select"].onchange=e=>loadModel(e.target.value);
  el["scenario-select"].onchange=e=>{stop();key=e.target.value;step=0;render();};
  el["play-btn"].onclick=()=>{if(playing)stop();else{if(step>=totalSteps())step=0;playing=true;render();tick();}};
  el["back-btn"].onclick=()=>{stop();go(step-1);}; el["step-btn"].onclick=()=>{stop();go(step+1);};
  el["reset-btn"].onclick=()=>{stop();go(0);}; el["timeline-range"].oninput=e=>{stop();go(+e.target.value);};
  el["speed-range"].oninput=()=>{if(playing){clearTimeout(timer);tick();}};
  el["compare-toggle"].onchange=()=>{step=Math.min(step,totalSteps());render();};
  el["export-btn"].onclick=()=>{
    const clone=document.getElementById("network").cloneNode(true);
    clone.setAttribute("xmlns","http://www.w3.org/2000/svg");
    const style=document.createElementNS("http://www.w3.org/2000/svg","style");
    style.textContent=".link{stroke:#c7cbbd;stroke-width:1.2}.link.pulsed{stroke:#c08a25}.ring{fill:none;stroke-width:2.4}.faction-misconception{stroke:#a83b2e}.faction-concept{stroke:#1f5d63}.seed{stroke-width:3.4}.node text{font:9px monospace;fill:#656b60;text-anchor:middle}.threshold-label{font-size:8px;fill:#1b1f1c}";
    clone.prepend(style);
    const source=new XMLSerializer().serializeToString(clone);
    const image=new Image(), blob=new Blob([source],{type:"image/svg+xml;charset=utf-8"}), url=URL.createObjectURL(blob);
    image.onload=()=>{const canvas=document.createElement("canvas");canvas.width=W;canvas.height=H;const ctx=canvas.getContext("2d");
      ctx.fillStyle="#f5f6f1";ctx.fillRect(0,0,W,H);ctx.drawImage(image,0,0);URL.revokeObjectURL(url);
      const a=document.createElement("a");a.download=`infodiff-${key}-step-${step}.png`;a.href=canvas.toDataURL("image/png");a.click();}; image.src=url;
  };
  loadModel(model);
  /* Guided intro: autoplay the core-pair sequence on loop until the viewer takes over. */
  let autoplay = true;
  for (const id of ["play-btn","back-btn","step-btn","reset-btn","timeline-range","speed-range","model-select","scenario-select","compare-toggle","export-btn"]) {
    el[id].addEventListener("pointerdown", () => { autoplay = false; }, { capture: true });
  }
  el["scenario-select"].value = "lt_core_pair";
  key = "lt_core_pair"; step = 0;
  playing = true; render(); tick();
})();
