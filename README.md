# Code-Helper

> **Autonomous Code Generation & Verification Platform (Phase 1)**
>
> An autonomous software execution environment that converts natural-language specifications into tested, reproducible program artifacts.

---

## Architecture Overview (Phase 1)

Phase 1 establishes the foundational autonomous Python execution loop:

```text
User Prompt
    │
    ▼
┌──────────────┐
│   Planner    │ ───► TaskSpecification (JSON)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Coder     │ ───► main.py
└──────┬───────┘
       │
       ▼
┌───────────────────┐
│ Deterministic     │
│ Syntax Validator  │
└──────┬────────────┘
       │
       ▼
┌───────────────────┐
│ Execution Sandbox │ ───► Runs main.py in isolated workspace/ws_<uuid>
└──────┬────────────┘
       │
       ├────────────── Pass ──────────────► VERIFIED
       │
     Fail
       │
       ▼
┌──────────────┐
│   Debugger   │ ───► Patches main.py using tracebacks & attempt history
└──────┬───────┘
       │
       └──────────────► Retry loop (Max 5 attempts)
```

---

## Core Invariants

1. **Deterministic Execution:** The LLM makes decisions; deterministic services execute, test, inspect, and isolate.
2. **Sandbox Isolation:** Scripts run inside ephemeral workspaces under `workspaces/ws_<uuid>/` with sanitized environments.
3. **Execution Limits:** 30-second default timeout; max 5 retry attempts.
4. **Deterministic Syntax Checks:** Fast syntax compilation (`compile()`) verifies code integrity prior to process invocation.
5. **Auditable Attempt History:** Every single attempt, error message, traceback, and patch summary is recorded.
6. **Model-Agnostic LLM Provider:** Clean `LLMProvider` protocol defaulting to local `qwen2.5-coder:1.5b` via Ollama.

---

## Directory Structure

```text
Code-Helper/
├── PDA.md                   # Product Definition Architecture
├── TDA.md                   # Technical Design & Architecture
├── README.md                # Project documentation
├── requirements.txt         # Core dependencies
├── app.py                   # Streamlit UI
├── config/
│   ├── __init__.py
│   └── settings.py          # App configuration
├── domain/
│   ├── __init__.py
│   ├── enums.py             # RunStatus, ErrorType, ExecutionMode
│   └── models.py            # TaskSpecification, Attempt, ExecutionResult, RunResult
├── llm/
│   ├── __init__.py
│   ├── base.py              # LLMProvider protocol
│   └── ollama.py            # OllamaProvider implementation
├── workspace/
│   ├── __init__.py
│   └── manager.py           # WorkspaceManager for ephemeral run directories
├── execution/
│   ├── __init__.py
│   ├── timeout.py           # Timeout enforcement & exceptions
│   ├── process.py           # Subprocess runner with timing & output capture
│   └── sandbox.py           # ExecutionSandbox
├── agent/
│   ├── __init__.py
│   ├── planner.py           # Task planner
│   ├── coder.py             # Python script generator
│   ├── debugger.py          # Traceback-driven self-repair agent
│   └── orchestrator.py      # Finite State Machine orchestrator
├── prompts/
│   ├── planner.txt          # Structured JSON planning prompt
│   ├── coder.txt            # Python script generation prompt
│   └── debugger.txt         # Targeted debugging and repair prompt
└── tests/
    ├── __init__.py
    ├── test_models.py       # Domain models test suite
    ├── test_execution.py    # Sandbox and timeout test suite
    └── test_orchestrator.py # Self-healing retry loop test suite
```

---

## Getting Started

### Prerequisites

- Python 3.10+ (tested on Python 3.14)
- [Ollama](https://ollama.com/) with `qwen2.5-coder:1.5b`:
  ```bash
  ollama run qwen2.5-coder:1.5b
  ```

### Installation

```bash
git clone https://github.com/Siddhardha231/Code-Helper.git
cd Code-Helper
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### Running the Test Suite

```bash
pytest -v
```

### Launching the Streamlit Application

```bash
streamlit run app.py
```
