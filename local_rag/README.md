# ART403 offline RAG

A local question-answering pipeline built for this corpus and the Ryzen 7 5800HS / 16 GB RAM Windows machine. It uses the existing `retrieval_chunks.jsonl`; it does not rerun OCR, contact museum websites, or upload your documents.

## Recommended stack

| Component | Choice | Why it fits |
|---|---|---|
| Answer model | Qwen2.5 3B Instruct, GGUF Q4_K_M | About 2.10 GB of weights; a practical small instruction model for answers grounded in short excerpts |
| Embeddings | BGE-small-en-v1.5, GGUF Q8_0 | 36.7 MB, 384-dimensional vectors, English retrieval |
| Inference | Portable llama.cpp Windows x64 CPU build b12628 | 25 MB download; no GPU drivers, Docker, PyTorch, or compilation |
| Retrieval | SQLite FTS5/BM25 + exact cosine search + reciprocal rank fusion | A few thousand passages do not require a vector database service or FAISS |
| Application | Python 3.11+ standard library | No pip dependencies; Python 3.12 is already installed here |

Budget approximately **3-4 GB of available RAM** for the application, with **4-6 GB free** preferable to leave headroom. These are planning estimates, not a guarantee of throughput. Total installed RAM is sufficient; the apps already running on the machine affect speed. The integrated graphics allocation is not used. Disk use for the complete runtime, weights, and index is comfortably below 3 GB, excluding the existing corpus; allow 4 GB while setting up. Your 155 GB free disk space is ample.

Default settings: 6 inference threads, 4 embedding threads, **0 GPU layers**, one generation slot, 4,096-token context, and a 420-token answer cap. The 3B model is intentionally modest: long comparisons and subtle attribution questions can still require reviewing the cited articles. A 7B/8B model would take more RAM and CPU time; it is not the default on this machine. If memory or speed remains limiting after closing large apps, a 1.5B quantized model is a possible future tradeoff, with reduced answer quality; it is not installed by this setup.

## Use it

Open PowerShell in the project folder (the folder containing `retrieval_chunks.jsonl`):

```powershell
python -m local_rag doctor
python -m local_rag ask "What structural features distinguish the Lotus Mahal?"
python -m local_rag mcq --file local_rag/sample-quiz.txt
python -m local_rag chat
```

Or double-click **Start-RAG.cmd** in this directory. Enter `/exit` to release both model processes. Each question is independent: include the artwork or subject name again in follow-up questions. Chat keeps the models loaded for faster subsequent questions; a one-shot `ask` closes them when it finishes. Answer generation may take tens of seconds on CPU, especially under memory pressure.

Useful commands:

```powershell
# Inspect retrieved excerpts without generating an answer.
python -m local_rag search "Cassatt aquatint woodblock"

# Keyword-only search works without any model process.
python -m local_rag search "Gandaberunda" --lexical

# Restrict evidence. Sourced is a corpus status, not a guarantee of verified attribution.
python -m local_rag ask "Describe Lotus Mahal's arches" --module 1 --sourced-only

# Explicitly include exam distractors together with their corrections.
python -m local_rag ask "Why is the floral-only reading of the course cover wrong?" --include-distractors

# Full machine-readable result: answer, citations, excerpts, provenance, and timings.
python -m local_rag ask "When was La Japonaise painted?" --json

# Rebuild after regenerating the corpus. Unchanged passage embeddings are cached.
python -m local_rag index

# Verify model integrity and current index readiness.
python -m local_rag doctor --verify
```

## Multiple-choice questions

Use `mcq`, not `ask`. `ask` is built for open questions: it returns a paragraph, and its
answer schema has no field for a letter, so it can describe the right option without ever
naming it. `mcq` retrieves separately for each option, judges every option, then commits.

```powershell
python -m local_rag mcq "Which features are characteristic of the Lotus Mahal at Hampi?
A. Rock-cut cave shrines of the Gupta period
B. Cusped arches combined with Hindu temple superstructures
C. A Portuguese colonial chapel plan
D. A timber Mughal pavilion"
```

Write the stem first, then one option per line starting with `A.`, `B)`, or `(c)`. Options
must run in order from A. Lines beginning with `#` are ignored. Omit the question to type
or paste it on stdin (finish with Ctrl+Z then Enter).

The output marks each option `+` supported, `x` contradicted, or `?` unsupported, where
unsupported means **this corpus is silent**, not that the option is false. An option is
only chosen if cited evidence supports it; otherwise the answer is an explicit refusal.

