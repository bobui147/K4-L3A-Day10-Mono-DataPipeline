# Baseline Pipeline Report

## Data source

- Source: Preserved Crossref snapshot
- Live refresh requested: False
- Raw records: 24
- Clean records: 24
- Query: agentic retrieval augmented generation large language model

## Evaluation

| Metric | Value |
| --- | ---: |
| Questions | 10 |
| Retrieval Hit Rate | 1.000 |
| Mean Token F1 | 0.974 |
| Judge Accuracy | 0.900 |
| Mean Judge Score (1-5) | 4.800 |
| Judge heuristic fallbacks | 0 |

## Data quality

- Quality gate: PASS
- GX checks: PASS
- Freshness SLA: PASS

| GX expectation | Column | Result |
| --- | --- | --- |
| expect_table_row_count_to_be_between | - | PASS |
| expect_column_values_to_not_be_null | paper_id | PASS |
| expect_column_values_to_not_be_null | title | PASS |
| expect_column_values_to_not_be_null | summary | PASS |
| expect_column_values_to_not_be_null | text_for_embedding | PASS |
| expect_column_values_to_be_unique | paper_id | PASS |
| expect_column_value_lengths_to_be_between | summary | PASS |
| expect_column_value_lengths_to_be_between | title | PASS |
| expect_column_value_lengths_to_be_between | paper_id | PASS |
| expect_column_value_lengths_to_be_between | text_for_embedding | PASS |

## Freshness

- Latest publication: 2026-07-22
- Oldest publication: 2026-03-28
- Stale records: 1/24
- Stale ratio: 4.2%
- Threshold: older than 180 days; alert above 25% stale

## Ragas

- Set RUN_RAGAS=1 to enable the slower Ragas pass.
