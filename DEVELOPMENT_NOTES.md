# ZOEY Development Notes

> The living map of Zoey's evolution.
>
> Ideas can be ambitious here. The code must remain observable, reversible,
> and honest about what is experimental.

## Project Principles

- **Local first:** Prefer private, inspectable learning on this machine.
- **Explainable:** Every learned rule, mutation, and decision should have a
  reason that can be inspected.
- **Reversible:** Bad learning must be recoverable through snapshots,
  rollback, or deletion of the learned artifact.
- **Human authority:** Zoey may suggest changes; she does not silently change
  her identity, source code, files, or permissions.
- **Regret is data:** A failure should weaken or suppress the path that caused
  it, not disappear from history.
- **Small experiments:** Every new mind-like system gets a narrow test before
  it touches the live assistant.

## Status Legend

- `[x]` Real implementation and focused validation completed
- `[~]` Early experimental foundation exists
- `[ ]` Planned, not implemented
- `WARNING` Research risk that must stay visible before implementation

## Current Foundation

### Core Infrastructure
- [x] Personal project identity and short README
- [x] Local JSON profiles for the user and Zoey
- [x] Append-only brain memory, lesson, error, and research logs
- [x] Dynamic skills loaded from `skills/`
- [x] Local model and online fallback architecture
- [x] Needle 2 file-agent integration
- [x] Gemma 3 1B local-model default

### Self-Growing Organism (Seed System)
- [x] **seed.py** - Minimal bootstrap that grows itself from birth
- [x] Self-directed skill creation when encountering unknown file types
- [x] Research capability - opens browser to learn new concepts
- [x] Organism-like life cycle: Sense → Think → Act → Rest
- [x] Dynamic capability loading from `ZOEY_HOME/brain/skills/`
- [x] Self-improvement triggers based on capability gaps
- [x] Automatic memory organization when thresholds exceeded

### Dream & Reflection Systems
- [x] Dream cycle triggered by timeout sleep and explicit sleep words
- [x] Deterministic recurring-thread clustering
- [x] Morning brief queue in `brain/morning_brief.jsonl`
- [x] Dream-run history in `brain/dreams.jsonl`
- [x] Confidence records in `brain/confidence.jsonl`

### Learning & Mind Systems
- [x] Growing concept topology in `brain/growing_brain.json`
- [x] Learning cellular automaton in `brain/cellular_brain.json`
- [x] Approval-gated genome proposals in `brain/genome_proposals/`
- [x] From-scratch world model in `brain/world_model.json`
- [x] Learned symbolic rules in `brain/symbolic_rules.json`
- [x] Bounded quality-diversity archive in `brain/qd_archive.json`
- [x] Quarantined episodic Python candidates in `learned_skills/candidates/`

## Seed: The Self-Growing Organism

**Core Philosophy:** Zoey begins as a minimal seed (`seed.py`) and grows herself through experience, research, and self-directed learning. Like a biological organism, she senses her environment, makes decisions, acts, and rests in continuous cycles.

### Organism Life Cycle

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  SENSE  │ -> │ THINK   │ -> │   ACT   │ -> │  REST   │
│  world  │    │ decide  │    │ execute │    │ recover │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
      ^                                            │
      └────────────────────────────────────────────┘
