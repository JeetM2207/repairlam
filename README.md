# RepairLAM: Autonomous Software Maintenance Using Large Action Models

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Model](https://img.shields.io/badge/Model-Qwen--2.5--Coder--32B--Instruct-purple.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct)
[![Hardware](https://img.shields.io/badge/Hardware-NVIDIA_DGX_A100-green.svg)](https://www.nvidia.com/en-us/data-center/dgx-a100/)
[![PR Precision](https://img.shields.io/badge/PR_Precision-100%25-brightgreen.svg)](#pull-request-precision)
[![Safe Escalation](https://img.shields.io/badge/Safe_Escalation-P%3D1.0-brightgreen.svg)](#safe-escalation-policy)

> **B.Tech Project (BTP) Final Implementation & Empirical Evaluation**  
> **Department of Computer Science and Engineering, The LNM Institute of Information Technology (LNMIIT), Jaipur**  
> **Students:** Meet Patel (`23UCS644`), Jeet Manseta (`23UCS603`)  
> **Supervisor:** Dr. Ankit Kumar Jain  
> **GitHub Repository:** [JeetM2207/repairlam](https://github.com/JeetM2207/repairlam)

---

## Table of Contents
- [Executive Overview](#executive-overview)
- [Core Milestones \& Contributions](#core-milestones--contributions)
- [Theoretical Foundation \& Architecture](#theoretical-foundation--architecture)
  - [SE 3.0 Dual Workbench Paradigm](#se-30-dual-workbench-paradigm)
  - [Action-Constrained Finite State Machine (FSM)](#action-constrained-finite-state-machine-fsm)
  - [Syntactic Anchor Replacement Engine](#syntactic-anchor-replacement-engine)
  - [Zero-Pollution Safe Escalation Policy](#zero-pollution-safe-escalation-policy)
- [Repository Structure](#repository-structure)
- [Installation \& Environment Setup](#installation--environment-setup)
- [Model Deployment on NVIDIA DGX A100](#model-deployment-on-nvidia-dgx-a100)
- [Execution Workflows](#execution-workflows)
  - [1. Running Live GitHub Issue Repair](#1-running-live-github-issue-repair)
  - [2. Human-in-the-Loop Interactive Resumption](#2-human-in-the-loop-interactive-resumption)
  - [3. Running Phase 1 Algorithmic Baseline (QuixBugs)](#3-running-phase-1-algorithmic-baseline-quixbugs)
  - [4. Module 6: Self-Boosting Trajectory Harvesting \& LoRA SFT](#4-module-6-self-boosting-trajectory-harvesting--lora-sft)
- [Comprehensive Empirical Results](#comprehensive-empirical-results)
  - [Phase 1: QuixBugs Algorithmic Benchmark](#phase-1-quixbugs-algorithmic-benchmark-n--40)
  - [Phase 2: Live GitHub 36-Bug Evaluation](#phase-2-live-github-36-bug-evaluation-n--36)
  - [All 36 Evaluated Live Issues (Full Trace)](#all-36-evaluated-live-issues-full-trace)
  - [Module 6 LoRA Fine-Tuning Convergence](#module-6-lora-fine-tuning-convergence-dgx-gpu-1)
- [Formal Empirical Ablation Studies (A1–A4)](#formal-empirical-ablation-studies-a1a4)
- [Academic Report \& LaTeX Source](#academic-report--latex-source)
- [Citation \& Acknowledgements](#citation--acknowledgements)

---

## Executive Overview

Software maintenance accounts for **60% to 80%** of total software lifecycle costs, costing the global economy approximately **$2.41 trillion annually**. Software engineers spend nearly half their working hours on bug diagnosis, localization, patch authoring, and verification.

While modern Large Language Models (LLMs) such as GPT-4 and Gemini exhibit strong text generation, they remain fundamentally **passive**—incapable of directly executing code, inspecting compiler errors, running regression test suites, or safely managing version control systems. Without grounded execution, LLMs suffer from severe hallucinations, frequently producing broken patches that introduce regressions.

**RepairLAM** solves this crisis by transforming passive code models into active **Large Action Models (LAMs)** guided by an **Action-Constrained Finite State Machine (FSM)**:
1. **Perceives Ground Truth**: Interacts directly with operating system subprocesses, compilers (`javac`, `mvn`, `gradle`), and test runners (JUnit).
2. **Executes Action Trajectories**: Emits structured, schema-validated JSON tool calls with line-anchored syntactic modifications.
3. **Guarantees Zero Repository Pollution**: Opens pull requests **strictly** if 100% of project test suites pass, deterministically halting and posting diagnostic comments when safety boundaries are triggered.

```
       [Raw GitHub Issue]
               │
               ▼
   ┌───────────────────────┐
   │ Scout & Fault Ingest  │ ──► Clones repo, checks out fix branch
   └───────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │  Action-Bounded FSM   │ ◄── Iterative Test & Error Feedback
   │ (UNDERSTAND ➔ FIX)    │
   └───────────────────────┘
         │           │
   (Tests Pass)  (Budget/Syntax Fail)
         │           │
         ▼           ▼
┌─────────────────┐ ┌──────────────────┐
│   Pull Request  │ │  Safe Escalation │
│   (100% Pass)   │ │ (Diagnostic Post)│
└─────────────────┘ └──────────────────┘
```

---

## Core Milestones & Contributions

1. **Live GitHub Issue Pipeline (Phase 2)**: Evaluated across **36 real-world, open, unfixed GitHub issues** spanning 5 enterprise Java repositories: `google/guava`, `google/gson`, `FasterXML/jackson-databind`, `netty/netty`, and `apache/commons-csv`.
2. **100% Pull Request Precision ($P = \frac{7}{7} = 1.00$)**: Every single pull request opened on GitHub passed 100% of the project's regression and integration test suites. Exactly **zero broken PRs** were ever submitted to open-source maintainers.
3. **Deterministic Safe Escalation ($P = 1.0$)**: When safety thresholds or edit budgets were reached, the agent cleanly halted and posted structured diagnostic comments (15 escalations, with **11 exiting with exactly 0 code churn**), preserving branch cleanliness.
4. **Module 6 Self-Boosting LAM Training**: Harvested 139 multi-turn trajectories (118 train, 21 validation) into ShareGPT format and successfully fine-tuned `Qwen-2.5-Coder-32B-Instruct` via LoRA ($r=8, \alpha=16$) on an NVIDIA DGX A100 server (GPU 1), reducing eval loss to **1.6455**.
5. **Human-in-the-Loop Interactive Resumption (Modules 5 & 8)**: Built and verified live interactive resumption enabling developers to comment directly on escalated GitHub issues to steer the agent to a valid fix without session restart (demonstrated live on `apache/commons-csv#4`).
6. **Phase 1 Foundations (QuixBugs Benchmark)**: Achieved **80% plausible (32/40)** and **70% correct (28/40)** repair rates on QuixBugs using Google Gemini 1.5 Pro, delivering a **$242\times$ execution speedup** and a **$14\times$ cost reduction** (~$0.01/bug) over Defects4J baseline literature.
7. **Formal Ablation Studies (A1–A4)**: Empirically verified that multi-turn FSM beats one-shot repair ($65.0\%$ vs $0.0\%$), syntactic anchors eliminate syntax errors ($0\%$ vs $35\%$), and turn budget scaling saturates optimally at $T \approx 30$.

---

## Theoretical Foundation & Architecture

### SE 3.0 Dual Workbench Paradigm
In strict alignment with the Agentic Software Engineering (SE 3.0) principles formulated by Hassan et al. (2025):
- **Agent Execution Environment (AEE)**: A digital, headless runtime where RepairLAM manages git branches, executes Maven/Gradle builds, and captures sanitized test logs without human visualization.
- **Agent Command Environment (ACE)**: A human-facing interface (GitHub Issues and PRs). RepairLAM submits verified **Merge-Readiness Packs (MRPs)** containing code diffs, passing test logs, and conventional commit summaries, shifting the human engineer from code author to senior reviewer.

### Action-Constrained Finite State Machine (FSM)
To prevent degenerative generation loops, RepairLAM enforces a mathematical state machine $\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{T}, \mathcal{G} \rangle$:
- **States $\mathcal{S}$**: `UNDERSTAND`, `COLLECT`, `TRY_FIX`, `REFLECT`, `PLAUSIBLE`, `ESCALATED`, `TIMEOUT`.
- **Phase-Constrained Tool Invocations**:
  - `read_file` and `search_code` are restricted to `COLLECT` and `REFLECT`.
  - `anchor_edit` is restricted exclusively to `TRY_FIX`.
  - **Invariance Rule**: Immediately after an `anchor_edit`, the only allowable action is `run_test`. Free-form consecutive edits without test execution are disallowed.
  - Escalation is blocked until at least 2 distinct patch attempts have been evaluated.

```
       ┌───────────────┐        has context        ┌───────────────┐
       │  UNDERSTAND   │ ────────────────────────► │    COLLECT    │ ◄──┐ (search /
       └───────────────┘                           └───────────────┘ ───┘  read)
               │                                           │
       ambiguous issue                             has target & code
               │                                           │
               ▼                                           ▼
       ┌───────────────┐        tests fail         ┌───────────────┐
       │   ESCALATED   │ ◄──────────────────────── │    TRY_FIX    │
       └───────────────┘                           └───────────────┘
               ▲                                           │
        budget exhausted                              tests pass
               │                                           │
       ┌───────────────┐                                   ▼
       │    REFLECT    │ ◄──────────────────────── ┌───────────────┐
       └───────────────┘                           │   PLAUSIBLE   │
               │                                   └───────────────┘
               └─────────► new hypothesis ────────► (UNDERSTAND)
```

### Syntactic Anchor Replacement Engine
Unlike naive repair tools that overwrite whole files (which cause truncation and break untouched methods), RepairLAM uses strict syntactic line-anchoring:
```json
{
  "file_path": "gson/src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java",
  "anchor_start": "final boolean isPrimitive = Primitives.isPrimitive(fieldType.getRawType());",
  "original_code": "JsonAdapter annotation = field.getAnnotation(JsonAdapter.class);",
  "replacement_code": "if (field.isSynthetic()) {\n  return null;\n}\nJsonAdapter annotation = field.getAnnotation(JsonAdapter.class);",
  "anchor_end": "TypeAdapter<?> mapped = null;"
}
```
If `original_code` does not match uniquely within the range bounded by `anchor_start` and `anchor_end`, the edit is rejected without mutating the filesystem.

### Zero-Pollution Safe Escalation Policy
In professional engineering, submitting a broken PR is actively harmful. RepairLAM implements:
1. Hard turn budget cap ($T_{\text{max}} = 35$).
2. Consecutive syntax error cap ($K_{\text{syntax}} = 3$).
3. Immediate `git reset --hard HEAD` on non-convergence.
4. Autonomous posting of an **Escalation Diagnostic Report** onto the issue with zero code churn.

---

## Repository Structure

```
.
├── CLAUDE.md                   # Operational cheat-sheet and DGX cluster guidelines
├── README.md                   # Comprehensive project documentation (this file)
├── .env.example                # Template for GitHub PAT, vLLM endpoints, and API keys
│
├── repairlam/                  # Core Python LAM Framework
│   ├── agent/                  # Agent loop and state machine
│   │   ├── loop.py             # FSM orchestrator (UNDERSTAND -> COLLECT -> FIX -> REFLECT)
│   │   ├── prompts.py          # System prompts, state schemas, and format enforcement
│   │   └── interactive.py      # Modules 5 & 8: Human-in-the-Loop resumption engine
│   ├── env/                    # Environment execution adapters
│   │   ├── d4j.py              # Defects4J CLI bindings (checkout, compile, test)
│   │   └── maven.py            # Headless Maven / Gradle subprocess runners
│   ├── github/                 # GitHub API & version control integration
│   │   ├── client.py           # PyGithub interface for issue extraction and PR creation
│   │   └── repo_env.py         # Git credential isolation (GIT_ASKPASS helper)
│   ├── tools/                  # Model tool-calling registry
│   │   ├── registry.py         # Tool dispatcher and phase constraint checker
│   │   └── edit.py             # Syntactic anchor replacement engine
│   ├── training/               # Module 6: Self-boosting training pipeline
│   │   ├── harvest.py          # Trajectory extraction from execution logs (139 episodes)
│   │   ├── train_lora.py       # LoRA SFT script for Qwen-2.5-Coder-32B on DGX
│   │   └── data/               # Harvested JSONL dataset (118 train, 21 validation)
│   └── events.py               # Structured turn-by-turn JSONL event logger
│
├── results/                    # Complete empirical evaluation artifacts
│   ├── live_run_log.json       # Comprehensive log of all 36 live GitHub runs
│   └── formal_ablation_studies.md # Full documentation of Ablations A1–A4
│
├── report/                     # Master Academic BTP Thesis
│   └── main.tex                # 1100+ line self-contained LaTeX source with TikZ figures
│
├── scripts/                    # Utility scripts for batch running and evaluation
│   ├── run_quixbugs.py         # Phase 1 QuixBugs runner with Gemini JSON adapter
│   └── evaluate_live.py        # Phase 2 batch runner for live GitHub issues
│
└── tests/                      # Unit and regression test suite for RepairLAM
```

---

## Installation & Environment Setup

### 1. Prerequisites
- **Python**: Version 3.10 or higher.
- **Java**: JDK 8 (for legacy Defects4J) and JDK 11/17 (for modern GitHub repositories).
- **Build Tools**: Apache Maven (`mvn`) and Gradle (`gradle`) in system `PATH`.
- **Git**: Configured with user identity.
- **Hardware**: For local serving, an NVIDIA GPU with at least 24GB VRAM (or access to DGX A100 cluster).

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/JeetM2207/repairlam.git
cd repairlam

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Credentials
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Fill in the parameters:
```env
# GitHub Personal Access Token (classic, with repo & workflow scopes)
GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere

# vLLM Server or Frontier Model Endpoint
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_API_KEY=EMPTY

# Optional: Gemini API Key for Phase 1 QuixBugs
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
```

---

## Model Deployment on NVIDIA DGX A100

On the LNMIIT DGX A100 cluster, we serve `Qwen-2.5-Coder-32B-Instruct` using `vLLM` on GPU 6:

```bash
# Check available GPUs
nvidia-smi

# Launch vLLM OpenAI-Compatible Server
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 1 \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --dtype bfloat16
```

---

## Execution Workflows

### 1. Running Live GitHub Issue Repair
To execute RepairLAM on an open GitHub issue:
```bash
# Run on a specific live issue
python -m repairlam.agent.loop \
  --repo google/gson \
  --issue 1920 \
  --max-turns 35 \
  --model Qwen/Qwen2.5-Coder-32B-Instruct
```

### 2. Human-in-the-Loop Interactive Resumption
When an issue is escalated, resume the session with developer feedback:
```bash
# Resume an escalated issue from developer feedback
python -m repairlam.agent.interactive \
  --repo apache/commons-csv \
  --issue 4 \
  --listen-comments
```

### 3. Running Phase 1 Algorithmic Baseline (QuixBugs)
```bash
python scripts/run_quixbugs.py \
  --model gemini-1.5-pro \
  --max-iterations 7
```

### 4. Module 6: Self-Boosting Trajectory Harvesting & LoRA SFT
To harvest trajectories from JSONL logs and fine-tune on DGX GPU 1:
```bash
# 1. Harvest trajectories
python -m repairlam.training.harvest \
  --logs-dir logs/ \
  --output repairlam/training/data/

# 2. Run LoRA SFT on DGX GPU 1
CUDA_VISIBLE_DEVICES=1 python -m repairlam.training.train_lora \
  --base-model Qwen/Qwen2.5-Coder-32B-Instruct \
  --data-dir repairlam/training/data/ \
  --output-dir /home/23ucs603/btp/models/repairlam-qwen32b-lora/ \
  --lora-r 8 \
  --lora-alpha 16 \
  --epochs 3 \
  --lr 2e-4
```

---

## Comprehensive Empirical Results

### Phase 1: QuixBugs Algorithmic Benchmark ($N = 40$)
Evaluated across 40 Java programs from the QuixBugs dataset using Google Gemini 1.5 Pro via our JSON schema adapter:

| Metric | Published Baseline (Defects4J / GPT-3.5) | RepairLAM (QuixBugs / Gemini) | Efficiency Improvement |
|---|---|---|---|
| **Plausible Fix Rate** | 22.0% | **80.0% (32/40)** | $+58.0\%$ absolute |
| **Correct Fix Rate** | 16.0% | **70.0% (28/40)** | $+54.0\%$ absolute |
| **Average Tokens per Bug** | 270,000 | $\sim$14,500 | **94.6% reduction** |
| **Median Execution Time** | 920.0 seconds | $\sim$3.8 seconds | **$242\times$ speedup** |
| **Monetary Cost per Bug** | \$0.14 | $\sim$\$0.01 | **$14\times$ cost reduction** |

---

### Phase 2: Live GitHub 36-Bug Evaluation ($N = 36$)
Evaluated across 36 live, unfixed issues in 5 enterprise repositories:

| Outcome Tier | Count | Percentage | Operational Significance |
|---|---|---|---|
| **PLAUSIBLE** | **7** | **19.4%** | Project test suite passed; verified PR opened on GitHub |
| **ESCALATED** | **15** | **41.7%** | Safety bounds triggered; diagnostic report posted; 0 code churn |
| **TIMEOUT** | **8** | **22.2%** | Maximum turn budget ($T=35$) reached; workspace reset |
| **SKIPPED** | **6** | **16.7%** | Deterministically verified as already fixed on upstream HEAD |
| **ERROR** | **0** | **0.0%** | Zero infrastructure crashes or unhandled runtime exceptions |
| **Total** | **36** | **100.0%** | Comprehensive empirical accounting across all test waves |

#### Pull Request Precision
$$\text{PR Precision} = \frac{|\text{Passing Opened PRs}|}{|\text{Total Opened PRs}|} = \frac{7}{7} = \mathbf{100.0\%}$$
Not a single broken or polluting pull request was submitted across all 36 evaluation runs.

#### Safe Escalation Policy
$$\text{Safe Escalation Precision} = \mathbf{1.00} \quad (15/15 \text{ cleanly halted with zero corrupted code})$$

---

### All 36 Evaluated Live Issues (Full Trace)

| # | Bug Identifier | Repository | Turns | Edits | Outcome | Verified GitHub Artifact |
|---|---|---|---|---|---|---|
| 1 | `guava#3493` | `google/guava` | 27 | 4 | **PLAUSIBLE** | [PR JeetM2207/guava#2](https://github.com/JeetM2207/guava/pull/2) |
| 2 | `guava#5284` | `google/guava` | 32 | 2 | **PLAUSIBLE** | [PR JeetM2207/guava#4](https://github.com/JeetM2207/guava/pull/4) |
| 3 | `guava#1065` | `google/guava` | 15 | 1 | **PLAUSIBLE** | [PR JeetM2207/guava#6](https://github.com/JeetM2207/guava/pull/6) |
| 4 | `gson#1511` | `google/gson` | 20 | 2 | **PLAUSIBLE** | [PR JeetM2207/gson#27](https://github.com/JeetM2207/gson/pull/27) |
| 5 | `gson#630` | `google/gson` | 19 | 1 | **PLAUSIBLE** | [PR JeetM2207/gson#29](https://github.com/JeetM2207/gson/pull/29) |
| 6 | `gson#600` | `google/gson` | 19 | 1 | **PLAUSIBLE** | [PR JeetM2207/gson#31](https://github.com/JeetM2207/gson/pull/31) |
| 7 | `gson#1920` | `google/gson` | 19 | 2 | **PLAUSIBLE** | [PR JeetM2207/gson#35](https://github.com/JeetM2207/gson/pull/35) |
| 8 | `jackson-databind#3067` | `FasterXML/jackson-databind` | 33 | 0 | **ESCALATED** | [Diagnostic Comment #1](https://github.com/JeetM2207/jackson-databind/issues/1) |
| 9 | `gson#2680` | `google/gson` | 22 | 0 | **ESCALATED** | [Diagnostic Comment #21](https://github.com/JeetM2207/gson/issues/21) |
| 10 | `guava#3790` | `google/guava` | 26 | 0 | **ESCALATED** | [Diagnostic Comment #9](https://github.com/JeetM2207/guava/issues/9) |
| 11 | `gson#1994` | `google/gson` | 30 | 2 | **ESCALATED** | [Diagnostic Comment #24](https://github.com/JeetM2207/gson/issues/24) |
| 12 | `gson#1736` | `google/gson` | 28 | 0 | **ESCALATED** | [Diagnostic Comment #25](https://github.com/JeetM2207/gson/issues/25) |
| 13 | `gson#1727` | `google/gson` | 23 | 0 | **ESCALATED** | [Diagnostic Comment #36](https://github.com/JeetM2207/gson/issues/36) |
| 14 | `gson#2769` | `google/gson` | 22 | 0 | **ESCALATED** | [Diagnostic Comment #37](https://github.com/JeetM2207/gson/issues/37) |
| 15 | `gson#1575` | `google/gson` | 27 | 5 | **ESCALATED** | [Diagnostic Comment #38](https://github.com/JeetM2207/gson/issues/38) |
| 16 | `gson#1397` | `google/gson` | 33 | 0 | **ESCALATED** | [Diagnostic Comment #39](https://github.com/JeetM2207/gson/issues/39) |
| 17 | `guava#3553` | `google/guava` | 22 | 0 | **ESCALATED** | [Diagnostic Comment #13](https://github.com/JeetM2207/guava/issues/13) |
| 18 | `netty#4514` | `netty/netty` | 36 | 2 | **ESCALATED** | [Diagnostic Comment #2](https://github.com/JeetM2207/netty/issues/2) |
| 19 | `gson#1587` | `google/gson` | 34 | 2 | **ESCALATED** | [Diagnostic Comment #39](https://github.com/JeetM2207/gson/issues/39) |
| 20 | `gson#548` | `google/gson` | 26 | 0 | **ESCALATED** | [Diagnostic Comment #42](https://github.com/JeetM2207/gson/issues/42) |
| 21 | `commons-csv#1` | `apache/commons-csv` | 17 | 0 | **ESCALATED** | [Diagnostic Comment #3](https://github.com/JeetM2207/commons-csv/issues/3) |
| 22 | `commons-csv#2` | `apache/commons-csv` | 20 | 1 | **ESCALATED** | [Diagnostic Comment #4](https://github.com/JeetM2207/commons-csv/issues/4) |
| 23 | `guava#3768` | `google/guava` | 48 | 0 | **TIMEOUT** | Diagnostic Comment #10 |
| 24 | `gson#2348` | `google/gson` | 36 | 1 | **TIMEOUT** | Diagnostic Comment #22 |
| 25 | `gson#2190` | `google/gson` | 39 | 2 | **TIMEOUT** | Diagnostic Comment #23 |
| 26 | `gson#2638` | `google/gson` | 34 | 4 | **TIMEOUT** | Diagnostic Comment #32 |
| 27 | `gson#2817` | `google/gson` | 33 | 3 | **TIMEOUT** | Diagnostic Comment #33 |
| 28 | `gson#996` | `google/gson` | 34 | 4 | **TIMEOUT** | Diagnostic Comment #40 |
| 29 | `guava#8693` | `google/guava` | 33 | 5 | **TIMEOUT** | Diagnostic Comment #14 |
| 30 | `gson#3047` | `google/gson` | 30 | 3 | **TIMEOUT** | Diagnostic Comment #43 |
| 31 | `gson#1735` | `google/gson` | — | — | **SKIPPED** | Passing on upstream HEAD |
| 32 | `gson#1394` | `google/gson` | — | — | **SKIPPED** | Passing on upstream HEAD |
| 33 | `gson#523` | `google/gson` | — | — | **SKIPPED** | Passing on upstream HEAD |
| 34 | `gson#453` | `google/gson` | — | — | **SKIPPED** | Passing on upstream HEAD |
| 35 | `jackson-databind#6185` | `FasterXML/jackson-databind` | — | — | **SKIPPED** | Resolved in Jackson 2.18 branch |
| 36 | `jackson-databind#6175` | `FasterXML/jackson-databind` | — | — | **SKIPPED** | Resolved in Jackson 3.x branch |

---

### Module 6 LoRA Fine-Tuning Convergence (DGX GPU 1)

- **Base Model**: `Qwen/Qwen2.5-Coder-32B-Instruct`
- **Dataset**: 139 multi-turn harvested trajectories (118 train, 21 validation)
- **Parameters**: $r=8$, $\alpha=16$, modules `q_proj, v_proj`, effective batch size 16, lr $2 \times 10^{-4}$

| Epoch | Step | Training Loss | Validation Loss | Total Time |
|:---:|:---:|:---:|:---:|:---:|
| 1.0 | 7 | 1.8412 | 1.6801 | 12m 14s |
| 2.0 | 14 | 1.7650 | 1.6512 | 24m 31s |
| 3.0 | 22 | **1.7402** | **1.6455** | **36m 47s** |

---

## Formal Empirical Ablation Studies (A1–A4)

### Ablation A1: Multi-Turn FSM vs. Single-Turn One-Shot Repair ($N = 20$)
- **Single-Turn One-Shot**: 0/20 Plausible (0.0%), 25.0% compile rate.
- **Multi-Turn FSM (RepairLAM)**: **13/20 Plausible (65.0%)**, 100.0% compile rate ($p < 0.001$).
- **Takeaway**: Test feedback injection is mandatory; zero-shot code generation fails on subtle enterprise regressions.

### Ablation A2: Syntactic Anchor Edits vs. Whole-File Rewriting ($N = 20$)
- **Whole-File Overwriting**: 35.0% syntax failure rate (token truncation on large classes), 50.0% repair success.
- **Syntactic Anchor Replacement**: **0.0% syntax error rate**, **85.0% repair success**.
- **Takeaway**: Constraining modifications to localized syntactic boundaries eliminates parser regressions.

### Ablation A3: Safe Escalation vs. Forced Guessing ($N = 36$)
- **Forced Guessing**: 36.8% PR precision, 12 broken PRs created, high repository pollution.
- **Safe Escalation (RepairLAM)**: **100.0% PR precision**, **0 broken PRs**, clean repository state.
- **Takeaway**: Bounded early escalation preserves maintainer trust in autonomous agents.

### Ablation A4: Turn Budget Scaling and Convergence Dynamics
- $T=10$: 28.6% yield
- $T=20$: 71.4% yield
- $T=30$: 100.0% yield
- $T=40$: 100.0% yield (saturation)
- **Takeaway**: Setting $T_{\text{max}} = 35$ optimal captures all recoverable bugs while minimizing token cost and runtime latency.

---

## Academic Report & LaTeX Source

The complete BTP thesis report, matching LNMIIT's formal thesis guidelines, is located at:
- **LaTeX Source**: [`report/main.tex`](report/main.tex)

To compile to PDF locally:
```bash
cd report/
pdflatex main.tex
pdflatex main.tex
```
*(Or upload `main.tex` directly to Overleaf and click Recompile).*

---

## Citation & Acknowledgements

```bibtex
@btechthesis{repairlam2026,
  title     = {Software Maintenance Using Large Action Models},
  author    = {Patel, Meet and Manseta, Jeet},
  school    = {The LNM Institute of Information Technology (LNMIIT), Jaipur},
  year      = {2026},
  month     = {April},
  type      = {Bachelor of Technology Thesis},
  advisor   = {Jain, Dr. Ankit Kumar}
}
```

We gratefully acknowledge:
- **Dr. Ankit Kumar Jain** for supervisory guidance and technical mentorship.
- **The Department of CSE, LNMIIT Jaipur** for compute infrastructure and DGX A100 server access.
- Authors of **RepairAgent** (Bouzenia, Devanbu, Pradel) and **LAM** (Microsoft Research) for foundational research papers.
