"""Per-task local or cloud model, and a cost-gated compare.

Committed defaults live in config/model-choice.json. The operator override
lives in $XDG_CONFIG_HOME/pfy/model-choice.json (default ~/.config/pfy/).
Compare history lives next to the setup ledger, under $XDG_STATE_HOME/pfy/.

Cloud calls go to the LiteLLM proxy (OpenAI-compatible /v1/chat/completions).
Local calls go to Ollama /api/generate. This module does not pull a model
and does not read secret values into logs.

resolve(task) -> (backend, model, source)
source is env, alias, user, default, or fallback.
A cloud backend is returned only when the operator set it.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

TASK_ORDER = (
    "catalog-fit",
    "eval-suite",
    "matrix",
    "decision-route",
    "build-lane",
)
# Runners that cannot call LiteLLM. A cloud choice is refused and the
# committed local model is kept. catalog-fit is not here: its caller
# already switches local Ollama vs the LiteLLM proxy.
RUNNER_TRANSPORT = {
    "eval-suite": "ollama",
    "matrix": "ollama",
    "decision-route": "ollama",
    "build-lane": "ollama",
}
# Alias env is read after PFY_MODEL_<TASK>. PFY_JEV_MODEL is not an alias:
# that variable is the TypeSafe / Laya id, owned by scripts/pfy_jev_230.py.
ALIAS_ENV = {
    "catalog-fit": "PFY_CATFIT_MODEL",
    "eval-suite": "EVAL_MODEL",
    "build-lane": "PFY_LOCAL_BUILD_MODEL",
}
COMPARE_TASKS = ("catalog-fit", "decision-route")
SUGGEST_CLOUD = ("grok-4.7", "gpt-6.1-sol")
REMIND_DAYS = 14
LOCK_STALE_S = 3600
DEFAULT_OLLAMA = "http://127.0.0.1:11434"
DEFAULT_LITELLM = "http://127.0.0.1:4000/v1"

# Tests inject this. Production leaves it None and uses HTTP.
# A cloud socket is refused while PFY_MODEL_NO_PAID=1 and this is None.
_TRANSPORT = None
# Tests inject a tokenizer: callable(text) -> (count, label). None uses the
# real order: litellm, else tiktoken, else chars/4.
_COUNTERS = None


class ModelCallError(Exception):
    """The model endpoint did not return text. No verdict."""


class UnknownModelPrice(Exception):
    """The model is not in data/model-prices.json."""


class PriceCoverageError(Exception):
    """The prompt is outside the priced context band."""


class StalePrice(Exception):
    """The price row is older than stale_after_days."""


class CompareBusy(Exception):
    """Another compare holds the lock."""


def repo_root(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env = (os.environ.get("PFY_ROOT") or "").strip()
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[1]


def env_name(task: str) -> str:
    return "PFY_MODEL_" + task.upper().replace("-", "_")


def user_config_path() -> Path:
    override = (os.environ.get("PFY_MODEL_CHOICE_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    xdg = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "pfy" / "model-choice.json"


def compare_state_path() -> Path:
    override = (os.environ.get("PFY_COMPARE_STATE_PATH") or "").strip()
    if override:
        return Path(override).expanduser()
    xdg = (os.environ.get("XDG_STATE_HOME") or "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "state"
    return base / "pfy" / "model-compare.json"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def committed_tasks(root: Path | None = None) -> dict:
    path = repo_root(root) / "config" / "model-choice.json"
    data = _load_json(path)
    tasks = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
    return tasks


def user_tasks() -> dict:
    data = _load_json(user_config_path())
    tasks = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
    return tasks


def parse_spec(text: str) -> tuple[str, str]:
    """backend, model. A bare name stays local. Only a cloud: prefix is cloud."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty model choice")
    if raw.startswith("cloud:"):
        model = raw[len("cloud:"):].strip()
        if not model:
            raise ValueError("cloud model missing")
        return "cloud", model
    if raw.startswith("local:"):
        model = raw[len("local:"):].strip()
        if not model:
            raise ValueError("local model missing")
        return "local", model
    return "local", raw


def _explicit_pair(raw: object) -> tuple[str, str] | None:
    if not isinstance(raw, dict):
        return None
    backend = str(raw.get("backend") or "").strip().lower()
    model = str(raw.get("model") or "").strip()
    if backend not in ("local", "cloud") or not model:
        return None
    return backend, model


def resolve(
    task: str,
    *,
    root: Path | None = None,
    local_tags: list[str] | None = None,
) -> tuple[str, str, str]:
    """Return (backend, model, source). Cloud only when explicitly configured.

    local_tags, when passed, may select the committed local fallback. An empty
    list means detection failed, so the preferred local model stays.
    """
    if task not in TASK_ORDER:
        raise ValueError("unknown task %s" % task)
    raw_defaults = committed_tasks(root).get(task)
    defaults = raw_defaults if isinstance(raw_defaults, dict) else {}
    fallback = str(defaults.get("fallback") or "").strip()
    backend, model, source = "local", str(defaults.get("model") or "").strip(), "default"
    if str(defaults.get("backend") or "local").strip().lower() == "cloud":
        # Committed file must not do this. Ignore a cloud default so a bad
        # edit cannot silently spend.
        backend = "local"
    stored = user_tasks().get(task)
    pair = _explicit_pair(stored if isinstance(stored, dict) else None)
    if pair:
        backend, model = pair
        source = "user"
    alias = ALIAS_ENV.get(task)
    if alias:
        raw_alias = (os.environ.get(alias) or "").strip()
        if raw_alias:
            backend, model = parse_spec(raw_alias)
            source = "alias"
    raw_env = (os.environ.get(env_name(task)) or "").strip()
    if raw_env:
        backend, model = parse_spec(raw_env)
        source = "env"
    if not model:
        model = str(defaults.get("model") or "").strip() or "qwen2.5:14b"
        if source == "default":
            backend = "local"
    if (
        backend == "local"
        and local_tags
        and model not in local_tags
        and fallback
        and fallback in local_tags
        and source == "default"
    ):
        model = fallback
        source = "fallback"
    return backend, model, source


