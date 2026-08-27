"""Run repeated IC experiments and save run-level and summary CSV files."""
import argparse, csv, math, random, statistics
from pathlib import Path
from graph_io import load_graph, normalize_node_ids
from independent_cascade import independent_cascade

def run_batch(graph, seeds, probabilities, runs, random_seed=42):
    rows = []
    for probability in probabilities:
        for run in range(runs):
            seed = random_seed + run
            result = independent_cascade(graph, seeds, probability, random.Random(seed))
            rows.append({"p": probability, "run": run + 1, "random_seed": seed, "final_spread": result.activated_total, "steps": len(result.steps)})
    summaries = []
    for probability in probabilities:
        values = [r["final_spread"] for r in rows if r["p"] == probability]
        mean = statistics.fmean(values); std = statistics.stdev(values) if len(values) > 1 else 0
        margin = 1.96 * std / math.sqrt(len(values))
        summaries.append({"p": probability, "runs": len(values), "mean": mean, "median": statistics.median(values),
                          "variance": statistics.variance(values) if len(values) > 1 else 0, "ci95_low": mean-margin, "ci95_high": mean+margin})
    return rows, summaries

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", default="karate"); parser.add_argument("--seeds", type=int, nargs="+", default=[0])
    parser.add_argument("--p", type=float, nargs="+", default=[.1, .2, .3]); parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=42); parser.add_argument("--output-prefix", type=Path, default=Path("batch_results"))
    args = parser.parse_args()
    if args.runs < 1: parser.error("--runs must be at least 1")
    rows, summaries = run_batch(normalize_node_ids(load_graph(args.graph, random_seed=args.random_seed)), args.seeds, args.p, args.runs, args.random_seed)
    write_csv(args.output_prefix.with_name(args.output_prefix.name+"_runs.csv"), rows)
    write_csv(args.output_prefix.with_name(args.output_prefix.name+"_summary.csv"), summaries)
if __name__ == "__main__": main()
