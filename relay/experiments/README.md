# Experiments

Run from this folder with the backend virtual environment active (the same one you use for the API).

1. Smoke test (no API calls):        python run_experiments.py --fake --per-category 1
2. Main comparison (loose budget):   python run_experiments.py --conditions single,fixed_pipeline,adaptive --reps 2 --budget loose
3. Tight budget (subset):            python run_experiments.py --conditions single,fixed_pipeline,adaptive --per-category 2 --budget tight
4. Ablations (subset):               python run_experiments.py --conditions abl_no_adapt,abl_no_early_stop,abl_no_parallel,abl_no_budget,abl_static_selection,abl_no_learning --per-category 2 --budget loose
5. Analyze:                          python analyze_results.py     (add: pip install matplotlib   for the figure)

Runs are saved one line at a time to results/results.jsonl and the script resumes where it stopped.
If you see rate-limit (429) errors, stop, wait a few minutes, and run the same command again.
Outputs: results/tables.md (paper tables), results/summary.csv, results/quality_vs_cost.png.