def local_default(task: str, root: Path | None = None) -> str:
    """Committed local model for task. Cloud defaults in the file are ignored."""
    raw = committed_tasks(root).get(task)
    defaults = raw if isinstance(raw, dict) else {}
    model = str(defaults.get("model") or "").strip()
    return model or "qwen2.5:14b"


def _refuse_cloud(task: str, model: str, kept: str) -> None:
    print(
        "model-choice: %s is Ollama-only; cloud:%s refused; keeping %s"
        % (task, model, kept),
        file=sys.stderr,
    )


def runner_choice(
    task: str,
    *,
    explicit: str | None = None,
    transport: str | None = None,
    root: Path | None = None,
) -> tuple[str, str, str]:
    """(backend, model, source) a runner should use.

    explicit is the runner's own flag or env (EVAL_MODEL, --model,
    PFY_JEV_MODEL). It wins over PFY_MODEL_<TASK>, the saved choice, and
    the committed default. A cloud choice on an ollama transport prints
    one refusal line and returns the committed local model.
    """
    if task not in TASK_ORDER:
        raise ValueError("unknown task %s" % task)
    kind = transport or RUNNER_TRANSPORT.get(task) or "ollama"
    raw = (explicit or "").strip()
    if raw:
        backend, model = parse_spec(raw)
        source = "flag"
    else:
        backend, model, source = resolve(task, root=root)
    if backend == "cloud" and kind != "litellm":
        kept = local_default(task, root)
        _refuse_cloud(task, model, kept)
        return "local", kept, "refused-cloud"
    return backend, model, source


def save_task(task: str, backend: str, model: str) -> Path:
    if task not in TASK_ORDER:
        raise ValueError("unknown task %s" % task)
    if backend not in ("local", "cloud"):
        raise ValueError("backend must be local or cloud")
    if not model.strip():
        raise ValueError("model missing")
    if backend == "cloud" and not model.strip():
        raise ValueError("cloud model missing")
    path = user_config_path()
    data = _load_json(path)
    tasks = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
    tasks[task] = {"backend": backend, "model": model.strip()}
    payload = {"tasks": tasks}
    _atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def apply_assignment(text: str) -> tuple[str, str, str]:
    if "=" not in text:
        raise ValueError("model-choice must be task=backend:model")
    task, spec = text.split("=", 1)
    task = task.strip()
    backend, model = parse_spec(spec)
    save_task(task, backend, model)
    return task, backend, model


def litellm_config_path(root: Path | None = None) -> Path:
    raw = (os.environ.get("LITELLM_CONFIG") or "").strip()
    if raw:
        return Path(raw).expanduser()
    profile = (os.environ.get("DEPLOY_PROFILE") or "balanced").strip() or "balanced"
    root_path = repo_root(root)
    candidate = root_path / "config" / "litellm" / ("%s.yaml" % profile)
    if candidate.is_file():
        return candidate
    return root_path / "config" / "litellm" / "balanced.yaml"


def configured_cloud_models(root: Path | None = None) -> list[str]:
    """LiteLLM model_name values that are not Ollama routes. No secrets."""
    path = litellm_config_path(root)
    try:
        import yaml
    except ImportError:
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError):
        return []
    names: list[str] = []
    for row in data.get("model_list") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("model_name") or "").strip()
        params = row.get("litellm_params") if isinstance(row.get("litellm_params"), dict) else {}
        model = str(params.get("model") or "")
        if not name or model.startswith("ollama/"):
            continue
        names.append(name)
    return sorted(set(names))


def priced_cloud_models(root: Path | None = None) -> list[str]:
    table = load_prices(root)
    out = []
    for name in table.get("models") or {}:
        if name == "ollama:*" or name.startswith("ollama:"):
            continue
        out.append(name)
    return out


def cloud_options(root: Path | None = None) -> list[str]:
    seen: list[str] = []
    for name in list(priced_cloud_models(root)) + configured_cloud_models(root):
        if name not in seen:
            seen.append(name)
    return seen


def detect_local_models(host: str | None = None, timeout: float = 0.4) -> list[str]:
    """GET /api/tags. Any failure is an empty list. Does not pull."""
    base = (host or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA).strip() or DEFAULT_OLLAMA
    url = base.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError, TimeoutError):
        return []
    if not isinstance(data, dict):
        return []
    names = []
    for row in data.get("models") or []:
        if isinstance(row, dict) and row.get("name"):
            names.append(str(row["name"]))
    return names


