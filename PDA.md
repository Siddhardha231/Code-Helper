# PDA — Autonomous Code Generation & Verification Platform

> **Product Definition:** An autonomous software execution environment that converts
> natural-language specifications into tested, reproducible program artifacts.

**Version:** 1.0
**Status:** Design / Pre-implementation
**Model:** `qwen2.5-coder:1.5b` (local, via Ollama) — model-agnostic architecture
**UI:** Streamlit

---

## Table of Contents

1. [Vision & Scope](#1-vision--scope)
2. [First Principles — Five Questions](#2-first-principles--five-questions)
3. [System Architecture (High Level)](#3-system-architecture-high-level)
4. [Component Design](#4-component-design)
5. [Execution Sandbox (Non-Negotiable)](#5-execution-sandbox-non-negotiable)
6. [Tool Layer](#6-tool-layer)
7. [Multi-Agent Topology](#7-multi-agent-topology)
8. [End-to-End Execution Lifecycle](#8-end-to-end-execution-lifecycle)
9. [Retry Policy](#9-retry-policy)
10. [Project Structure](#10-project-structure)
11. [Phased Roadmap (MVP → Full System)](#11-phased-roadmap-mvp--full-system)
12. [Risk Register (Devil's Advocate)](#12-risk-register-devils-advocate)
13. [Final Target Architecture](#13-final-target-architecture)
14. [Product Definition (Final)](#14-product-definition-final)
15. [Next Concrete Step](#15-next-concrete-step)
16. [Implementation Notes Per Phase](#16-implementation-notes-per-phase)

---

## 1. Vision & Scope

### 1.1 What This Is

A general-purpose autonomous coding/execution agent that takes a natural-language
prompt and produces a **verified, reproducible artifact**:

```
prompt → specification → code → dependency resolution → execution
       → testing → debugging → final artifact
```

### 1.2 What This Is Not

- Not an "AI that writes Python."
- Not a thin wrapper around `subprocess.run()`.
- Not a system where the LLM is responsible for everything.

### 1.3 Core Principle

> **The LLM makes decisions; deterministic services execute, test, install, and inspect.**

### 1.4 Central Distinction

> **Execution success ≠ correctness.**

Correctness requires:

```
Syntax correctness
      +
Environment correctness
      +
Runtime correctness
      +
Test correctness
      +
Task correctness
```

---

## 2. First Principles — Five Questions

Every prompt must resolve:

| # | Question | Resolved By |
|---|----------|-------------|
| 1 | What should be built? | Planner |
| 2 | Which language? | Planner / Language Registry |
| 3 | What files are required? | Planner + Coder |
| 4 | What dependencies are required? | Dependency Analyzer |
| 5 | How do we know it works? | Test Generator + Runner |

### 2.1 Core Loop

```
PROMPT
  ↓
SPECIFICATION
  ↓
CODE GENERATION
  ↓
DEPENDENCY ANALYSIS
  ↓
ENVIRONMENT PREPARATION
  ↓
EXECUTION
  ↓
TESTING
  ↓
      ┌─────────────── error ───────────────┐
      ↓                                      │
ERROR ANALYSIS                              │
      ↓                                      │
CODE CORRECTION ────────────────────────────┘
      │
      ↓
ALL TESTS PASS
      ↓
ARTIFACTS
```

Expressed as code:

```python
while not verified:
    generate_or_fix_code()
    resolve_dependencies()
    execute()
    run_tests()
    analyze_result()
```

**Constraint:** The loop needs strict boundaries (max attempts, allowed packages,
allowed commands) to prevent runaway behavior.

---

## 3. System Architecture (High Level)

```
                    ┌─────────────────────┐
                    │      Web UI         │
                    │     Streamlit       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Agent Manager    │
                    │  Planning / State   │
                    │    Retry policy     │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
 ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
 │ Code Generator │   │ Test Generator │   │ Error Analyzer │
 │      LLM       │   │      LLM       │   │      LLM       │
 └────────────────┘   └────────────────┘   └────────────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Language Manager    │
                    └──────────┬──────────┘
                               │
        ┌──────────────┬───────┼────────┬──────────────┐
        ▼              ▼       ▼        ▼              ▼
     Python          Java    C/C++  JavaScript      ...
        │
        ▼
 ┌──────────────────────────────────────────────────────┐
 │                 Execution Engine                     │
 │   Docker / isolated container                        │
 │   filesystem · timeout · memory · network policy     │
 └─────────────────────────┬────────────────────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │ Dependency Manager  │
                 └─────────────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │  Artifact Manager   │
                 │  .py .ipynb inputs  │
                 │  outputs logs       │
                 └─────────────────────┘
```

---

## 4. Component Design

### 4.1 Language Adapter Interface

**Do not** implement "any language" as one giant `if/else` chain. Use an adapter
per language.

```python
class LanguageAdapter:
    language_name: str

    def detect_files(self): ...
    def install_dependencies(self): ...
    def compile(self): ...
    def execute(self): ...
    def test(self): ...
    def collect_errors(self): ...
```

Adapters:

```
LanguageAdapter
├── PythonAdapter
├── JavaScriptAdapter
├── TypeScriptAdapter
├── JavaAdapter
├── CAdapter
├── CppAdapter
├── GoAdapter
├── RustAdapter
└── ...
```

### 4.2 Python Execution Modes

```
Python
├── Script Mode   → main.py
└── Notebook Mode → notebook.ipynb
```

**UI control:**

```
Language
[ Auto ▼ ]

Python execution mode
(●) Python Script
( ) Jupyter Notebook
```

Auto-selection rule: prompts mentioning "notebook", "data analysis", "explore",
or "visualize" → Jupyter mode.

### 4.3 Notebook Architecture

**Never** have the LLM emit raw `.ipynb` JSON. Use a structured intermediate:

```
LLM
 ↓
Structured notebook representation
 ↓
Notebook Builder
 ↓
nbformat
 ↓
.ipynb
 ↓
Jupyter execution
```

Intermediate representation:

```python
notebook = {
    "cells": [
        {"type": "markdown", "content": "# Student Analysis"},
        {"type": "code",     "content": "import pandas as pd"},
        {"type": "code",     "content": "df = pd.read_csv('students.csv')"},
    ]
}
```

Execution must capture per-cell:

```
stdout · stderr · exceptions · cell number · execution count · outputs
```

So the debugger can report:

```
Cell 7 failed.
NameError: 'df_cleaned' is not defined.
```

### 4.4 Dependency Resolution

**Never** let the LLM run `pip install whatever-it-wants`.

```
Generated code
       ↓
Dependency Analyzer
       ↓
Required packages
       ↓
Package Resolver
       ↓
Virtual environment
       ↓
Install
```

Example:

```
import pandas
import numpy
import matplotlib.pyplot
   ↓
pandas
numpy
matplotlib
   ↓
requirements.txt
```

Workspace layout:

```
workspace/
├── main.py
├── requirements.txt
├── input/
└── output/
```

### 4.5 Missing-Module Recovery

```
ModuleNotFoundError: No module named 'requests'
        ↓
Error Classifier
        ↓
extract "requests"
        ↓
package resolver
        ↓
pip install requests
        ↓
rerun
```

Only escalate to the LLM if deterministic recovery fails.

### 4.6 Error Correction Levels

```
                    FAILURE
                       │
                       ▼
                Error Classifier
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
 Dependency         Environment       Code
       │               │                │
       ▼               ▼                ▼
Auto resolve       Auto resolve      LLM repair
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                    RERUN
```

Error classes:

```
ERROR CLASSIFIER
       │
       ├── Missing dependency
       ├── Syntax error
       ├── Runtime error
       ├── Compilation error
       ├── Test failure
       ├── File not found
       ├── Permission error
       └── Environment error
```

Handling matrix:

| Error | Handler |
|-------|---------|
| `ModuleNotFoundError: pandas` | install pandas |
| `FileNotFoundError: students.csv` | check input artifact exists |
| `SyntaxError` | send source + traceback to repair agent |
| `AssertionError` | send test + source + result to debugging agent |

### 4.7 Testing System

**More important than execution.**

```
Generated
   ↓
Executed
   ↓
Tests
   ↓
Verified
```

`program exited with code 0` is **not** success.

Example:

```python
def factorial(n): ...

assert factorial(0) == 1
assert factorial(1) == 1
assert factorial(5) == 120
assert factorial(10) == 3628800
```

Only after `4/4 PASS`:

```
STATUS = VERIFIED
```

**Weakness:** If the same LLM writes both code and tests, it can make the same
mistake twice. Mitigation:

```
Code Generator
       │
       ▼
Implementation
       │
       ├───────────────┐
       │               │
       ▼               ▼
Test Generator    Static Analysis
       │               │
       └───────┬───────┘
               ▼
          Verification
```

And **user-provided tests** are the strongest verification source.

### 4.8 Input Files — Three Distinct Cases

**A. User provides a file**

```
Prompt + students.csv
   ↓
workspace/input/students.csv
   ↓
pd.read_csv("input/students.csv")
```

**B. Prompt specifies a public dataset**

```
"Download the Iris dataset and analyze it."
   ↓
input/iris.csv
```

**C. Prompt requires an external API**

```
API → network permission → credentials → runtime
```

These must **not** be treated as the same thing.

### 4.9 Artifact Manager

Artifacts are first-class.

```
workspace/
│
├── source/
│   ├── main.py
│   └── helper.py
│
├── tests/
│   └── test_main.py
│
├── input/
│   ├── data.csv
│   └── config.json
│
├── output/
│   ├── result.csv
│   └── graph.png
│
├── notebook/
│   └── analysis.ipynb
│
├── logs/
│   ├── execution.log
│   └── errors.log
│
└── metadata.json
```

UI rendering:

```
Generated Files
📄 main.py
📄 requirements.txt
📄 test_main.py
📊 result.csv
📓 analysis.ipynb
🖼 graph.png
```

### 4.10 Agent State

```python
@dataclass
class AgentState:
    task: str
    language: str
    execution_mode: str
    workspace: str
    source_files: list
    input_files: list
    output_files: list
    dependencies: list
    tests: list
    execution_results: list
    errors: list
    attempt: int
    max_attempts: int
    status: str
```

This makes the agent reproducible.

---

## 5. Execution Sandbox (Non-Negotiable)

This is where the design **must** diverge from a naive `subprocess.run()` approach.

A prompt like *"Create a Python program that searches my computer for files"*
can produce:

```python
import os
import subprocess
import shutil
import socket
```

**An LLM-generated program must run inside an isolated environment.**

```
Web Application
      │
      ▼
Agent
      │
      ▼
Workspace
      │
      ▼
Container / Sandbox
      │
      ├── CPU limit
      ├── RAM limit
      ├── execution timeout
      ├── filesystem isolation
      ├── network policy
      └── process limits
```

### 5.1 Never Install Into the Host

**Bad:**

```
Agent → pip install → YOUR WINDOWS/WSL ENVIRONMENT
```

**Better:**

```
Agent
 ↓
create execution environment
 ↓
install dependencies
 ↓
execute
 ↓
destroy environment
```

```
workspace #123
     │
     ▼
isolated environment
     │
     ├── Python
     ├── pip
     ├── pandas
     └── numpy
     │
     ▼
execute
     │
     ▼
collect artifacts
     │
     ▼
destroy
```

Environment caching may be added later for performance.

---

## 6. Tool Layer

Do **not** give the LLM unrestricted shell access. Expose controlled tools:

```
Tools
│
├── create_file()
├── read_file()
├── edit_file()
├── list_files()
│
├── install_python_package()
├── install_npm_package()
├── install_maven_dependency()
│
├── execute_python()
├── execute_javascript()
├── execute_java()
├── execute_cpp()
│
├── run_tests()
├── inspect_error()
│
├── create_input_file()
├── download_dataset()
│
└── collect_artifacts()
```

The LLM decides *"I need pandas"*; the application decides **how** pandas is
installed.

---

## 7. Multi-Agent Topology

Use specialized agents, not one giant prompt.

```
                    USER PROMPT
                         │
                         ▼
                  ┌─────────────┐
                  │   PLANNER   │
                  └──────┬──────┘
                         │
                         ▼
                  Task Specification
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       Code Agent   Test Agent   Dependency Agent
            │            │            │
            └────────────┼────────────┘
                         ▼
                    EXECUTION
                         │
                         ▼
                   RESULT ANALYZER
                         │
              ┌──────────┴──────────┐
              │                     │
             PASS                  FAIL
              │                     │
              ▼                     ▼
          VERIFIED              DEBUGGER
                                    │
                                    ▼
                                  PATCH
                                    │
                                    └──────► EXECUTION
```

### 7.1 Planner — Structured Output Only

**No** free-form prose. JSON only.

Script example:

```json
{
  "language": "python",
  "execution_mode": "script",
  "entrypoint": "main.py",
  "dependencies": [],
  "input_files": [],
  "output_files": [],
  "tests_required": true
}
```

Notebook example:

```json
{
  "language": "python",
  "execution_mode": "jupyter",
  "entrypoint": "analysis.ipynb",
  "dependencies": ["pandas", "matplotlib"],
  "input_files": ["data.csv"],
  "tests_required": true
}
```

The application validates this. Parsing natural language is a fallback, not the
primary path.

---

## 8. End-to-End Execution Lifecycle

```
USER
"Create a Python program that reads students.csv,
 calculates average marks and generates a graph."
                    │
                    ▼
             ┌──────────────┐
             │    PLANNER   │
             └──────┬───────┘
                    │
                    ▼
Language: Python
Mode: Script
Input: students.csv
Output: result.csv
Output: graph.png
Tests: required
                    │
                    ▼
             ┌──────────────┐
             │  CODE AGENT  │
             └──────┬───────┘
                    │
                    ▼
                main.py
                    │
                    ▼
           DEPENDENCY ANALYZER
                    │
                    ▼
              pandas
              matplotlib
                    │
                    ▼
           ENVIRONMENT BUILDER
                    │
                    ▼
              SANDBOX
                    │
                    ▼
               EXECUTE
                    │
                    ▼
             ┌──────────────┐
             │   RESULT     │
             └──────┬───────┘
                    │
                    ▼
                 TESTS
                    │
             ┌──────┴──────┐
             │             │
            FAIL          PASS
             │             │
             ▼             ▼
          DEBUGGER      VERIFIED
             │             │
             ▼             ▼
           PATCH        ARTIFACTS
             │
             └──────► EXECUTE
```

---

## 9. Retry Policy

Do **not** use `while error: fix()`. That can run forever.

```
MAX_ATTEMPTS = 5
```

Track *why* each attempt failed:

```
Attempt 1
─────────
SyntaxError

Attempt 2
─────────
ModuleNotFoundError: pandas

Attempt 3
─────────
FileNotFoundError

Attempt 4
─────────
Test failure

Attempt 5
─────────
All tests passed
→ STATUS = VERIFIED
```

If attempt 5 fails:

```
STATUS = FAILED
→ return entire debugging history
```

### 9.1 Do Not Blindly "Fix" Every Error

If `pip install pandas` fails, the LLM might try
`pip install random-pandas-package`. Dangerous.

Dependency system must verify:

```
import name
      ↓
package mapping
      ↓
PyPI/package registry
      ↓
package metadata
      ↓
install
```

Unusual packages may require user approval.

---

## 10. Project Structure

```
auto-code-agent/
│
├── app.py
│
├── config/
│   ├── settings.py
│   └── languages.yaml
│
├── agent/
│   ├── planner.py
│   ├── coder.py
│   ├── debugger.py
│   ├── tester.py
│   └── orchestrator.py
│
├── execution/
│   ├── sandbox.py
│   ├── process.py
│   ├── timeout.py
│   └── resources.py
│
├── languages/
│   ├── base.py
│   ├── python.py
│   ├── javascript.py
│   ├── java.py
│   ├── cpp.py
│   └── registry.py
│
├── dependencies/
│   ├── resolver.py
│   ├── python.py
│   ├── npm.py
│   └── maven.py
│
├── testing/
│   ├── test_generator.py
│   ├── test_runner.py
│   └── evaluator.py
│
├── notebooks/
│   ├── builder.py
│   └── executor.py
│
├── artifacts/
│   ├── manager.py
│   └── storage.py
│
├── workspaces/
│
├── prompts/
│   ├── planner.txt
│   ├── coder.txt
│   ├── debugger.txt
│   └── tester.txt
│
└── tests/
    ├── unit/
    └── integration/
```

---

## 11. Phased Roadmap (MVP → Full System)

Do **not** attempt all languages + notebooks + autonomous downloads + sandboxing
simultaneously.

### Phase 1 — Python

```
Prompt → Generate main.py → Execute → Capture errors → LLM fixes → Retry
```

Evolves the existing Local Auto-Code Agent.

### Phase 2 — Testing

```
Generate code → Generate tests → Run tests → Fix failures → Verified
```

### Phase 3 — Dependencies

```
import analysis → dependency resolver → isolated environment → install
```

### Phase 4 — Input/Output Artifacts

```
input/ · output/ — automatically managed
```

### Phase 5 — Jupyter

```
Python Script | Python Notebook
```

### Phase 6 — Other Languages

```
JavaScript · Java · C · C++ · Go · Rust
```

### Phase 7 — Strong Sandbox

Move all execution into containers / isolated environments.

### Phase 8 — Full Autonomous Agent

```
Prompt → Planner → Code → Dependencies → Environment
       → Execution → Testing → Debugging → Verification → Artifacts
```

---

## 12. Risk Register (Devil's Advocate)

| Problem | Why it's difficult |
|---------|--------------------|
| Any programming language | Each ecosystem has different build/package/test systems |
| Automatic package installation | Import names ≠ package names |
| Automatic debugging | Some failures are environmental, not code errors |
| Generated tests | Same model can generate bad tests |
| Input downloading | Source, format, licensing, URLs, network failures vary |
| Jupyter | Notebook state makes execution different from scripts |
| Autonomous execution | Generated code is untrusted code |
| Infinite correction | Agent may repeatedly make equivalent changes |
| Dependency conflicts | Packages can require incompatible versions |
| Compilation | C/C++/Rust/Java introduce build-toolchain problems |
| External APIs | Credentials, rate limits, network policies matter |
| Correctness | "Runs successfully" ≠ "solves the requested problem" |

---

## 13. Final Target Architecture

```
                         ┌──────────────┐
                         │    USER      │
                         └──────┬───────┘
                                │
                                ▼
                     ┌───────────────────┐
                     │   WEB FRONTEND    │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │ AGENT ORCHESTRATOR│
                     └─────────┬─────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
        ┌─────────┐       ┌─────────┐       ┌─────────┐
        │ PLANNER │       │  CODER  │       │ TESTER  │
        └─────────┘       └─────────┘       └─────────┘
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                      ┌─────────────────┐
                      │ TOOL CONTROLLER │
                      └────────┬────────┘
                               │
          ┌────────────────────┼─────────────────────┐
          ▼                    ▼                     ▼
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │ DEPENDENCY  │      │    FILE     │      │  LANGUAGE   │
   │   MANAGER   │      │   MANAGER   │      │  ADAPTERS   │
   └─────────────┘      └─────────────┘      └─────────────┘
          │                    │                     │
          └────────────────────┼─────────────────────┘
                               ▼
                     ┌──────────────────┐
                     │ EXECUTION SANDBOX│
                     └────────┬─────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │  RESULT ANALYZER │
                     └────────┬─────────┘
                              │
                       ┌──────┴──────┐
                       │             │
                    FAILURE        PASS
                       │             │
                       ▼             ▼
                  ┌─────────┐   ┌──────────┐
                  │ DEBUGGER│   │ VERIFIED │
                  └────┬────┘   └────┬─────┘
                       │             │
                       └──────┐      ▼
                              │   ARTIFACTS
                              │
                              └──► RETRY
```

This is not "an AI that writes Python." It is a **language-agnostic code
generation and verification platform**.

---

## 14. Product Definition (Final)

Instead of:

> *"AI that writes and runs code."*

Define the product as:

> **"An autonomous software execution environment that converts natural-language
> specifications into tested, reproducible program artifacts."**

That definition naturally leads to the right architecture:

```
planner → generator → dependency resolver → sandbox → executor
       → tester → debugger → verifier → artifacts
```

rather than an LLM wrapped around `subprocess.run()`.

---

## 15. Next Concrete Step

Turn this PDA into an **implementation-level TDA** containing:

- Exact Python classes and interfaces
- State machine definition
- Database schema
- API endpoints
- Docker sandbox design
- Jupyter execution flow
- First working MVP implementation (Phase 1)

---

## 16. Implementation Notes Per Phase

This section gives concrete, minimal implementation guidance for each phase so
you can build incrementally without over-engineering.

### Phase 1 — Python (Script Mode Only)

**Goal:** `Prompt → main.py → Execute → Capture errors → LLM fixes → Retry → Done`

**Deliverables:**

```
auto-code-agent/
├── app.py                    # Streamlit UI
├── agent/
│   ├── planner.py            # prompt → JSON spec (minimal)
│   ├── coder.py              # spec → main.py
│   ├── debugger.py           # traceback → patch
│   └── orchestrator.py       # retry loop
├── execution/
│   ├── sandbox.py            # subprocess wrapper (temp dir)
│   ├── process.py            # run + capture stdout/stderr
│   └── timeout.py            # kill after N seconds
├── workspaces/
│   └── ws_<uuid>/
│       └── main.py
└── prompts/
    ├── planner.txt
    ├── coder.txt
    └── debugger.txt
```

**Constraints:**

- Max attempts: 5
- Timeout: 30s
- No network
- No package installs
- Temp directory per run, deleted after

**Minimal `AgentState`:**

```python
@dataclass
class AgentState:
    task: str
    workspace: str
    source: str
    attempt: int = 0
    max_attempts: int = 5
    errors: list = field(default_factory=list)
    status: str = "pending"  # pending | running | verified | failed
```

**Exit criteria for Phase 1:**

- Prompt `"print hello world"` → produces `main.py`, runs it, captures output.
- Prompt with a deliberate bug (e.g. `"divide 1 by 0"`) → produces traceback,
  sends to debugger, LLM patches, reruns.
- After 5 failed attempts, returns full history with `status="failed"`.

---

### Cross-Phase Rules

1. **Never skip the sandbox for long.** Even Phase 1 should run in a temp dir with
   timeout; move to Docker by Phase 7 at the latest.
2. **Never parse natural language when you can require JSON.** Planner, dependency
   analyzer, and error classifier all emit JSON.
3. **Never let the LLM choose package names directly.** Map imports → packages via a
   controlled registry.
4. **Never treat exit code 0 as success.** Only tests passing counts.
5. **Never let retries run unbounded.** `MAX_ATTEMPTS = 5`, always.
6. **Always persist the full attempt history.** It is the product's audit trail.
7. **Always keep the model swappable.** `qwen2.5-coder:1.5b` today, anything
   tomorrow — the architecture must not depend on it.

---

*End of PDA.*
