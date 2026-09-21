# infodiff-model

Two classic information-diffusion models — **Independent Cascade** and
**Linear Threshold** — repurposed as a **learner model**: how understanding
spreads through a concept graph.

The default network is a hand-built **Fourier / sine-wave concept graph**:
five core concepts (frequency, amplitude, phase, superposition, spectrum)
and four documented misconceptions — M1 (faster wiggle = taller wave),
M2 (adding waves adds their frequencies), M3 (phase shift changes pitch),
M4 (a square wave contains one frequency) — wired by prerequisite links.
The Python models compute how a breakthrough on one concept propagates
node-by-node under different starting conditions. The results are exported
as JSON and played back frame-by-frame in a small interactive site on
GitHub Pages.

**Live demo:** `https://cmpsno.github.io/infodiff-model/`

## How the models work

The [Independent Cascade
model](https://en.wikipedia.org/wiki/Independent_cascade_model) is one of
the two canonical diffusion models in network science (the other being
Linear Threshold). Starting from a seed set:

1. Every node that just became active gets exactly **one independent
   chance** to activate each of its still-inactive neighbors, with a fixed
   probability `p`.
2. A failed attempt is never retried on that edge.
3. The cascade halts once a full round produces no new activations.

On the concept graph, IC is the **"aha" model**: a newly mastered concept
gets one shot at unlocking each related concept.

The **Linear Threshold** model captures reinforcement instead of one-shot
transmission. Every inactive node has an individual threshold and activates
once the share of its active neighbors meets that threshold. On the concept
graph, LT is **mastery propagation**: a concept is mastered once enough of
its prerequisites are, and misconceptions carry higher thresholds (0.55 vs
0.3) — they only resolve once most of their prerequisites are mastered. The
same node thresholds are shared across all four LT scenarios, so changing
the seed location is a fair comparison.

The default dataset precomputes four starting conditions for both models
(frequency clicks first; superposition clicks; confront M1 head-on;
frequency + amplitude together). The site can show IC and LT side by side
on a synchronized timeline, scrub in either direction, color nodes by
mastery step, expose LT thresholds, and export the current network frame
as PNG.

## Repo structure

```
infodiff-model/
├── model/
│   ├── independent_cascade.py   # the diffusion model itself ("aha" spreading)
│   ├── linear_threshold.py      # reinforcement diffusion model (mastery propagation)
│   ├── generate_simulation.py   # builds the graph, runs all scenarios, writes JSON
│   ├── configuration.py         # validated experiment configuration
│   ├── graph_io.py              # graph files, built-in generators, fourier concept graph
│   ├── batch_simulate.py        # repeated runs and statistical CSV summaries
│   ├── example_config.json      # example sweep configuration
│   ├── test_models.py           # model and generated-data contract tests
│   └── requirements.txt
├── data/
│   └── simulation.json          # generated output (checked in for convenience)
└── docs/                        # GitHub Pages site (static, no build step)
    ├── index.html
    ├── style.css
    ├── script.js
    └── simulation.json          # copy of data/simulation.json the site fetches
```

## Regenerating the simulation data

```bash
cd model
pip install -r requirements.txt
python3 generate_simulation.py
```

This is deterministic: every scenario is driven by a fixed random seed.
The default command builds the Fourier concept-graph experiment.

Run the classic Karate Club version instead:

```bash
python3 generate_simulation.py --graph karate --seeds 33
```

Run a parameter sweep on a generated graph:

```bash
python3 generate_simulation.py \
  --graph erdos_renyi:100,0.05 --model both --p 0.1 0.2 0.3 --seeds 0 1
```

Or use the supplied JSON configuration:

```bash
python3 generate_simulation.py --config example_config.json
```

Graph sources include `fourier`, `karate`, `erdos_renyi:n,p`,
`barabasi_albert:n,m`, `watts_strogatz:n,k,p`, and local `.csv`,
`.edgelist`, `.gml`, `.graphml`, or Pajek `.net` files. Arbitrary
file node labels are normalized to stable integer IDs, with the source labels
retained in generated data. Threshold distributions can be uniform, normal,
or a custom node-to-threshold mapping.

## Batch experiments

Repeated IC runs produce raw results and a summary with mean, median,
variance, and a 95% normal-approximation confidence interval:

```bash
python3 batch_simulate.py --graph fourier --seeds 0 --p 0.1 0.2 0.3 \
  --runs 100 --output-prefix results/fourier
```

This writes `results/fourier_runs.csv` and
`results/fourier_summary.csv`.

## Running the tests

```bash
cd model
python3 -m unittest -v
```

The tests cover deterministic IC behavior, synchronous LT activation, result
invariants, the Fourier concept-graph structure (including the exact
`frequency-first` LT spread the site's story describes), and the JSON
playback contract shared by all generated scenarios.

## Viewing the site locally

The `docs/` folder is a plain static site (D3.js loaded from a CDN, no
bundler). Serve it locally with:

```bash
cd docs
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Publishing on GitHub Pages

1. Push this repo to GitHub.
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **Deploy from a
   branch**.
4. Set the branch to `main` and the folder to **`/docs`**, then save.
5. GitHub will publish the site at
   `https://cmpsno.github.io/infodiff-model/` within a minute or
   two.

## Extending this

Some natural next steps if you want to keep building:

- Add a second concept domain (softmax) as a new built-in graph — the
  site renders any `graph.nodes` / `graph.links` payload in the same shape.
- Make the front end fully interactive: run the cascade live in the
  browser instead of replaying precomputed steps, so visitors can click
  any concept to seed it.
- Track *which* edge caused each activation (rather than just which nodes
  activated) to animate individual "transmission" events along specific
  links.
- Feed real learner data back in: fit per-node thresholds from observed
  mastery sequences instead of hand-setting them.

## License

MIT — see [LICENSE](LICENSE).