def litellm_base() -> str:
    for key in ("LITELLM_BASE_URL", "LITELLM_PROXY_API_BASE"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return raw.rstrip("/")
    return DEFAULT_LITELLM


def ollama_host(host: str | None = None) -> str:
    raw = (host or os.environ.get("PFY_CATFIT_HOST") or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA).strip()
    return raw or DEFAULT_OLLAMA


def _paid_blocked() -> bool:
    return (os.environ.get("PFY_MODEL_NO_PAID") or "").strip() == "1"


def post_json(req: dict) -> dict:
    """POST JSON. req has backend, url, body. Secrets are not part of req."""
    backend = req.get("backend")
    if backend == "cloud" and _paid_blocked() and _TRANSPORT is None:
        raise ModelCallError("paid cloud call blocked")
    if _TRANSPORT is not None:
        data = _TRANSPORT(req)
        if not isinstance(data, dict):
            raise ModelCallError("transport did not return an object")
        return data
    headers = {"Content-Type": "application/json"}
    if backend == "cloud":
        # Name only. The value is not logged.
        key = (os.environ.get("LITELLM_MASTER_KEY") or "").strip()
        if key:
            headers["Authorization"] = "Bearer " + key
    body = json.dumps(req.get("body") or {}).encode("utf-8")
    request = urllib.request.Request(req["url"], data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ModelCallError("http %s" % exc.code) from exc
    except urllib.error.URLError as exc:
        label = "litellm unreachable" if backend == "cloud" else "ollama unreachable"
        raise ModelCallError(label) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        label = "litellm response is not json" if backend == "cloud" else "ollama response is not json"
        raise ModelCallError(label) from exc
    if not isinstance(data, dict):
        raise ModelCallError("response is not an object")
    return data


def _usage_pair(prompt: str, text: str, prompt_tokens: int, completion_tokens: int) -> dict:
    if prompt_tokens <= 0:
        prompt_tokens, _method = count_tokens(prompt)
    if completion_tokens <= 0 and text:
        completion_tokens, _method = count_tokens(text)
    return {
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
    }


def _missing_model(data: dict) -> bool:
    err = str(data.get("error") or "")
    return "not found" in err.lower() or "404" in err


def call_model(
    prompt: str,
    *,
    task: str = "catalog-fit",
    model: str | None = None,
    host: str | None = None,
    backend: str | None = None,
    root: Path | None = None,
) -> tuple[str, dict]:
    """Return (text, usage). Local is Ollama. Cloud is the LiteLLM proxy."""
    resolved_backend, resolved_model, _source = resolve(task, root=root)
    chosen_backend, chosen_model = resolved_backend, resolved_model
    if backend in ("local", "cloud"):
        chosen_backend = backend
    if model:
        if model.startswith("cloud:") or model.startswith("local:"):
            chosen_backend, chosen_model = parse_spec(model)
        elif model != resolved_model:
            chosen_model = model
            if backend not in ("local", "cloud"):
                chosen_backend = "local"
    if chosen_backend == "cloud":
        return _call_cloud(prompt, chosen_model)
    return _call_local(prompt, chosen_model, host=host, root=root, task=task)


def _call_cloud(prompt: str, model: str) -> tuple[str, dict]:
    base = litellm_base()
    url = base if base.endswith("/chat/completions") else base.rstrip("/") + "/chat/completions"
    data = post_json({
        "backend": "cloud",
        "url": url,
        "body": {
            "model": model,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
    })
    if data.get("error"):
        raise ModelCallError("litellm response missing")
    choices = data.get("choices") or []
    message = (choices[0].get("message") or {}) if choices and isinstance(choices[0], dict) else {}
    text = message.get("content") if isinstance(message, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise ModelCallError("litellm response missing")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return text, _usage_pair(
        prompt,
        text,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
    )


def _call_local(prompt: str, model: str, *, host: str | None, root: Path | None, task: str) -> tuple[str, dict]:
    url = ollama_host(host).rstrip("/") + "/api/generate"
    data = post_json({
        "backend": "local",
        "url": url,
        "body": {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0},
        },
    })
    if _missing_model(data):
        defaults = committed_tasks(root).get(task) or {}
        fallback = str(defaults.get("fallback") or "").strip() if isinstance(defaults, dict) else ""
        if fallback and fallback != model:
            return _call_local(prompt, fallback, host=host, root=root, task=task)
        raise ModelCallError(str(data.get("error") or "ollama model missing"))
    text = data.get("response") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise ModelCallError("ollama response missing")
    return text, _usage_pair(
        prompt,
        text,
        int(data.get("prompt_eval_count") or 0),
        int(data.get("eval_count") or 0),
    )


def _venv_root() -> Path | None:
    raw = (os.environ.get("PFY_VENV") or "").strip()
    if raw:
        return Path(raw).expanduser()
    candidate = repo_root() / ".venv"
    if candidate.is_dir():
        return candidate
    return None


def _add_venv_site() -> list[str]:
    """Put <venv>/lib/python*/site-packages on sys.path. Tokenizer imports only."""
    root = _venv_root()
    if root is None:
        return []
    lib = root / "lib"
    if not lib.is_dir():
        return []
    added: list[str] = []
    for site in sorted(lib.glob("python*/site-packages")):
        if not site.is_dir():
            continue
        text = str(site)
        if text not in sys.path:
            sys.path.insert(0, text)
            added.append(text)
    if added:
        cache = root / "tiktoken-cache"
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(cache))
    return added


def _import_mod(name: str):
    """Import name. On failure, add the tokenizer venv and try once more."""
    try:
        return importlib.import_module(name)
    except Exception:
        if not _add_venv_site():
            raise
        return importlib.import_module(name)


def _count_litellm(text: str) -> tuple[int, str]:
    mod = _import_mod("litellm")
    return int(mod.token_counter(model="gpt-4o", text=text)), "litellm"


def _count_tiktoken(text: str) -> tuple[int, str]:
    mod = _import_mod("tiktoken")
    enc = mod.get_encoding("o200k_base")
    return len(enc.encode(text)), "tiktoken o200k_base"


def count_tokens(text: str) -> tuple[int, str]:
    """litellm.token_counter, else tiktoken o200k_base, else chars/4.

    The label is litellm, tiktoken o200k_base, or approx. Empty text is
    (0, exact) and does not import a tokenizer. tiktoken's BPE file is a
    read-only fetch; TIKTOKEN_CACHE_DIR is the venv cache when that venv
    supplied the package. tiktoken is an approximation for non-OpenAI
    tokenizers, including xAI.
    """
    raw = text or ""
    if not raw:
        return 0, "exact"
    if _COUNTERS is not None:
        return _COUNTERS(raw)
    for counter in (_count_litellm, _count_tiktoken):
        try:
            return counter(raw)
        except Exception:
            continue
    return (len(raw) + 3) // 4, "approx"


def load_prices(root: Path | None = None) -> dict:
    path = repo_root(root) / "data" / "model-prices.json"
    data = _load_json(path)
    if not data.get("models"):
        raise UnknownModelPrice("price table missing")
    return data


def _price_row(model: str, root: Path | None = None) -> dict:
    table = load_prices(root)
    models = table.get("models") or {}
    if model in models and isinstance(models[model], dict):
        return models[model]
    if ":" in model and isinstance(models.get("ollama:*"), dict):
        return models["ollama:*"]
    raise UnknownModelPrice("no price for %r" % model)


def short_source(url: str) -> str:
    text = (url or "").strip()
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def quote(model: str, prompt_tokens: int, completion_tokens: int, *, root: Path | None = None) -> dict:
    row = _price_row(model, root)
    pin = Decimal(str(row.get("in")))
    pout = Decimal(str(row.get("out")))
    band = "standard"
    long_row = row.get("long_context") if isinstance(row.get("long_context"), dict) else None
    if long_row and prompt_tokens >= int(long_row.get("min_prompt_tokens") or 0):
        pin = Decimal(str(long_row.get("in")))
        pout = Decimal(str(long_row.get("out")))
        band = "long"
    cap = row.get("short_context_max_input_tokens")
    if cap is not None and prompt_tokens > int(cap):
        raise PriceCoverageError(
            "no short-context price for %s at %s input tokens" % (model, prompt_tokens)
        )
    cost = (Decimal(prompt_tokens) * pin + Decimal(completion_tokens) * pout) / Decimal(1000000)
    cost_q = cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    fetched = str(row.get("fetched") or "")
    return {
        "model": model,
        "provider": str(row.get("provider") or ""),
        "source": str(row.get("source") or ""),
        "source_short": short_source(str(row.get("source") or "")),
        "fetched": fetched,
        "price_in": float(pin),
        "price_out": float(pout),
        "band": band,
        "cost_usd": float(cost_q),
        "cost_text": f"{cost_q:.4f}",
        "stale_after_days": int(load_prices(root).get("stale_after_days") or 45),
    }


def price_age_days(fetched: str, today: date | None = None) -> int:
    stamp = date.fromisoformat(fetched)
    day = today or datetime.now(timezone.utc).date()
    return (day - stamp).days


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def gui_document(*, root: Path | None = None, probe: bool = False, local_tags: list[str] | None = None) -> dict:
    tags = list(local_tags) if local_tags is not None else (detect_local_models() if probe else [])
    clouds = cloud_options(root)
    rows = []
    for task in TASK_ORDER:
        backend, model, source = resolve(task, root=root, local_tags=tags or None)
        defaults = committed_tasks(root).get(task) or {}
        local_names = []
        for name in [model if backend == "local" else str(defaults.get("model") or ""), str(defaults.get("fallback") or "")] + tags:
            if name and name not in local_names:
                local_names.append(name)
        cloud_model = model if backend == "cloud" else (clouds[0] if clouds else "")
        rows.append({
            "task": task,
            "backend": backend,
            "model": model,
            "source": source,
            "local_spec": "local:" + (model if backend == "local" else (local_names[0] if local_names else model)),
            "cloud_spec": ("cloud:" + cloud_model) if cloud_model else "",
            "local_options": local_names,
            "cloud_options": clouds,
        })
    return {"tasks": rows, "html": render_html(rows), "compare_task": "catalog-fit"}


def render_html(rows: list[dict]) -> str:
    parts = []
    for row in rows:
        task = row["task"]
        selected = "%s:%s" % (row["backend"], row["model"])
        options = []
        for name in row["local_options"]:
            value = "local:" + name
            mark = " selected" if value == selected else ""
            options.append('<option value="%s"%s>%s</option>' % (_esc(value), mark, _esc(name)))
        for name in row["cloud_options"]:
            value = "cloud:" + name
            mark = " selected" if value == selected else ""
            options.append('<option value="%s"%s>%s</option>' % (_esc(value), mark, _esc(name)))
        local_on = " primary" if row["backend"] == "local" else ""
        cloud_on = " primary" if row["backend"] == "cloud" else ""
        parts.append(
            '<div class=row data-task="%s"><b>%s</b> '
            '<button type=button class="task-backend%s" data-task="%s" data-spec="%s">local</button> '
            '<button type=button class="task-backend%s" data-task="%s" data-spec="%s">cloud</button> '
            '<select class=task-model data-task="%s">%s</select> '
            '<span class=muted>%s</span></div>'
            % (
                _esc(task), _esc(task),
                local_on, _esc(task), _esc(row["local_spec"]),
                cloud_on, _esc(task), _esc(row["cloud_spec"]),
                _esc(task), "".join(options), _esc(row["source"]),
            )
        )
    return "\n".join(parts)


def task_lines(*, root: Path | None = None, local_tags: list[str] | None = None) -> list[str]:
    doc = gui_document(root=root, local_tags=local_tags, probe=False)
    lines = ["TASK MODELS", "  why       per-task local or cloud. Cloud only when you set it."]
    for row in doc["tasks"]:
        lines.append("  %-16s %-6s %s" % (row["task"], row["backend"], row["model"]))
    lines.append("  compare   Compare last local catalog-fit run")
    return lines


def show_text(*, root: Path | None = None) -> str:
    lines = []
    for task in TASK_ORDER:
        backend, model, source = resolve(task, root=root)
        lines.append("%-16s %-6s %-22s %s" % (task, backend, model, source))
    return "\n".join(lines)


def setup_from_args(args) -> int | None:
    """Apply --model-choice, or prompt when the setup step asked.

    None when this invocation is not a model-choice step. A spec without
    --yes and without a TTY prints needs_confirmation and writes nothing.
    Bare `./pfy setup` asks via `model-choice prompt`. Catalog install flags
    do not prompt by themselves.
    """
    specs = list(getattr(args, "model_choice", None) or [])
    yes = bool(getattr(args, "yes", False))
    asked = bool(getattr(args, "model_choice_prompt", False))
    tty = sys_isatty()
    if not specs and not asked:
        return None
    if specs and not yes and not tty:
        print("needs_confirmation")
        return 1
    if specs:
        for spec in specs:
            task, backend, model = apply_assignment(spec)
            print("model-choice %s %s:%s" % (task, backend, model))
        if yes or not asked:
            return 0
    if asked and not yes:
        _prompt(root=getattr(args, "root", None))
    return 0


def sys_isatty() -> bool:
    import sys
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _prompt(*, root: Path | None) -> None:
    tags = detect_local_models()
    clouds = cloud_options(root)
    local_txt = ", ".join(tags) if tags else "(none detected)"
    cloud_txt = ", ".join(clouds) if clouds else "(none in LiteLLM config)"
    print("model choice. Enter keeps the current row.")
    print("local models: %s" % local_txt)
    print("cloud models: %s" % cloud_txt)
    for task in TASK_ORDER:
        backend, model, source = resolve(task, root=root, local_tags=tags or None)
        print("%s [%s:%s] (%s)" % (task, backend, model, source))
        try:
            line = input("  choice> ").strip()
        except EOFError:
            line = ""
        if not line:
            continue
        chosen_backend, chosen_model = parse_spec(line)
        save_task(task, chosen_backend, chosen_model)
        print("model-choice %s %s:%s" % (task, chosen_backend, chosen_model))


def _fit():
    import sys
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts import catalog_fit_triage as fit
    return fit


def catalog_fit_cases(root: Path, run: str | None, last: bool) -> list[dict]:
    fit = _fit()
    gate = fit.load_gate(root)
    run_dir = _run_dir(root, run, last)
    files = {}
    if run_dir is not None:
        for path in sorted(run_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and isinstance(data.get("slug"), str):
                files[data["slug"]] = (data, path.read_text(encoding="utf-8"))
    cases = []
    chosen = []
    golden_slugs = set()
    for case in gate["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("slug"), str):
            continue
        golden_slugs.add(case["slug"])
        if files and case["slug"] not in files:
            continue
        chosen.append(case)
    # A real triage batch (eval/catalog-fit/) mostly holds non-golden slugs.
    # Replay those from their stage card; they have no golden label.
    for slug in sorted(files):
        if slug in golden_slugs:
            continue
        card_rel = "data/stages/%s.json" % slug
        if (root / card_rel).is_file():
            chosen.append({"id": slug, "slug": slug, "card": card_rel})
    for case in chosen:
        slug = case["slug"]
        subject = fit.subject_for_case(root, case)
        prompt = fit.build_prompt(slug, subject, gate)
        golden = case.get("label") if isinstance(case.get("label"), str) else None
        if slug in files:
            stored, text = files[slug]
            local = stored.get("verdict") if isinstance(stored.get("verdict"), str) else None
            origin = "run"
        else:
            local = golden
            text = json.dumps({
                "slug": slug,
                "fit": local == "fit",
                "overlap_with": None,
                "verdict": local,
                "reason": "golden",
                "confidence": 0.9,
            })
            origin = "golden"
        cases.append({
            "id": case.get("id") or slug,
            "slug": slug,
            "prompt": prompt,
            "local": local,
            "golden": golden,
            "completion_text": text,
            "origin": origin,
        })
    return cases


def _run_dir(root: Path, run: str | None, last: bool) -> Path | None:
    if run:
        path = Path(run)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.is_dir():
            return path
        if path.is_file():
            return path.parent
    if last or not run:
        batch = root / "eval" / "catalog-fit"
        if batch.is_dir() and any(batch.glob("*.json")):
            return batch
    return None


def format_estimate_line(est: dict) -> str:
    label = est.get("token_method") or "approx"
    return (
        "Compare %s (%s cases) on %s: ~%s input + ~%s output tokens (%s) = $%s "
        "(%s price $%.2f/$%.2f per 1M, %s, fetched %s). Run it? [y/N]"
        % (
            est["task"],
            est["cases"],
            est["model"],
            f"{est['prompt_tokens']:,}",
            f"{est['completion_tokens']:,}",
            label,
            est["cost_text"],
            est["provider"],
            est["price_in"],
            est["price_out"],
            est["source_short"],
            est["fetched"],
        )
    )


def _fold_method(current: str, piece: str) -> str:
    if piece == "approx" or current == "approx":
        return "approx"
    if piece and piece != "exact":
        return piece
    return current


def _require_compare_task(task: str) -> None:
    if task == "eval-lane":
        raise ValueError(
            "eval-lane is not replayable: stored files are probe verdicts, not the prompts the lane sent"
        )
    if task not in COMPARE_TASKS:
        raise ValueError("compare supports catalog-fit and decision-route")


def estimate_task(
    task: str,
    *,
    against: str,
    root: Path | None = None,
    run: str | None = None,
    last: bool = True,
    today: date | None = None,
) -> dict:
    _require_compare_task(task)
    root_path = repo_root(root)
    cases = _compare_cases(task, root_path, run, last)
    if not cases:
        raise ValueError("%s has no cases" % task)
    prompt_tokens = 0
    completion_tokens = 0
    method = "exact"
    for case in cases:
        p_tokens, p_method = count_tokens(case["prompt"])
        c_tokens, c_method = count_tokens(case["completion_text"])
        prompt_tokens += p_tokens
        completion_tokens += c_tokens
        method = _fold_method(method, p_method)
        method = _fold_method(method, c_method)
    priced = quote(against, prompt_tokens, completion_tokens, root=root_path)
    stale_days = price_age_days(priced["fetched"], today)
    stale = stale_days > int(priced["stale_after_days"])
    est = {
        "task": task,
        "model": against,
        "cases": len(cases),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "token_method": method,
        "provider": priced["provider"],
        "price_in": priced["price_in"],
        "price_out": priced["price_out"],
        "source": priced["source"],
        "source_short": priced["source_short"],
        "fetched": priced["fetched"],
        "cost_usd": priced["cost_usd"],
        "cost_text": priced["cost_text"],
        "stale": stale,
        "age_days": stale_days,
    }
    est["line"] = format_estimate_line(est)
    return est


def estimate_catalog_fit(
    *,
    against: str,
    root: Path | None = None,
    run: str | None = None,
    last: bool = True,
    today: date | None = None,
) -> dict:
    return estimate_task(
        "catalog-fit", against=against, root=root, run=run, last=last, today=today,
    )


def _confirm(
    *,
    yes: bool,
    max_usd: float | None,
    cost: float,
    cost_text: str,
    isatty: bool,
    answer: str | None,
    stale: bool,
    accept_stale: bool,
) -> str | None:
    """None when the run may proceed. Otherwise a block reason."""
    if stale and not accept_stale:
        return "stale price"
    if yes:
        if max_usd is None:
            return "--yes requires --max-usd"
        cap = Decimal(str(max_usd)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if Decimal(cost_text) > cap:
            return "estimate $%s exceeds --max-usd %s" % (cost_text, max_usd)
        return None
    if not isatty:
        return "no TTY"
    if (answer or "").strip().lower() not in ("y", "yes"):
        return "declined"
    return None


def _lock_path() -> Path:
    return compare_state_path().with_name("compare.lock")


def _acquire_lock() -> Path:
    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(path, flags, 0o644)
    except FileExistsError:
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            age = 0
        if age <= LOCK_STALE_S:
            raise CompareBusy("compare already running")
        try:
            path.unlink()
        except OSError as exc:
            raise CompareBusy("compare already running") from exc
        fd = os.open(path, flags, 0o644)
    os.write(fd, str(os.getpid()).encode("utf-8"))
    os.close(fd)
    return path


def _release_lock(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _record_compare(task: str, against: str) -> None:
    path = compare_state_path()
    data = _load_json(path)
    tasks = data.get("tasks") if isinstance(data.get("tasks"), dict) else {}
    tasks[task] = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "against": against,
    }
    _atomic_write(path, json.dumps({"tasks": tasks}, indent=2, sort_keys=True) + "\n")


def _verdict_of(text: str, slug: str) -> str | None:
    fit = _fit()
    payload, _problem = fit.parse_model(text, slug)
    if not payload:
        return None
    verdict = payload.get("verdict")
    return verdict if isinstance(verdict, str) else None


def _parse_catalog_fit(text: str, case: dict) -> str | None:
    return _verdict_of(text, str(case.get("slug") or ""))


_DECISION_REPLY = (
    "Reply with one JSON object and no other text:\n"
    '{"choice":"<criteria key>","confidence":0.0,"why":"one short reason"}\n'
    "Pick exactly one criteria key. Use a confidence below 0.85 when the state does not settle the choice.\n"
)


def _decision_rules() -> str:
    """Same procedure text the Laya trial gives the executor. No network."""
    path = repo_root() / "examples" / "typed-decisions-local" / "trial.py"
    spec = importlib.util.spec_from_file_location("pfy_decision_prompt", path)
    if spec is None or spec.loader is None:
        raise ImportError("trial.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return str(mod.decision_prompt()).strip()


def _jev():
    root = str(repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts import pfy_jev_230 as jev
    return jev


def decision_prompt_for_case(case: dict, rules: str) -> str:
    """User message for one labeled Choice.

    Live decide_choice is token overlap, not a chat call. typesafe_evaluate
    posts state plus questions. Compare renders those fields, plus the trial
    procedure, as this message. The label is not included.
    """
    case_id = case.get("id")
    instructions = case.get("instructions") or ""
    state = case.get("state")
    criteria = case.get("criteria") if isinstance(case.get("criteria"), dict) else {}
    payload = {
        "id": case_id,
        "instructions": instructions,
        "state": state,
        "criteria": criteria,
        "questions": {
            str(case_id): {
                "type": "choice",
                "instructions": instructions,
                "criteria": criteria,
            }
        },
    }
    body = json.dumps(payload, indent=2, sort_keys=True)
    return rules.strip() + "\n\n" + _DECISION_REPLY + "\nCASE_JSON:\n" + body


def parse_decision_choice(text: str, case: dict) -> str | None:
    """A JSON choice that is one of the criteria keys. Anything else is None."""
    keys = case.get("keys")
    if not isinstance(keys, (list, tuple, set)):
        criteria = case.get("criteria") if isinstance(case.get("criteria"), dict) else {}
        keys = list(criteria.keys())
    allowed = {str(key) for key in keys}
    found = _choice_in(text, allowed)
    return found


def _choice_in(text: str, allowed: set[str]) -> str | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    blobs: list[object] = []
    try:
        blobs.append(json.loads(raw))
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                blobs.append(json.loads(raw[start:end + 1]))
            except json.JSONDecodeError:
                return None
    for blob in blobs:
        got = _walk_choice(blob, allowed)
        if got:
            return got
    return None


def _walk_choice(blob: object, allowed: set[str]) -> str | None:
    if isinstance(blob, dict):
        choice = blob.get("choice")
        if isinstance(choice, str) and choice in allowed:
            return choice
        for value in blob.values():
            got = _walk_choice(value, allowed)
            if got:
                return got
    elif isinstance(blob, list):
        for item in blob:
            got = _walk_choice(item, allowed)
            if got:
                return got
    return None


def decision_route_cases(root: Path, run: str | None, last: bool) -> list[dict]:
    """Labeled Jev Choice set. run and last are ignored: this is not a stored batch.

    Local verdict is decide_choice (no model call). Completion text for the
    estimate is that local choice as JSON.
    """
    del run, last
    path = Path(root) / "data" / "decision-gates" / "laya-trial.cases.v0.json"
    data = _load_json(path)
    rows = data.get("cases") if isinstance(data.get("cases"), list) else []
    rules = _decision_rules()
    jev = _jev()
    cases = []
    for case in rows:
        if not isinstance(case, dict) or not case.get("id"):
            continue
        criteria = case.get("criteria") if isinstance(case.get("criteria"), dict) else {}
        if not criteria:
            continue
        instructions = str(case.get("instructions") or "")
        rec = jev.decide_choice(case.get("state"), criteria, instructions=instructions)
        local = rec.get("choice") if isinstance(rec, dict) else None
        if not isinstance(local, str):
            local = None
        golden = case.get("label") if isinstance(case.get("label"), str) else None
        completion = json.dumps(
            {
                "choice": local,
                "confidence": rec.get("confidence") if isinstance(rec, dict) else None,
                "why": "local",
            },
            sort_keys=True,
        )
        packed = {
            "id": case["id"],
            "instructions": instructions,
            "state": case.get("state"),
            "criteria": criteria,
            "keys": list(criteria.keys()),
        }
        cases.append({
            "id": case["id"],
            "slug": case["id"],
            "prompt": decision_prompt_for_case(packed, rules),
            "local": local,
            "golden": golden,
            "completion_text": completion,
            "origin": "labeled",
            "keys": list(criteria.keys()),
        })
    return cases


def _compare_cases(task: str, root: Path, run: str | None, last: bool) -> list[dict]:
    if task == "catalog-fit":
        return catalog_fit_cases(root, run, last)
    if task == "decision-route":
        return decision_route_cases(root, run, last)
    raise ValueError("compare supports catalog-fit and decision-route")


def _compare_parse(task: str, text: str, case: dict) -> str | None:
    if task == "catalog-fit":
        return _parse_catalog_fit(text, case)
    if task == "decision-route":
        return parse_decision_choice(text, case)
    raise ValueError("compare supports catalog-fit and decision-route")


def run_compare(
    task: str,
    *,
    against: str,
    run: str | None = None,
    last: bool = True,
    yes: bool = False,
    max_usd: float | None = None,
    accept_stale: bool = False,
    out: str | None = None,
    root: Path | None = None,
    today: date | None = None,
    isatty: bool | None = None,
    answer: str | None = None,
    input_fn=None,
) -> dict:
    _require_compare_task(task)
    root_path = repo_root(root)
    est = estimate_task(task, against=against, root=root_path, run=run, last=last, today=today)
    print(est["line"])
    stale_note = ""
    if est["stale"]:
        stale_note = (
            "Price for %s was fetched %s (older than %s days). Pass --accept-stale-price to continue."
            % (against, est["fetched"], 45)
        )
        print(stale_note)
    shown = est["line"] if not stale_note else est["line"] + " " + stale_note
    tty = sys_isatty() if isatty is None else isatty
    if tty and not yes and answer is None and input_fn is not None:
        answer = input_fn("")
    elif tty and not yes and answer is None and isatty is None:
        try:
            answer = input("").strip()
        except EOFError:
            answer = ""
    block = _confirm(
        yes=yes,
        max_usd=max_usd,
        cost=est["cost_usd"],
        cost_text=est["cost_text"],
        isatty=tty,
        answer=answer,
        stale=bool(est["stale"]),
        accept_stale=accept_stale,
    )
    result = {
        "ok": block in (None, "declined"),
        "ran": False,
        "blocked": block,
        "needs_confirm": block == "no TTY",
        "line": shown,
        "cost_usd": est["cost_usd"],
        "estimate": est,
        "task": task,
        "against": against,
    }
    if block:
        if block not in ("declined",):
            result["ok"] = False
            print(block)
        else:
            print("not run")
        return result
    lock = _acquire_lock()
    try:
        cases = _compare_cases(task, root_path, run, last)
        rows = []
        prompt_tokens = 0
        completion_tokens = 0
        for case in cases:
            text, usage = call_model(case["prompt"], task=task, model="cloud:" + against, root=root_path)
            prompt_tokens += int(usage["prompt_tokens"])
            completion_tokens += int(usage["completion_tokens"])
            cloud = _compare_parse(task, text, case)
            local = case["local"]
            golden = case["golden"]
            rows.append({
                "id": case["id"],
                "slug": case["slug"],
                "local": local,
                "cloud": cloud,
                "golden": golden,
                "agree": local == cloud,
                "local_source": case["origin"],
                "match_golden_local": (local == golden) if golden else None,
                "match_golden_cloud": (cloud == golden) if golden else None,
            })
        actual = quote(against, prompt_tokens, completion_tokens, root=root_path)
        payload = {
            "against": against,
            "cases": rows,
            "cost_usd": actual["cost_usd"],
            "estimate": {k: est[k] for k in est if k != "line"},
            "ran": True,
            "task": task,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        }
        dest = _out_path(out, task)
        _atomic_write(dest, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        _record_compare(task, against)
        print("wrote %s" % dest)
        result.update({
            "ok": True,
            "ran": True,
            "blocked": None,
            "out": str(dest),
            "usage": payload["usage"],
            "cost_usd": actual["cost_usd"],
            "cases": rows,
        })
        return result
    finally:
        _release_lock(lock)


def _out_path(out: str | None, task: str) -> Path:
    if out:
        path = Path(out)
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.suffix != ".json":
            path.mkdir(parents=True, exist_ok=True)
            return path / ("compare-%s.json" % task)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    dest = repo_root() / "tmp" / ("compare-%s.json" % task)
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def latest_local_run(root: Path | None = None) -> Path | None:
    batch = repo_root(root) / "eval" / "catalog-fit"
    if not batch.is_dir():
        return None
    files = [p for p in batch.glob("*.json") if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def reminder_line(
    task: str = "catalog-fit",
    *,
    root: Path | None = None,
    now: datetime | None = None,
    days: int | None = None,
) -> str | None:
    """One offer line, or None. Does not call a model."""
    # The reminder stays on catalog-fit. Other compare tasks do not offer.
    if task != "catalog-fit":
        return None
    latest = latest_local_run(root)
    if latest is None:
        return None
    state = _load_json(compare_state_path())
    tasks = state.get("tasks") if isinstance(state.get("tasks"), dict) else {}
    last = tasks.get(task) if isinstance(tasks.get(task), dict) else {}
    stamp = str(last.get("at") or "")
    moment = now or datetime.now(timezone.utc)
    window = REMIND_DAYS if days is None else days
    raw_days = (os.environ.get("PFY_COMPARE_REMIND_DAYS") or "").strip()
    if days is None and raw_days:
        try:
            window = int(raw_days)
        except ValueError:
            window = REMIND_DAYS
    if stamp:
        try:
            compared = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            compared = None
        if compared is not None and (moment - compared).days < window:
            return None
        if compared is not None and latest.stat().st_mtime <= compared.timestamp():
            return None
    against = SUGGEST_CLOUD[0]
    try:
        est = estimate_catalog_fit(against=against, root=root, last=True)
    except (UnknownModelPrice, PriceCoverageError, ValueError):
        return None
    cents = Decimal(str(est["cost_usd"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    names = ", ".join(SUGGEST_CLOUD)
    return (
        "It will cost ~$%s to check your last local %s run with %s: ./pfy compare %s --against %s"
        % (f"{cents:.2f}", task, names, task, against)
    )


def print_compare_reminder() -> None:
    try:
        line = reminder_line()
    except (OSError, UnknownModelPrice, PriceCoverageError, ValueError):
        return
    if line:
        print(line)


def gui_set(body: dict, *, root: Path | None = None) -> dict:
    task = str((body or {}).get("task") or "").strip()
    spec = str((body or {}).get("spec") or "").strip()
    if not spec and body.get("backend") and body.get("model"):
        spec = "%s:%s" % (body.get("backend"), body.get("model"))
    try:
        if "=" in spec and spec.split("=", 1)[0] in TASK_ORDER:
            task, backend, model = apply_assignment(spec)
        else:
            backend, model = parse_spec(spec)
            if task not in TASK_ORDER:
                raise ValueError("unknown task %s" % task)
            if backend == "cloud" and not model:
                raise ValueError("cloud model missing")
            save_task(task, backend, model)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    doc = gui_document(root=root, probe=False)
    return {"ok": True, "task": task, "backend": backend, "model": model, "html": doc["html"], "tasks": doc["tasks"]}


def gui_compare(body: dict, *, root: Path | None = None) -> dict:
    """Same gate as the CLI. confirm is the explicit yes. max_usd is required to run."""
    task = str((body or {}).get("task") or "catalog-fit")
    against = str((body or {}).get("against") or SUGGEST_CLOUD[0])
    confirm = (body or {}).get("confirm") in (True, "yes", "y", "true", 1)
    max_usd = (body or {}).get("max_usd")
    if max_usd is not None:
        try:
            max_usd = float(max_usd)
        except (TypeError, ValueError):
            return {"ok": False, "ran": False, "error": "bad max_usd"}
    try:
        return run_compare(
            task,
            against=against,
            last=True,
            yes=confirm,
            max_usd=max_usd if confirm else None,
            isatty=False,
            root=root,
        )
    except UnknownModelPrice as exc:
        return {"ok": False, "ran": False, "error": "UnknownModelPrice: %s" % exc}
    except (PriceCoverageError, CompareBusy, ValueError, ModelCallError) as exc:
        return {"ok": False, "ran": False, "error": str(exc)}


def main(argv: list[str] | None = None) -> int:
    """`python3 -m pfylib.model_choice resolve <task> --field model|backend|spec`."""
    import argparse

    parser = argparse.ArgumentParser(prog="pfylib.model_choice")
    sub = parser.add_subparsers(dest="cmd", required=True)
    res = sub.add_parser("resolve", help="print the model a runner should use")
    res.add_argument("task")
    res.add_argument("--field", choices=("model", "backend", "spec"), default="model")
    res.add_argument("--transport", choices=("ollama", "litellm"), default="")
    res.add_argument("--explicit", default="", help="runner flag or env value; wins over resolve()")
    args = parser.parse_args(argv)
    transport = args.transport or None
    explicit = args.explicit or None
    if transport or explicit:
        backend, model, _source = runner_choice(
            args.task, explicit=explicit, transport=transport or "ollama",
        )
    else:
        backend, model, _source = resolve(args.task)
    if args.field == "backend":
        print(backend)
    elif args.field == "spec":
        print("%s:%s" % (backend, model))
    else:
        print(model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
