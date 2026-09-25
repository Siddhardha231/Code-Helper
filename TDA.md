# TDA — Autonomous Code Generation & Verification Platform

> This TDA is derived from the supplied PDA, including its architecture, phase roadmap, safety constraints, state machine, and implementation notes. The PDA defines the product as an autonomous software execution environment that converts natural-language specifications into tested, reproducible artifacts.

> **Technical Design & Architecture**
>
> **Product Definition:** An autonomous software execution environment that converts natural-language specifications into tested, reproducible program artifacts.

**Version:** 1.0  
**Status:** Implementation Design  
**Source:** PDA v1.0 supplied for this project  
**Initial Model:** `qwen2.5-coder:1.5b` via Ollama  
**UI:** Streamlit  
**Primary Language:** Python  
**Architecture Goal:** Model-agnostic, language-agnostic, sandboxed, reproducible

---

## 1. Purpose

This TDA translates the project's Product Design Architecture (PDA) into an implementation-level design.

The system accepts a natural-language programming task and autonomously:

1. Interprets the task.
2. Produces a structured task specification.
3. Selects a language and execution mode.
4. Generates source code.
5. Detects and resolves dependencies.
6. Creates an isolated execution environment.
7. Executes the generated program.
8. Generates or accepts tests.
9. Runs tests.
10. Classifies failures.
11. Repairs code or environment.
12. Repeats within bounded retry limits.
13. Produces verified artifacts and a complete execution history.

The core invariant is:

> **The LLM makes decisions; deterministic services execute, test, install, and inspect.**

The system must never equate process exit success with program correctness.

---

# 45. Python Phase 1 Implementation

Initial directory:

```text
auto-code-agent/
├── app.py
├── agent/
│   ├── planner.py
│   ├── coder.py
│   ├── debugger.py
│   └── orchestrator.py
├── execution/
│   ├── sandbox.py
│   ├── process.py
│   └── timeout.py
├── prompts/
│   ├── planner.txt
│   ├── coder.txt
│   └── debugger.txt
├── workspaces/
└── tests/
```

Phase 1 constraints:

```text
max_attempts = 5
timeout = 30 seconds
network = disabled
package_installation = disabled
temporary workspace = required
```

---

# 46. Phase 1 Execution Flow

```text
User prompt
    ↓
Planner
    ↓
TaskSpecification
    ↓
Coder
    ↓
main.py
    ↓
Syntax check
    ↓
Execution
    ↓
Success?
   / \
 No   Yes
 |      \
 ▼       ▼
Debugger Verified
 |
 └───► Retry (up to 5 attempts)
```

---

# 64. Phase 1 Concrete Contract

The first implementation should satisfy exactly:

```text
INPUT
  natural-language prompt

OUTPUT
  main.py

PROCESS
  planner
    ↓
  coder
    ↓
  syntax validation
    ↓
  execution
    ↓
  traceback capture
    ↓
  debugger
    ↓
  patch
    ↓
  retry

LIMITS
  max_attempts = 5
  timeout = 30 sec
  network = disabled
  package installation = disabled
  temporary workspace = required
```

Phase 1 should not contain:

```text
multi-language support
Jupyter
automatic package installation
public dataset downloading
Docker
database
```

Those are later milestones.

---

# 65. Cross-Phase Invariants

These rules apply throughout the implementation.

1. **Never allow unbounded retries.** `MAX_ATTEMPTS = 5`.
2. **Never treat exit code 0 as verification.** Tests and acceptance criteria matter. (In Phase 1, exit code 0 without exceptions/errors fulfills minimal script execution).
3. **Never install packages directly on the host.**
4. **Never provide unrestricted shell access to the LLM.**
5. **Never expose host secrets to generated code.**
6. **Never let generated code write outside its workspace.**
7. **Prefer structured JSON over natural-language parsing.**
8. **Keep the LLM provider replaceable.**
9. **Persist every attempt.**
10. **Keep source, tests, inputs, outputs, notebooks, and logs separate.**
11. **Deterministic error handlers should run before LLM debugging.**
12. **Network access is disabled by default.**
