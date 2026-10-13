# Semantic Vector Sliding Window

A browser-based text-window utility and a Python package for sliding-window and boundary experiments. The browser tool is deterministic and runs locally: it does **not** call a remote model or API.

## Browser application

The standalone app is in [web/index.html](web/index.html). Run it locally with:

```bash
python -m http.server 8080 --directory web
```

Open `http://localhost:8080`, then:

1. Paste text or load a local `.txt`/`.md` file (maximum 1 MB).
2. Adjust the adjacent-similarity threshold, minimum text units per segment, and overlap units.
3. Select **Analyze windows** to inspect segments, or **Export JSON** to download their boundaries and content.

By default the browser compares adjacent sentence/line units using **word-set Jaccard similarity**; this is a lexical heuristic, not a semantic embedding model. To use cosine similarity, provide JSON containing one equal-length numeric embedding vector per detected unit. Boundaries are chosen where adjacent similarity falls below the selected threshold, subject to the segment-length constraint. Overlap repeats preceding units into subsequent windows.

The browser version uses native JavaScript rather than downloading a Python runtime. It requires a modern browser with Unicode regular expressions and lookbehind support. All browser input stays in the tab unless you explicitly export it. There is no upload endpoint, analytics, or browser storage in the web app.

A GitHub Pages deployment workflow publishes the `web/` directory from `master` when GitHub Pages is enabled. Deployment is not considered live until the published URL is verified.

## Python package

Python 3.10 or later is required. Install for development:

```bash
python -m pip install -e ".[server,test]"
python -m pytest -q
```

The importable `vector_window` package includes:

- `semantic_boundaries.SemanticBoundaryDetector`: consecutive-embedding cosine similarity, or lexical similarity when embeddings are absent; segmentation with a minimum size.
- `overlap_smoothing.OverlapSmoother`: numeric overlap blending (linear, cosine, sigmoid), or discrete choice for nonnumeric elements.
- `auto_tuning.WindowAutoTuner`: heuristic query-complexity-based window sizing.
- `vector_window.cli`: an independent parameter-audit and CSV demonstration interface.

Example:

```python
from vector_window.semantic_boundaries import SemanticBoundaryDetector

units = ["A first topic.", "Related information.", "A distinct subject."]
detector = SemanticBoundaryDetector(similarity_threshold=0.4, min_segment_size=1)
segments = detector.split_at_boundaries(units)
print(segments)
```

The installed command `semantic-vector-sliding-window` exposes the `vector_window.cli` demo:

```bash
semantic-vector-sliding-window audit --task-id EXAMPLE --primary 12 --secondary 3 --status NOMINAL
semantic-vector-sliding-window batch --input sample.csv --output results.csv
```

## Legacy demonstration API

The top-level `cli.py` and `agents/` code form a **separate synthetic threshold-audit demo**, not the browser chunking engine. They do not calculate clinically validated risk, perform remote LLM reasoning, or provide an actual patient safety system. Thresholds and labels in that demo are illustrative and should not be used for clinical decisions.

```bash
python cli.py audit
python cli.py batch -i sample.csv -o results.csv
python cli.py serve
```

The FastAPI server exposes `/health`, `/metrics` (Prometheus text), `/api/audit`, `/api/chat` (deterministic mock), and `/api/audit/logs`. The audit log endpoint returns HTTP 403 unless `AUDIT_ACCESS_TOKEN` is configured and supplied as the `X-Audit-Token` header. The identifier-pattern guard is **not** comprehensive PHI detection or HIPAA de-identification.

An audit signing key is generated in memory if `AUDIT_SECRET_KEY` is absent. Set a sufficiently strong private `AUDIT_SECRET_KEY` for deployments requiring a stable audit key across process restarts. HMAC chain validation detects modifications to stored entries, but an in-memory log is not durable storage or an externally anchored audit ledger.

For Docker Compose, define `AUDIT_SECRET_KEY` in your shell or a private local `.env` file, then run `docker compose up --build`. Never commit actual signing keys or access tokens.

## Development and security

CI checks the package on Python 3.10–3.12, runs the test suite, checks package dependencies, and validates the browser JavaScript syntax with Node.js. Neither the package nor the browser app requires an external LLM or paid service.

The browser processes local content in the user's browser; the optional FastAPI service processes submitted data on the server and keeps its demonstration audit records in process memory. Do not submit identifiable patient data to the demonstration API.

## License

[MIT](LICENSE).
