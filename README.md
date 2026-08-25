# infodiff-model

Two classic information-diffusion models — **Independent Cascade** and
**Linear Threshold** — run on [Zachary's
Karate Club](https://en.wikipedia.org/wiki/Zachary%27s_karate_club) — the
real 34-member social network from a 1977 anthropology study, famous for
splitting into two rival factions during the course of the study.

The Python models compute how a rumor, idea, or product might spread
node-by-node through that network under different starting conditions. The
results are exported as JSON and played back frame-by-frame in a small
interactive site on GitHub Pages.

**Live demo:** enable GitHub Pages for this repo (see below) and it will be
served at `https://<your-username>.github.io/infodiff-model/`.

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

The **Linear Threshold** model captures social reinforcement instead of
one-shot transmission. Every inactive node has an individual threshold and
activates once the share of its active neighbors meets that threshold. This
implementation gives neighbors equal influence and samples reproducible
thresholds from `0.1` to `0.5`. The same node thresholds are shared across
all four LT scenarios, so changing the seed location is a fair comparison.

The repo precomputes the same four starting conditions for both models
(eight runs total), then lets you switch models and step or auto-play through
each run to compare how far — and how evenly — the information spreads.

## Repo structure

```
infodiff-model/
├── model/
│   ├── independent_cascade.py   # the diffusion model itself
│   ├── linear_threshold.py      # social-reinforcement diffusion model
│   ├── generate_simulation.py   # builds the graph, runs all scenarios, writes JSON
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

This is deterministic — every scenario is driven by a fixed
`random.Random(seed)` — so re-running it reproduces the exact same output
unless you change the model parameters or `SEEDING_SCENARIOS` in
`generate_simulation.py`. Each generated scenario includes a `model` and
`parameters` field; the front end uses those model identifiers to populate
and filter its model/scenario selectors.

## Running the tests

```bash
cd model
python3 -m unittest -v
```

The tests cover deterministic IC behavior, synchronous LT activation, result
invariants, and the JSON playback contract shared by all generated scenarios.

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
   `https://<your-username>.github.io/infodiff-model/` within a minute or
   two.

## Extending this

Some natural next steps if you want to keep building:

- Add an **SIR** or **SIS** model with state-aware playback.
- Swap in a different network (any edge list works — the front end only
  needs `graph.nodes` / `graph.links` in the same shape).
- Make the front end fully interactive: run the cascade live in the
  browser instead of replaying precomputed steps, so visitors can click
  any node to seed it.
- Track *which* edge caused each activation (rather than just which nodes
  activated) to animate individual "transmission" events along specific
  links.

## License

MIT — see [LICENSE](LICENSE).