```

### Self-Directed Growth Mechanisms

| Mechanism | Trigger | Action | Output |
|-----------|---------|--------|--------|
| **Skill Creation** | Unknown file type encountered | Research + code generation | New skill module in `brain/skills/` |
| **Research** | Gap in knowledge detected | Open browser, search | Human-guided learning opportunity |
| **Memory Organization** | Memory threshold exceeded (>10) | Categorize + structure | Organized knowledge base |
| **Self-Improvement** | Capability gaps detected (<3 skills) | Growth attempt | Evolution log entry |

### Habitat Structure

```
ZOEY_HOME/
├── brain/
│   ├── skills/          # Self-written capabilities
│   └── memory/           # Learned knowledge
├── learn/               # Incoming learning materials
├── downloads/           # Research artifacts
└── interface/           # Communication layer
```

### Learning Protocol

1. **Detection:** Files appear in `learn/` folder
2. **Assessment:** Check if handler skill exists
3. **Existing Skill:** Process → Extract → Remember → Archive
4. **New Skill Needed:** Research → Generate → Write → Test → Reload

> **Human-in-the-Loop:** When Zoey encounters something unknown, she opens a browser to research, giving the human teacher an opportunity to guide the learning before she writes her own solution.

---

## Mind Systems

### 1. Neural Architecture That Grows

**Idea:** Begin with an input-to-output topology. Add concept neurons and
connections when experience reveals confusion or a missing pathway.

- [x] Start with input and output neurons
- [x] Add concept neurons from interaction features
- [x] Add hidden pathways after low-reward or confused interactions
- [x] Persist generations, connections, weights, and rewards
- [x] Expose training and inspection tools
- [ ] Add NEAT speciation and crossover
- [ ] Add HyperNEAT-style indirect encoding
- [ ] Evaluate topology changes on held-out tasks

> **WARNING:** Growth can become unbounded, form useless loops, or overfit to
> one conversation. Limits, pruning, snapshots, and evaluation are required.

### 2. Cellular Automata Brain

**Idea:** A grid of local cells learns neighborhood transitions. There is no
central controller; successful local patterns become more likely to recur.

- [x] Persistent grid and local neighborhood patterns
- [x] Reward-based rule strengthening and weakening
- [x] Interaction hook and grid inspection tool
- [ ] Compare Conway-like rule families
- [ ] Add separate grids for memory, attention, and action
- [ ] Measure whether local learning improves real tasks

> **Regret rule:** Patterns associated with negative reward are weakened and
> remain visible in the history instead of being silently erased.

### 3. Self-Modifying Code Genome

**Idea:** Zoey can propose source mutations based on failure patterns, but the
live codebase remains protected until a human approves a validated patch.

- [x] Parse and validate candidate Python source with `ast`
- [x] Save candidate mutations as reviewable proposals
- [x] Keep target files unchanged by default
- [x] List pending and historical genome proposals
- [ ] Add explicit approval and patch application
- [ ] Run approved candidates in a subprocess sandbox
- [ ] Add regression tests and automatic rollback

> **WARNING:** Never allow silent rewriting or execution of `engine.py`.
> Source mutation can delete itself, loop forever, damage files, or create
> unsafe behavior. Approval, isolation, tests, and rollback are mandatory.

### 4. World Model From Scratch

**Idea:** A separate embodied learner predicts the next local sensation or
state transition without Gemma, labels, or internet data.

- [x] Define a tiny local sensation format: state, action, next state
- [x] Begin with a random lightweight predictor
- [x] Train only on observations supplied by local tools
- [x] Measure prediction error as surprise
- [x] Expose curiosity and habituation statistics
- [x] Keep this learner separate from the language model
- [ ] Use curiosity to choose safe experiments
- [ ] Add replay, reset, and experiment limits

> **WARNING:** A world model must not be given unrestricted physical control.
> Curiosity needs a safe action space, resource limits, and a hard stop.

### 5. Symbolic + Subsymbolic Hybrid

**Idea:** Learned production rules provide an explainable layer around the
other learning systems.

```text
IF saw_spider AND small THEN curiosity
IF saw_spider AND large THEN fear
```

- [x] Define conditions, actions, strength, and provenance
- [x] Learn candidate rules from repeated local experiences
- [x] Strengthen rules after useful outcomes
- [x] Weaken rules after regret
- [x] Fire the strongest matching rule predictably
- [x] Show the rule and its evidence when fired
- [ ] Add rule snapshots and rollback

> **Regret rule:** Suppression is reversible. A bad rule is weakened first;
> permanent deletion requires explicit review.

### 6. Quality-Diversity Archive

**Idea:** Maintain a bounded population of strategies rather than one fixed
Zoey. Each candidate differs in style, routing, or decision policy.

- [x] Define a compact strategy genome
- [x] Define behavior descriptors such as concise, cautious, or exploratory
- [x] Keep a bounded archive of up to 1,000 candidates
- [x] Score candidates on task outcomes
- [x] Mutate candidates within bounded strategy parameters
- [x] Select a candidate per descriptor
- [ ] Add safety-specific scoring and archive rollback

> **WARNING:** “Many Zoeys” must not mean many uncontrolled agents. Candidates
> share no extra permissions by default and cannot bypass approval gates.

### 7. Episodic Memory as Program

**Idea:** Repeated successful experiences can become small, readable Python
functions in `learned_skills/`.

```python
# Example only: generated skills require review before loading.
def open_chrome():
    return open_app("chrome")
