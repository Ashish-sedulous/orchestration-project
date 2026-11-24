# Results tables (source: results.jsonl, 28 runs)

Models used: {'cheap': 'groq/openai/gpt-oss-20b', 'strong': 'gemini/gemini-3.5-flash', 'judge': 'gemini/gemini-3.5-flash-lite'}

## Overall comparison, loose budget

| Condition | Runs | Success % | Check score | Judge (0-1) mean +/- sd | Median lat (s) | P95 lat (s) | Mean cost | Tokens | Calls | Retries | Swaps | Skipped | Within budget % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| single | 20 | 95.0 | 0.97 | 1.00 +/- 0.00 | 15.3 | 51.9 | $0.00109 | 496 | 1.0 | 0.00 | 0.00 | 0.00 | 100 |
| fixed_pipeline | 3 | 100.0 | 0.92 | 1.00 +/- 0.00 | 20.5 | 22.1 | $0.00370 | 4029 | 4.0 | 0.00 | 0.00 | 0.00 | 100 |
| adaptive | 5 | 100.0 | 1.00 | 1.00 +/- 0.00 | 1.4 | 8.9 | $0.00027 | 798 | 2.0 | 0.00 | 0.00 | 0.00 | 100 |

## Success % and mean cost by task category, loose budget

| Condition | qa | research | coding | data | multi |
|---|---|---|---|---|---|
| single | 100% / $0.0001 | 100% / $0.0016 | 100% / $0.0010 | 100% / $0.0009 | 75% / $0.0018 |
| fixed_pipeline | n/a | n/a | 100% / $0.0025 | 100% / $0.0029 | 100% / $0.0057 |
| adaptive | 100% / $0.0000 | 100% / $0.0001 | 100% / $0.0000 | 100% / $0.0012 | 100% / $0.0001 |

## Paired differences, adaptive minus baseline (loose budget, per-task means, 95% bootstrap CI)

| Comparison | Metric | Mean diff | 95% CI | Tasks |
|---|---|---|---|---|
| adaptive - single | check score | +0.0000 | [+0.0000, +0.0000] | 5 |
| adaptive - single | judge quality | +0.0000 | [+0.0000, +0.0000] | 5 |
| adaptive - single | latency (s) | -26.2900 | [-45.7900, -9.3200] | 5 |
| adaptive - single | cost ($) | -0.0009 | [-0.0016, -0.0002] | 5 |
| adaptive - single | agent calls | +1.0000 | [+1.0000, +1.0000] | 5 |

## Adaptive behaviour, loose budget

Adaptation events: none

Topologies chosen: single=5

Agents selected: research_fast=3, analyst=1, coder_fast=1
