# Local validation — 22 November 2026

Machine: AMD Ryzen 7 5800HS, 8 physical cores / 16 logical processors, 16 GB installed RAM (15.41 GiB usable), Windows, Python 3.12.2. All inference used the CPU-only runtime with zero GPU layers.

## Installed and indexed

- Runtime archive and both model files passed the pinned SHA-256 checks.
- Runtime, models, logs, index, and embedding cache occupy approximately **2.26 GB** on disk, excluding the pre-existing corpus.
- The index contains **3,382 passages** from all **2,975 source records** and **340 articles**. Its size is **18.47 MB**.
- Character-span coverage was checked against every original record: no text loss. Every indexed passage is at most **360 actual BGE tokens**.
- SQLite integrity check: `ok`. Passage and FTS row counts both equal 3,382.
- The unchanged-index path recomputed no embeddings. Rebuilding the metadata reused 3,370 cached embeddings; the initial full embedding build took about 347 seconds.

## Functional checks

- **14 model-free regression tests passed**, covering chunk coverage, Unicode, long unbroken strings, invalid/duplicate records, resumable embeddings, stale indexes, interrupted builds, source/module filters, false exam claims, corrections, citation validation, concurrent index writers, and exact-excerpt fallback for unsupported object names or years.
- **8/8 real semantic retrieval checks passed**, finding the expected articles for Lotus Mahal, kalamkari, La Japonaise, Mannen Bridge, Gandaberunda, the cover dish, granite/chlorite friezes, and A Goldsmith in his Shop.
- Actual generated answers correctly distinguished **1876 from the lecture's 1875** for La Japonaise and **ca. 1830–32 from the lecture's 1823** for Mannen Bridge. The maker of the cover dish remained **unconfirmed**. Their cited passages were inspected.
- The final retrieval cutoff is **0.55**. The eight positive retrieval cases still pass it (their best cosine scores were approximately 0.69–0.82).
- A question about Tesla battery voltage was refused in **0.19 seconds**, with `insufficient_evidence: true`, no fabricated citations, and **no LLM process started**.
- Interactive chat opened and exited successfully. Owned inference processes were closed after testing.

During development, unconstrained inline citations and repeated answer paragraphs were unreliable on the 3B model. The final output schema requires one paragraph and a validated source list. An unrelated question also exposed an inconsistent model refusal flag at the old 0.48 retrieval cutoff; the 0.55 cutoff now rejects that weak match before generation. Manual inspection additionally found an extra Charminar comparison in a Lotus Mahal summary that was absent from its cited excerpts. Prompt instructions alone did not reliably prevent this. A conservative check now detects known object names and years missing from cited text and returns exact excerpts instead of that draft summary. This is not a full semantic verifier.

## Resource observations

| Measurement | Observed value |
|---|---:|
| Combined sampled peak working sets: Python + both inference processes | **3.359 GiB** |
| Warm retrieval | Approximately **0.14–0.20 seconds** |
| First retrieval including embedding-model start | Approximately **0.7 seconds** |
| Four generated factual/attribution answers during the measured run | **52–71 seconds each** |
| Token generation during those answers | Approximately **6–11 tokens/second** |

These are observations under the machine's running workload, not throughput guarantees. Model startup and prompt processing are included in answer latency where applicable. Other applications were using much of the installed RAM during development; leave approximately 4–6 GB free for more consistent performance.

## Offline scope and reproducible reports

The real retrieval/answer checks ran with Python socket connections restricted to loopback and llama.cpp's `--offline` flag enabled. Models were loaded from local files. No cloud inference or web lookup was used. This verifies the application path; a physical network-disconnection test was not performed.

- [Full diagnostic run](data/evaluation-full.json): retrieved evidence, generated answers, timings, and memory. This historical run includes the old-cutoff refusal-flag failure described above.
- [Final cutoff checks](data/evaluation-final-gate.json): reruns all eight retrieval cases, confirms the four previously tested positive answer paths still pass the new cutoff, and verifies immediate refusal of the unrelated question. The four positive answers were not regenerated solely for that cutoff change.
- [Final answer check](data/evaluation-final-answer.json): targeted generation after the final prompt refinement and evidence fallback were added. The two date answers and the draft-maker answer were tested earlier; their cited evidence was inspected and supports the mentioned names and dates.
- [Support-check regression](data/evaluation-support-checks.json): the final guard accepts the earlier supported dates and maker uncertainty, and detects the unsupported comparison. The real final answer check returned an exact Lotus Mahal structural-system excerpt in 66.05 seconds, with the unsupported comparison removed.

Run `python -m unittest local_rag.test_rag -v` and `python -m local_rag.evaluate --generate` to repeat the checks. Evaluation JSON files are local generated artifacts, excluded from Git.

This is a small smoke suite, not a comprehensive accuracy study. A valid citation ID does not prove semantic support for every generated claim. The 3B model can still add unsupported details; inspect the cited excerpts with `search` when exact wording or attribution matters. The retrieval cutoff is a heuristic, not a calibrated confidence probability.
