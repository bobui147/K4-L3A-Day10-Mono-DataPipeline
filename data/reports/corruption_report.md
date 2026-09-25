# Corruption and Repair Report

## Three-state comparison

| Metric | Clean baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Questions | 10 | 10 | 10 |
| Retrieval Hit Rate@4 | 1.000 | 0.700 | 1.000 |
| Mean Token F1 | 0.974 | 0.600 | 0.974 |
| Judge Accuracy | 0.900 | 0.600 | 0.900 |
| Mean Judge Score (1-5) | 4.800 | 3.700 | 4.800 |
| Judge heuristic fallbacks | 0 | 0 | 0 |
| Quality gate | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Stale ratio | 4.2% | 28.6% | 4.2% |

## Controlled corruption

| Defect | Affected records |
| --- | ---: |
| drop_latest_records | 5 |
| blank_summary | 3 |
| inject_noise | 3 |
| truncate_title | 3 |
| stale_date | 6 |
| duplicate_rows | 2 |

## Detection and recovery

- Corrupted GX failures: expect_column_values_to_be_unique (paper_id), expect_column_value_lengths_to_be_between (summary), expect_column_value_lengths_to_be_between (title).
- Repaired paper content matches baseline: True.
- Retrieval Hit Rate restored: True.
- Mean Token F1 restored: True.
- Repair source: preserved `data/raw/crossref_records.json`.