```powershell
# A whole practice set. An optional "Answer: X" line per question is scored and hidden from the model.
python -m local_rag mcq --file local_rag/sample-quiz.txt

# Answer anyway when the stem names something the corpus never mentions.
python -m local_rag mcq --file quiz.txt --allow-unknown-terms

# Per-option verdicts, citations, and timings as JSON.
python -m local_rag mcq "..." --json
```

`sample-quiz.txt` is a worked example in the expected format.

Three behaviours differ from `ask` deliberately:

- **Distractors are included by default.** An MCQ distractor is often the corpus's own
  recorded false exam claim, which travels with its correction. `--exclude-distractors`
  restores the `ask` default.
- **Out-of-corpus questions are refused before any inference.** If the stem names a proper
  noun absent from the whole corpus, you get an immediate refusal naming the term rather
  than a fluent answer drawn from loosely related passages. Similarity alone does not catch
  this: an off-topic question still matches generic passages at a respectable cosine.
  `--allow-unknown-terms` overrides it.
- **Names from the options are not treated as hallucinations.** `ask` rejects any answer
  containing a name or year missing from the cited excerpts, which would reject every
  explanation of why a distractor is wrong. `mcq` checks only years that the model
  introduced itself and did not quote from the question.

Expect 90-150 seconds per question on this machine: four extra retrievals are cheap, but
the model writes a verdict for every option. `mcq_answer_tokens` in `config.json` caps that
reasoning. A `contested` note means more than one option was judged supported; read the
excerpts before trusting the letter. The 3B model's notes are terse and sometimes repeat
one sentence across options. The letter and its citations are the reliable part; the prose
is not an exam-grade justification.

Additional filters: `--article ARTICLE_ID`, `--top-k 1..12`, and `--lexical`. `--lexical` changes retrieval only; `ask` and `chat` still use the LLM. `search --lexical` is the option requiring no models. Module filters refer to recorded slide occurrences, including recurring objects.

## One-time setup or reinstall

**Internet is needed only to obtain the runtime and model files.** Once setup and indexing finish, all the commands above work without Internet access. No API key or subscription is required.

```powershell
python -m local_rag.bootstrap
python -m local_rag index
python -m local_rag doctor --verify
```

`Setup-RAG.ps1` runs these three steps. Downloads resume from `.partial` files. `assets.json` pins the runtime release, model repository revisions, file sizes, and SHA-256 checksums. Setup verifies each download before use. It does not install a Windows service, change PATH, or change firewall settings.

The large runtime and weights live in `%LOCALAPPDATA%\ART403-RAG`, outside the OneDrive project folder. Set `ART403_RAG_HOME` **before both setup and use** to choose another directory. Copy that entire directory, this project, and an installed Python 3.11+ interpreter to prepare a completely disconnected Windows x64 machine; downloads are not attempted by query commands. Keep the corpus files available locally in OneDrive ("Always keep on this device") if they could otherwise be made online-only.

## How evidence reaches an answer

```text
retrieval_chunks.jsonl
   -> validate identifiers and provenance
   -> split with the embedding model's actual tokenizer
   -> BGE vectors + SQLite keyword index (saved locally)

Question
   -> BGE query vector + keyword search
   -> reciprocal rank fusion and article diversity
   -> attach catalogue corrections and attribution notes
   -> fit evidence into the LLM's actual token budget
   -> CPU Qwen answer
   -> validate citation IDs and show local article/slide references
```

The original 2,975 records describe 340 articles. Long sections are split into passages of at most 360 BGE tokens, including their title, with up to 24 words of overlap. Splits preserve Unicode text and original record IDs. Metadata retains source URLs, article paths, slides, draft/sourced status, evidence category, and section-level confidence tiers. The application never treats the corpus's `cl100k_base` token counts as BGE or Qwen token counts.

Search uses the BGE query instruction and CLS pooling, with L2-normalized 384-dimensional vectors. Vectors are compact float32 blobs in SQLite; exhaustive cosine ranking is adequate at this corpus size. Keyword search helps exact artwork names and dates. Navigation/link-list sections are indexed but excluded from retrieval results. Filters are applied before candidate cutoffs. At most three initially retrieved passages per article prevent one article from filling every slot.

Catalogue **External Checks** and **Attribution Notes** are attached to retrieved articles. The prompt gives catalogue corrections priority over conflicting raw lecture assertions and keeps `Course reading:` interpretations distinct from observations. Deliberately false exam claims are excluded by default. When explicitly included, their entire original record, including the correction, is supplied together.

