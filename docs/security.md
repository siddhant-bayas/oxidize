# security -- secret scanning

oxidize includes a built-in secret scanner that detects API keys, tokens, private keys, and credentials in your codebase before you commit them.

## usage

```bash
# scan entire working directory
oxidize scan

# scan specific files or directories
oxidize scan main.py src/

# scan only staged files
oxidize scan --staged

# scan specific file
oxidize scan config.py --staged
```

## detected patterns (21 total)

### cloud providers

| pattern | example match |
|---------|--------------|
| AWS Access Key | `AKIAIOSFODNN7EXAMPLE` |
| AWS Secret Key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| GCP API Key | `AIzaSyD-example1234567890` |
| Google OAuth Token | `ya29.example1234567890` |

### code hosting

| pattern | example match |
|---------|--------------|
| GitHub PAT | `ghp_XXXX...` (starts with `ghp_` + 36 alphanum chars) |
| GitHub Fine-Grained PAT | `github_pat_XXXX...` (starts with `github_pat_` + long string) |
| GitLab PAT | `glpat-XXXX...` (starts with `glpat-` + alphanum) |

### communication

| pattern | example match |
|---------|--------------|
| Slack Token | `xoxb-XXXX...` (starts with `xoxb-`) |
| Slack Webhook | `https://hooks.slack.com/services/T.../B.../...` |

### payments

| pattern | example match |
|---------|--------------|
| Stripe Secret Key | `sk_live_XXXX...` (starts with `sk_live_` + alphanum) |

### ai/ml services

| pattern | example match |
|---------|--------------|
| OpenAI API Key | `sk-XXXX...` (starts with `sk-` + long string) |
| OpenAI Project Key | `sk-proj-XXXX...` (starts with `sk-proj-`) |
| Anthropic API Key | `sk-ant-XXXX...` (starts with `sk-ant-`) |
| HuggingFace Token | `hf_XXXX...` (starts with `hf_`) |

### email/messaging

| pattern | example match |
|---------|--------------|
| SendGrid API | `SG.XXXX...` (starts with `SG.` + alphanum) |
| Twilio SID | `AC...` (starts with `AC` + 32 hex chars) |
| Mailgun API | `key-XXXX...` (starts with `key-` + alphanum) |

### generic patterns

| pattern | example match |
|---------|--------------|
| API Key | `api_key=ABCDEF1234567890` |
| Private Key Block | `-----BEGIN RSA PRIVATE KEY-----` |
| JWT Token | `eyJhbGciOiJIUzI1NiIs...` |
| Connection String | `postgres://user:pass@host:5432/db` |
| Bearer Token | `Bearer eyJhbGciOi...` |
| Generic Password | `password=supersecret123` |

## ignored directories

the scanner automatically skips these directories (hardcoded; cannot be un-ignored):

- `.oxidize/`
- `.git/`
- `__pycache__/`
- `node_modules/`
- `.venv/`
- `venv/`
- `.mypy_cache/`
- `.pytest_cache/`
- `.ruff_cache/`
- `*.egg-info/`
- `dist/`
- `build/`

in addition, `oxidize scan` **respects `.oxignore`** by default: any path that `oxidize add` would skip is also skipped here. pass `--no-oxignore` to disable the rule for a single invocation (e.g. for a one-off security audit).

## output format

when secrets are found, the scanner outputs:

```
GitHub PAT main.py:15 -- ghp_ABCDEF1234567890abcdef
Stripe Secret Key config.py:42 -- sk_live_ABCDEF1234567890
```

format: `[type] [file]:[line] -- [matched text]`

## using programmatically

```python
from pathlib import Path
from oxidize.security.scanner import scan_text, scan_file, scan_directory, scan_paths
from oxidize.core.ignores import IgnoreMatcher

# scan a string
results = scan_text("api_key = 'ghp_ABCDEF1234567890'", "config.py")
for r in results:
    print(f"{r['type']} in {r['file']}:{r['line']}")

# scan a single file
results = scan_file(Path("config.py"), Path("."))

# scan entire directory, respecting .oxignore
matcher = IgnoreMatcher.from_repo(...)  # any Repository-like object
results = scan_directory(Path("."), matcher)

# scan a specific list of paths
results = scan_paths([Path("src/"), Path("config.py")], Path("."), matcher)
```

each result is a dict with keys:
- `type` -- the type of secret found (e.g. "GitHub PAT")
- `file` -- the file path
- `line` -- the line number (1-indexed)
- `match` -- the matched text

## before commit

the scanner can be run before commit to catch secrets early:

```bash
# scan staged files before committing
oxidize scan --staged

# if clean, proceed
oxidize commit -m "add config"
```

**note:** the `scan_on_commit` config option is mentioned in architecture but is not currently enforced automatically. run `oxidize scan --staged` manually before committing for now.
