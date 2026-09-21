# infodiff-model

Two classic information-diffusion models — **Independent Cascade** and
**Linear Threshold** — running on a **rumor network**: how September
2026's hot CPI print spread from the newswires through algos and trading
desks until the market priced another Fed rate hike.

On September 11, August CPI printed 3.4% (core 0.3% vs 0.2% expected);
hike odds jumped to 85%. Five days later the Fed raised 25bp to
3.75–4.00% — its first hike since 2023 — the dot plot pointed to one
more this year, the 10Y closed at 5.006%, and gold fell to $4,310.

The default network is a hand-built **rumor-market graph**: 2 rumor
sources (the FOMC, Chair Warsh), 3 media channels (wires, social, TV),
7 market participants (algos, institutional desks, market makers, bond
desks, economists, retail, options), and 8 market outcomes (hike odds,
2Y and 10Y yields, S&P 500, Nasdaq, VIX, the dollar, gold) —
wired by weighted information-flow links. The Python models compute how
the rumor propagates node-by-node under different starting conditions.
The results are exported as JSON and played back frame-by-frame in a
small interactive site on GitHub Pages.

**Live demo:** `https://cmpsno.github.io/infodiff-model/`

## How the models work

The [Independent Cascade
model](https://en.wikipedia.org/wiki/Independent_cascade_model) is one of
the two canonical diffusion models in network science (the other being
Linear Threshold). Starting from a seed set:

1. Every node that just heard the rumor gets exactly **one independent
   chance** to pass it to each of its still-unaware neighbors, with a
   fixed probability `p`.
2. A failed attempt is never retried on that edge.
3. The cascade halts once a full round produces no new activations.

On the rumor network, IC is the **gossip model**: each actor gets one shot
at spreading the rumor to each contact.

The **Linear Threshold** model captures reinforcement instead of one-shot
transmission. Every inactive node has an individual threshold and activates
once the share of its active neighbors meets that threshold. On the rumor
network, LT is **conviction propagation**: algos believe the fastest
(threshold 0.15), retail needs the most confirmation (0.55), and market
outcomes move only once enough participants act on the rumor. The same
node thresholds are shared across all four LT scenarios, so changing the
seed location is a fair comparison.

The default dataset precomputes four starting conditions for both models
(a hot CPI print; the Fed hikes; Warsh doubles down; retail piles in
late). The site can show IC and LT side by side
on a synchronized timeline, scrub in either direction, color nodes by the
step the rumor arrived, expose LT thresholds, read out each market move
as it happens, and export the current network frame as PNG.

## Repo structure

```
infodiff-model/
├── model/
│   ├── independent_cascade.py   # the diffusion model itself (rumor spreading)
│   ├── linear_threshold.py      # reinforcement diffusion model (conviction propagation)
│   ├── generate_simulation.py   # builds the graph, runs all scenarios, writes JSON
│   ├── configuration.py         # validated experiment configuration
│   ├── graph_io.py              # graph files, built-in generators, rumor-market graph
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
The default command builds the rumor-market experiment.

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

Graph sources include `rumor`, `fourier`, `karate`, `erdos_renyi:n,p`,
`barabasi_albert:n,m`, `watts_strogatz:n,k,p`, and local `.csv`,
`.edgelist`, `.gml`, `.graphml`, or Pajek `.net` files. Arbitrary
file node labels are normalized to stable integer IDs, with the source labels
retained in generated data. Threshold distributions can be uniform, normal,
or a custom node-to-threshold mapping.

## Batch experiments

Repeated IC runs produce raw results and a summary with mean, median,
variance, and a 95% normal-approximation confidence interval:

```bash
python3 batch_simulate.py --graph rumor --seeds 0 --p 0.5 0.6 0.7 \
  --runs 100 --output-prefix results/rumor
```

This writes `results/rumor_runs.csv` and
`results/rumor_summary.csv`.

## Running the tests

```bash
cd model
python3 -m unittest -v
```

The tests cover deterministic IC behavior, synchronous LT activation, result
invariants, the rumor-graph structure (including the exact `fed_hike` LT
spread the site's story describes), and the JSON playback contract shared
by all generated scenarios.

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

- Add a second rumor (e.g. an earnings leak) as a competing cascade on
  the same network and watch which reaches the market outcomes first.
- Make the front end fully interactive: run the cascade live in the
  browser instead of replaying precomputed steps, so visitors can click
  any node to seed the rumor there.
- Track *which* edge caused each activation (rather than just which nodes
  activated) to animate individual "transmission" events along specific
  links.
- Calibrate thresholds and edge weights against real event-study data
  (e.g. minute-bar moves around FOMC announcements) instead of
  hand-setting them.

## License

MIT — see [LICENSE](LICENSE).