Answers cite `[S1]`, `[S2]`, etc., which map to actual provided excerpts. Constrained generation returns one concise answer paragraph and its source list; the application checks the identifiers and attaches the visible citations. This also prevents the small model from producing multiple repetitive summary paragraphs. A further conservative check looks for known corpus object names and years absent from the cited excerpts. If those checks or the answer-structure checks fail, the application replaces the draft summary with **exact corpus excerpts**, clearly labelled as evidence (`mode: evidence_only` in JSON). Context overflow and incomplete outputs produce an actionable error. Weak retrieval and model-declared insufficient evidence produce an explicit refusal. The similarity threshold in `config.json` is a heuristic, **not a calibrated confidence score**. These checks cannot prove semantic support for every generated claim, and may reject a valid paraphrase or expanded date range. Check the cited passages when precision matters.

## Offline behavior and persistence

- Inference servers use local GGUF paths, `--offline`, and `--n-gpu-layers 0`. They bind only to `127.0.0.1` on temporary ports, with their web interfaces disabled and a randomly generated per-process API token.
- Python ignores HTTP proxy settings for inference and refuses redirects. There are no web-search, analytics, or cloud-model calls in indexing or answering.
- Only this application's own hidden child processes are terminated on normal exit or Ctrl+C. No other apps are closed to free memory.
- `data/index.sqlite3` holds the current index; `data/embedding-cache.sqlite3` permits interrupted builds to resume. A complete temporary build replaces the index atomically. Duplicate IDs, invalid records, changed corpus hashes, and incompatible configuration fail visibly.
- Close other RAG sessions before rebuilding on Windows. An index-build lock prevents concurrent writers. The previous complete index remains intact if a new build fails.
- Runtime logs are under `%LOCALAPPDATA%\ART403-RAG\logs`. Answers are printed to the terminal; the application does not maintain chat history. Evaluation commands explicitly save their results under `data/`.

If the process is forcibly killed or the PC shuts down unexpectedly, its cleanup code cannot run. If a `llama-server.exe` process remains, inspect its command line before closing it; a new invocation otherwise starts its own isolated servers.

## Checks and tuning

See [VALIDATION.md](VALIDATION.md) for the checks and resource measurements from this machine.

```powershell
# Fast, model-free regression tests.
python -m unittest local_rag.test_rag local_rag.test_mcq -v

# Actual local semantic retrieval checks.
python -m local_rag.evaluate

# Also generate five corpus-grounded answers, including a refusal and a draft attribution.
python -m local_rag.evaluate --generate
```

The evaluation blocks Python network connections to non-loopback addresses and starts llama.cpp with offline mode enabled. It checks expected retrieved articles, selected answer facts, and refusals; it is a small smoke suite, not a comprehensive accuracy benchmark. Reports include timings, settings, source passages, and sampled combined process working sets. An Internet-connected development machine is not the same as a physical network-disconnection test.

Edit `config.json` to tune threads (try 4, 6, then 8), the answer cap, or the retrieval count. Avoid using all 16 logical threads by default. Larger contexts increase prompt-processing time and memory. Changing chunk size or overlap requires `index`; changing generation settings does not. If an answer exceeds its output budget, ask a narrower question or increase `max_answer_tokens` to 600. If retrieval misses a fact, inspect `search --json` and adjust query wording or `--top-k` before changing models.

This is **text RAG** over the existing reviewed descriptions. It does not re-examine the PDF images. BGE-small is an English embedding model; use English questions for best retrieval. The original corpus's draft identifications and external source limitations remain applicable.

## Upstream references and licenses

- [Qwen's official Qwen2.5 3B GGUF repository](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF) and [pinned weights](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/tree/7dabda4d13d513e3e842b20f0d435c732f172cbe): Qwen Research License. Review that license if you later plan uses beyond this personal study setup.
- [BGE model card](https://huggingface.co/BAAI/bge-small-en-v1.5) and [ggml-org's quantized conversion](https://huggingface.co/ggml-org/bge-small-en-v1.5-Q8_0-GGUF): MIT license, 384 dimensions, 512-token input limit.
- [llama.cpp release b12628](https://github.com/ggml-org/llama.cpp/releases/tag/b12628) and [server API documentation](https://github.com/ggml-org/llama.cpp/blob/b12628/tools/server/README.md): MIT license.

These links document the chosen components; normal use never fetches them.