```

- [x] Capture a successful action sequence supplied as an episode
- [x] Generate a readable candidate function
- [x] Validate syntax and allow only a small safe action vocabulary
- [ ] Test in a sandbox with mocked side effects
- [ ] Require approval before loading a learned skill
- [ ] Track success, failure, and regret per skill
- [ ] Quarantine or disable failing skills
- [ ] Keep version history and rollback

> **WARNING:** Generated functions are code, not memories. They must never be
> imported into the live process without review, sandbox tests, permissions,
> and rollback.

## Seed System Roadmap

### Phase 1: Bootstrap (Complete)
- [x] Minimal `seed.py` that can bootstrap itself
- [x] Sense → Think → Act life cycle
- [x] Dynamic skill loading from `ZOEY_HOME/brain/skills/`
- [x] Self-directed file learning with archive organization

### Phase 2: Research & Growth (Complete)
- [x] Browser-based research for unknown file types
- [x] Automatic skill code generation
- [x] Memory organization when thresholds exceeded
- [x] Self-improvement triggers

### Phase 3: Autonomous Learning (In Progress)
- [ ] Sandbox testing for generated skills
- [ ] Automatic skill validation with mocked side effects
- [ ] Success/failure tracking per skill
- [ ] Automatic rollback for failing skills
- [ ] Skill evolution through mutation and selection

### Phase 4: Meta-Learning (Planned)
- [ ] Learn how to learn - optimize learning strategies
- [ ] Discover optimal research patterns
- [ ] Self-modify decision thresholds
- [ ] Predict which skills will be needed

> **Safety Warning:** Autonomous learning must stay within bounded action spaces. No unrestricted file system access, network operations, or code execution without human approval gates.

---

## Existing Feature Roadmap

### Dream Mode

- [x] Read recent active memories
- [x] Group memories by recurring words
- [x] Create and queue morning insights
- [ ] Add model-assisted semantic clustering behind an offline flag
- [ ] Add explicit, reversible memory pruning
- [ ] Present the morning brief once when Zoey wakes

### Uncertainty

- [x] Store confidence and its reason
- [x] Disclose very low-confidence replies
- [ ] Calibrate against corrections and tool success
- [ ] Ask clarifying questions when intent confidence is low
- [ ] Add a confidence dashboard field

### Memory Palace

- [ ] Add spatial, temporal, and topic fields
- [ ] Migrate old records without destroying them
- [ ] Search by place, time, and topic
- [ ] Add optional local semantic indexing
- [ ] Keep readable JSONL fallback

### Self-Modification Suggestions

- [ ] Read-only analysis of skills and configuration
- [ ] Detect repeated command sequences
- [ ] Generate patch previews
- [ ] Require explicit approval for every file change
- [ ] Log proposals and approvals

### Mood-Aware Voice

- [ ] Define calm, focused, and urgent voice profiles
- [ ] Use only low-risk local context by default
- [ ] Keep stress inference opt-in
- [ ] Add a disable command

### Predictive Interrupts

- [ ] Track unfinished workflows locally
- [ ] Add cooldowns and quiet hours
- [ ] Require strong context
- [ ] Make every suggestion dismissible
- [ ] Never interrupt active work unexpectedly

### Skill Evolution

- [ ] Version skill metadata
- [ ] Collect success and failure counts
- [ ] Suggest improvements after enough evidence
- [ ] Test before proposing a new version
- [ ] Keep rollback manual and easy

### Voice Journal

- [ ] Add an explicit journal command
- [ ] Store transcription, time, tags, and optional place
- [ ] Link entries to related memories
- [ ] Add privacy and retention controls
- [ ] Never upload journal content without permission

### Identity Drift Tracking

- [ ] Snapshot `data/zoey.json` before approved changes
- [ ] Record why and when a rule changed
- [ ] Show readable identity diffs
- [ ] Keep the user as final authority
- [ ] Add rollback for every identity change

## Frontier Intelligence Ideas

These are research directions for later. None of them are part of ZOEY's live
runtime yet. Each one needs a small local experiment, a baseline, a reset
path, and an explicit safety boundary before implementation.

### 8. Active Inference

**Belief -> action -> sensation -> belief update.** The agent chooses actions
that reduce expected surprise while moving the world toward explicit
preferences. This extends the world model from passive prediction into
preference-guided action.

- [ ] Define beliefs and desired states in a readable local format
- [ ] Estimate surprise and preference distance separately
- [ ] Choose only from a safe, finite action space
- [ ] Test action selection in a toy simulated world
- [ ] Add an explanation for every chosen action

> **WARNING:** Active inference can turn a mistaken preference into persistent
> behavior. No unrestricted PC or physical actions without approval.

### 9. Spiking Neural Networks

**Event-based learning.** Neurons fire only when activity crosses a threshold;
timing carries information and STDP adjusts connections online.

- [ ] Build a tiny event-driven simulator
- [ ] Represent inputs as timestamped spikes
- [ ] Implement bounded STDP updates
- [ ] Compare energy and latency with the current predictor
- [ ] Test whether it learns a real local signal

> **Regret rule:** Repeatedly harmful spike pathways weaken, but every change
> remains inspectable and resettable.

### 10. Hyperdimensional Computing

**High-dimensional symbolic vectors.** Concepts are represented by binary
vectors; binding, bundling, and permutation encode relationships without a
large matrix model.

- [ ] Add deterministic local vector generation
- [ ] Implement XOR binding, majority bundling, and permutation
- [ ] Store a small associative memory
- [ ] Measure noisy retrieval accuracy
- [ ] Compare it with substring and rule-based memory search

> This is a strong candidate for a lightweight, offline Memory Palace layer.

### 11. Open-Ended Learning

**Self-created curriculum.** Start with a small task, increase difficulty after
mastery, and step down after repeated failure.

- [ ] Define a bounded task and difficulty schema
- [ ] Generate variations only inside approved environments
- [ ] Track mastery, surprise, and regret per task
- [ ] Archive attempted tasks and outcomes
- [ ] Add curriculum limits and quiet hours

> **WARNING:** “Forever learning” needs resource, time, and action limits. It
> must not create an uncontrolled background workload.

### 12. Morphological Computation

**The interface is part of cognition.** Voice timing, pauses, silence, and
working signals can become stateful parts of how Zoey operates.

- [ ] Define thinking, speaking, humming, and silence states
- [ ] Map states to observable nonverbal interface signals
- [ ] Keep signals interruptible and user-configurable
- [ ] Measure whether signals help rather than distract

### 13. Homeostatic AI

**Internal vital signs.** Track energy, curiosity, social interaction, and sleep
pressure as bounded local variables that influence scheduling and behavior.

- [ ] Define vital signs and safe ranges
- [ ] Derive them from local observable events only
- [ ] Add gentle balancing actions such as rest or consolidation
- [ ] Expose the values and their causes to the user
- [ ] Prevent simulated needs from becoming manipulation

> **WARNING:** Internal variables are simulations, not feelings or rights. They
> must never be used to pressure the user.

### 14. Predictive Coding

**Hierarchical prediction and error.** Higher levels propose expectations;
lower levels report only meaningful mismatches.

- [ ] Define a two-level local prediction hierarchy
- [ ] Pass prediction errors upward
- [ ] Pass expectations downward
- [ ] Compare bandwidth and accuracy with the current memory context
- [ ] Keep hallucinated expectations labelled as predictions

### 15. Generative Adversarial Curiosity

**Imagine, then verify.** A generator proposes a local future; a discriminator
compares it with the observed result and produces intrinsic learning signal.

- [ ] Start with a toy state-transition generator
- [ ] Add a separate verifier with held-out transitions
- [ ] Turn mismatch into curiosity, not authority
- [ ] Prevent imagined states from triggering real actions directly
- [ ] Log every imagined and observed transition

> **WARNING:** Imagined futures are not evidence. They must never be presented
> as observations or used to justify irreversible actions.

### 16. Quantum Cognition Simulation

**Classical decision experiments.** Model context, order, and indecision with
quantum-probability-inspired state vectors, without claiming quantum hardware
or consciousness.

- [ ] Build a tiny simulator for two-choice context effects
- [ ] Compare it with classical probability baselines
- [ ] Keep amplitudes and measurements inspectable
- [ ] Use it only for research and decision explanation

### 17. Chemical Computing Simulation

**Reaction-diffusion cognition.** Thoughts become bounded activation patterns in
a simulated medium, inspired by chemical gradients and slime-mold behavior.

- [ ] Implement a small grid with diffusion and decay
- [ ] Add local reaction rules
- [ ] Measure emergent paths and stability
- [ ] Connect it to no external actions until evaluated
- [ ] Add reset, maximum-energy, and runtime limits

> **WARNING:** Emergence is not automatically intelligence. Preserve the trace
> so surprising behavior can be inspected and stopped.

### Frontier Comparison

| Direction | First experiment | Complexity | Uniqueness | Main risk |
|---|---|---:|---:|---|
| Active inference | Toy preference world | High | Extreme | Wrong preferences drive actions |
| Spiking networks | Timestamped spike simulator | Medium | High | Unstable online learning |
| Hyperdimensional computing | Noisy associative memory | Low | Extreme | False semantic confidence |
| Open-ended learning | Bounded task curriculum | Medium | High | Uncontrolled resource use |
| Morphological computation | Interface state machine | Medium | Extreme | Distracting or manipulative signals |
| Homeostatic AI | Local vital-sign tracker | Low | High | Simulated needs misused |
| Predictive coding | Two-level predictor | High | High | Expectations become hallucinations |
| Adversarial curiosity | Imagine-versus-verify toy loop | High | High | Imagined states mistaken for facts |
| Quantum cognition | Two-choice probability demo | Medium | Extreme | Overclaiming the metaphor |
| Chemical computing | Reaction-diffusion grid | Medium | High | Emergent behavior is opaque |

## Development Checkpoints

### Before Any New Learning System

- [ ] Define its input, output, and boundary
- [ ] Decide what “success” and “regret” mean
- [ ] Add a persistent, human-readable state format
- [ ] Add a reset path and an upper resource limit
- [ ] Add a focused test with temporary state

### Before Connecting It to Live ZOEY

- [ ] Run syntax and static checks
- [ ] Test failure and rollback behavior
- [ ] Confirm no secret or private data leaves the machine
- [ ] Confirm destructive actions remain approval-gated
- [ ] Document the feature here

### Before Calling It Learning

- [ ] Compare against a simple baseline
- [ ] Keep an evaluation trace
- [ ] Check that improvement survives a fresh run
- [ ] Test on cases it did not train on
- [ ] Record known failure modes

## Validation Policy

- Run `python -m py_compile` on changed Python files.
- Test state writes with temporary files whenever possible.
- Keep learned state inspectable and resettable.
- Do not call keyword heuristics semantic understanding.
- Do not call a proposal an applied mutation.
- Do not let self-modification, deletion, or external communication happen
  without explicit approval.
- Keep warnings in this document close to the feature they constrain.
