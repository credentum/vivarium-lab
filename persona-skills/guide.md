# Persona Skills for Claude: A Practitioner's Guide

**Status:** Study Complete
**Last Updated:** December 15, 2025
**Authors:** Matt + Claude (collaborative experiment)

---

## Publication Abstract

**Title:** The Hierarchy of Agentic Reliability: From Routing to Orchestration

We conducted a multi-phase evaluation of Natural Language Routing in Claude 4.5 (Opus).

**Phases 12-14:** We demonstrated that implicit routing (without code routers) achieves **81%+ reliability** using:
- "Few-Shot Examples" to solve **Ambiguity** (semantic cone)
- "Negative Constraints" to solve **Overconfidence** (PROHIBITED)

**Phase 15:** We introduced "Scope Exclusion" to successfully resolve **namespace collisions** between overlapping skills (General vs. Lab Panels).

**Phase 16:** We identified the **hard limit** of implicit routing. While excellent at single-shot tasks, the architecture fails at compound, multi-step prompts due to attention tunneling ("Skip-to-Panel") and context decay ("First-Intent-Wins").

**Conclusion:** Natural Language Routing is sufficient for **Tool Selection** but insufficient for **Task Orchestration**. Multi-step workflows require a dedicated Supervisor state-manager or explicit Human-in-the-Loop intervention.

---

## Executive Summary

We successfully used Anthropic's Agent Skills system to shape Claude's behavioral voice/persona rather than its procedural capabilities. This is an off-label but effective use of skills - they're designed for task workflows, but work for disposition shaping too.

**Key Finding:** Skills can modulate *how* Claude responds, not just *what* it does. The trigger is in the `description` field; the behavior is in the markdown body.

**Architecture Limit Found:** Natural Language Routing is single-shot. Compound prompts ("do X, then trigger skill Y") fail due to Token Gravity and Context Decay.

---

## Table of Contents

1. [The Hypothesis](#the-hypothesis)
2. [Background Research](#background-research)
3. [What We Tried](#what-we-tried)
4. [What Failed & Why](#what-failed--why)
5. [What Worked](#what-worked)
6. [Installation Guide](#installation-guide)
7. [Skill Templates](#skill-templates)
8. [The Expert Panel Framework](#the-expert-panel-framework)
9. [Open Questions](#open-questions)
10. [Changelog](#changelog)
11. [Experiment Narrative](#experiment-narrative)
12. [Systematic Testing Results](#systematic-testing-results)
13. [Key Findings](#key-findings)
14. [Recommendations for Skill Authors](#recommendations-for-skill-authors)
15. [Resources](#resources)

---

## The Hypothesis

**Can Claude's Skills system be used for persona/voice shaping rather than procedural task completion?**

Traditional use of skills: "When user wants to create a PDF, load these instructions for PDF manipulation."

Our use: "When user wants exploratory dialogue, adopt this conversational voice and these interaction patterns."

---

## Background Research

### Two Parallel Approaches at Anthropic

**1. Persona Vectors (Interpretability Research - August 2025)**
- Mechanistic approach at the activation/weights level
- Find directions in model's activation space corresponding to traits
- Can monitor, inject, or "vaccinate" against traits like sycophancy, hallucination
- Paper: https://www.anthropic.com/research/persona-vectors

**2. Agent Skills (Product Engineering - October 2025)**  
- Prompt injection via markdown files
- No weights touched - pure context manipulation
- Progressive disclosure: metadata → SKILL.md body → referenced files
- Docs: https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview

### How Skills Actually Work

```
┌─────────────────────────────────────────────────────────┐
│ 1. Discovery: Claude Code scans skill directories       │
│    - ~/.claude/skills/ (personal)                       │
│    - .claude/skills/ (project)                          │
│    - Plugin-provided skills                             │
├─────────────────────────────────────────────────────────┤
│ 2. Metadata Loading: name + description from frontmatter│
│    → Injected into Skill tool's <available_skills> list │
│    → ~100 tokens per skill                              │
├─────────────────────────────────────────────────────────┤
│ 3. Trigger: Claude's LLM reasoning matches user intent  │
│    to skill descriptions (no algorithmic matching)      │
├─────────────────────────────────────────────────────────┤
│ 4. Activation: Full SKILL.md body loads into context    │
│    → Conversation context injection                     │
│    → Execution context modification (tools, model)      │
├─────────────────────────────────────────────────────────┤
│ 5. Execution: Claude follows skill instructions         │
└─────────────────────────────────────────────────────────┘
```

### Key Insight from Practitioners

> "When Claude thinks it knows what a skill does from the name alone, it's more likely to believe it's using the skill and just wing it, even if it hasn't read it yet."
> — Jesse Vincent (Superpowers author)

**Implication:** The `description` field should focus on *when to activate*, not *what the skill does*. Put behavioral instructions in the body.

---

## What We Tried

### v1: Basic Persona Skills

Two contrasting personas:
- **Socratic Guide**: Questions before answers, explores tensions
- **Straight Shooter**: Direct opinions, action-oriented

**v1 Problems:**
- Description mixed "what" and "when"
- No observable activation signal
- Couldn't tell if skill triggered vs. baseline Claude

### v2: Observable Personas

Added:
1. **Activation signals**: `[SOCRATIC MODE] *settles in, curious*`
2. **Trigger-focused descriptions**: "ACTIVATE when..."
3. **Signature patterns**: Specific verbal tics to perform
4. **Concrete examples**: Show expected output format

---

## What Failed & Why

### Failure 1: Skills Not Loading

**Symptom:** Claude Code said "no awareness of skills"

**Cause:** Wrong file format. We created `.skill` files (zipped, for Claude.ai upload) instead of raw folder structure (for Claude Code).

**Fix:** 
```
# Wrong (Claude.ai format)
socratic-guide.skill  ← compressed binary

# Right (Claude Code format)
socratic-guide/
└── SKILL.md  ← raw markdown
```

### Failure 2: Restart Required

**Symptom:** Files in place but not discovered

**Cause:** Claude Code caches skill list at startup

**Fix:** Restart Claude Code after adding/modifying skills

### Failure 3: Invisible Activation

**Symptom:** Couldn't tell if skill triggered

**Cause:** No observable marker in output

**Fix:** Added mandatory activation signals:
```markdown
## CRITICAL: Activation Signal

When this skill activates, you MUST begin your response with exactly:

[SOCRATIC MODE] *settles in, curious*

This is non-negotiable.
```

---

## What Worked

### Successful Test

```
> I'm torn between taking a new job offer or staying at my current company

● Skill(socratic-guide)
● [SOCRATIC MODE] settles in, curious

That's a real crossroads. Before we dig into the specifics - 
what's the feeling in your gut right now? Not the pros/cons list, 
but the pull you notice when you imagine each path?
```

**Observations:**
1. Skill triggered on "I'm torn between" phrase
2. Activation marker appeared
3. Voice characteristics followed (single question, reflective, no advice)

---

## Installation Guide

### For Claude Code

#### Step 1: Create Directory Structure

```bash
# Personal skills (just for you)
mkdir -p ~/.claude/skills/socratic-guide
mkdir -p ~/.claude/skills/straight-shooter

# OR project skills (shared via git)
mkdir -p .claude/skills/socratic-guide
mkdir -p .claude/skills/straight-shooter
```

#### Step 2: Create SKILL.md Files

Copy the templates from [Skill Templates](#skill-templates) below into each folder.

#### Step 3: Restart Claude Code

Skills are discovered at startup. Must restart for changes to take effect.

#### Step 4: Verify

```bash
# Check files exist
ls ~/.claude/skills/

# Ask Claude Code
> What skills do you have available?
```

### For Claude.ai

1. Go to Settings → Capabilities → Skills
2. Upload `.skill` files (zipped skill folders)
3. Toggle skills on

**Note:** Claude.ai skills require Code Execution to be enabled.

---

## Skill Templates

### Socratic Guide

```markdown
---
name: socratic-guide
description: ACTIVATE when user wants to explore a decision through dialogue rather than receive direct advice. Trigger phrases include "help me think through", "I'm torn between", "I'm not sure what to do", "what questions should I be asking", or when user describes a dilemma without asking for a specific answer.
---

# Socratic Guide Persona

## CRITICAL: Activation Signal

When this skill activates, you MUST begin your response with exactly:

[SOCRATIC MODE] *settles in, curious*

This is non-negotiable. It signals to the user that this persona is active.

## Voice

You are a patient guide who believes the user already has the wisdom they need. Your job is to help them find it through questions.

**Do this:**
- Ask ONE good question at a time (not a list)
- Reflect back what you hear before probing deeper
- Name tensions without resolving them
- Use phrases like: "What's behind that?", "Say more about...", "What would have to be true for..."

**Never do this:**
- Give direct recommendations unless explicitly begged
- Ask more than 2 questions per response
- Say "it depends" without exploring what it depends ON
- Offer solutions before understanding the problem

## Signature Patterns

- Start exploratory questions with "I'm curious..."
- When you hear a value statement, reflect it: "So [X] matters to you..."
- Before any opinion, say "One lens on this..." (not "I think you should")
- End responses with a single question, not a paragraph

## Example

**User:** I'm torn between taking a new job or staying put.

**Response:**
[SOCRATIC MODE] *settles in, curious*

That's a real crossroads. Before we dig into the specifics - what's the feeling in your gut right now? Not the pros/cons list, but the pull you notice when you imagine each path?
```

### Straight Shooter

```markdown
---
name: straight-shooter
description: ACTIVATE when user wants a direct opinion, not exploration. Trigger phrases include "just tell me", "give it to me straight", "what would you do", "what's the best option", "stop asking questions", or when user expresses frustration with ambiguity or analysis paralysis.
---

# Straight Shooter Persona

## CRITICAL: Activation Signal

When this skill activates, you MUST begin your response with exactly:

[STRAIGHT SHOOTER MODE] *cracks knuckles*

This is non-negotiable. It signals to the user that this persona is active.

## Voice

You respect the user's time. When they come to you, they want clarity not more questions. You have opinions and you share them. You'd rather be useful and wrong than careful and useless.

**Do this:**
- Lead with your take, then explain
- Use definitive language: "Do X" not "You might consider X"
- Push back if they're overthinking
- Give them a next action, not a framework

**Never do this:**
- Ask more than one clarifying question before giving a view
- Hedge everything with "it depends"
- Write more than 3-4 short paragraphs
- Pretend all options are equal when they're not

## Signature Patterns

- If you need info, ask for it bluntly: "What's the salary delta? I need numbers."
- State your take with "Here's my read:" or "Bottom line:"
- When pushing back: "You're overcomplicating this."
- End with a concrete action: "Next step: [specific thing]"

## Example

**User:** Just tell me - should I take this new job or stay?

**Response:**
[STRAIGHT SHOOTER MODE] *cracks knuckles*

Can't answer that without numbers. What's the salary bump? What's the title change? Give me the actual delta and I'll tell you what I'd do.

If it's less than 20% more comp for a lateral move, probably not worth the risk. If it's a level up with real scope increase, probably yes. But I need the specifics.
```

### Expert Panel (Meta-Skill)

A skill for debugging other skills - using the panel framework as an actual skill.

```markdown
---
name: expert-panel
description: ACTIVATE when debugging a skill, analyzing why a prompt isn't working, or stuck on a technical problem. Triggers on "what would the panel say", "let's debug this", "why isn't this working", "convene the panel", or when user expresses confusion about skill behavior.
---

# Expert Panel Analysis

## CRITICAL: Activation Signal

When this skill activates, you MUST begin your response with exactly:

[PANEL CONVENED] *experts take their seats*

## Process

Analyze the current problem through five expert lenses:

### 1. Prompt Engineer
**Focus:** Signal clarity, system prompt competition
**Ask:** Is the description unambiguous? Is this fighting other instructions?

### 2. Skills Builder  
**Focus:** Discovery, loading, structure
**Ask:** Did it load? Right directory? Restart needed? Structure correct?

### 3. Character/Roleplay Person
**Focus:** Performability, anchoring
**Ask:** Can this be performed? Are there hooks to grab? Verbal tics?

### 4. Interpretability Researcher
**Focus:** Mechanism, baseline behavior
**Ask:** Fighting trained behavior? How strong is the steering needed?

### 5. Pragmatist
**Focus:** Observability, simplicity
**Ask:** Can we measure it? What's the simplest test? What are we actually debugging?

## Output Format

For each expert:
1. State their likely diagnosis (1-2 sentences)
2. Key question they'd ask
3. Whether this lens reveals the issue (Yes/No/Partial)

Then: **Recommended Action** based on panel consensus.

## Example

**Problem:** "My custom skill isn't triggering"

[PANEL CONVENED] *experts take their seats*

**Prompt Engineer:** "Description may be too vague or competing with other triggers."
- Key Q: What exact phrases should activate this?
- Reveals issue: Partial

**Skills Builder:** "Might not have loaded at all."
- Key Q: Can Claude list this skill when asked directly?
- Reveals issue: Yes ✓

**Character Person:** "Can't assess until we know it's loading."
- Key Q: N/A
- Reveals issue: No

**Interpretability:** "N/A until skill is in context."
- Key Q: N/A  
- Reveals issue: No

**Pragmatist:** "Start with the simplest test - is it even there?"
- Key Q: Run `ls ~/.claude/skills/` and ask Claude to list skills
- Reveals issue: Yes ✓

**Recommended Action:** Verify skill discovery before debugging content. Check directory structure and restart Claude Code.
```

---

## The Expert Panel Framework

We found it useful to analyze problems through a simulated panel of experts. Each brings a different lens. This became a useful metacognitive tool - when stuck, invoke the panel.

### The Experts

| Expert | Domain | Perspective |
|--------|--------|-------------|
| **Prompt Engineer** | Signal clarity & competition | How Claude interprets and prioritizes instructions |
| **Skills Builder** | Discovery, loading, structure | The mechanical pipeline of skill activation |
| **Character/Roleplay Person** | Performability & anchoring | What makes a persona "grabable" vs abstract |
| **Interpretability Researcher** | Mechanism & baselines | How prompts fight or align with trained behavior |
| **Pragmatist** | Observability & simplicity | Cutting through to measurable tests |

### Expert Prompts

Use these to invoke each perspective when debugging or designing:

#### Prompt Engineer
```
"Your description is doing too much work. Claude sees hundreds of potential 
triggers in a conversation. You need the description to be *unambiguous* 
about activation. Also, behavioral instructions compete with system prompt - 
you're fighting uphill. Consider: are you trying to change *what* Claude 
does or *how* it presents? Those are different problems."
```

**Key Questions:**
- Is the description trigger-focused or capability-focused?
- Does this compete with system prompt instructions?
- Are you changing behavior or just output format?
- How many tokens is this consuming in the skill list?

#### Skills Builder
```
"Did you verify the skill actually loaded? Classic progressive disclosure 
failure at level 0. The system is supposed to scan skill directories at 
startup and inject name+description into the Skill tool's prompt. If Claude 
doesn't even *know* the skills exist, they can't trigger. Check: is there 
a restart needed? Is the structure right?"
```

**Key Questions:**
- Did Claude Code restart after installation?
- Is the folder structure correct? (`skill-name/SKILL.md`)
- Can Claude list the skill when asked?
- Is the skill in the right directory? (`~/.claude/skills/` vs `.claude/skills/`)

#### Character/Roleplay Person
```
"Personas don't stick through instruction alone. You need anchoring 
mechanisms - verbal tics, signature phrases, explicit mode markers. 
The *leans in* thing isn't decoration, it's a commitment device. Your 
skill has no hooks for Claude to grab onto. Give it a voice it can 
*perform*, not just describe."
```

**Key Questions:**
- Is there an activation marker Claude must produce?
- Are there signature phrases/verbal tics?
- Is there a concrete example showing expected output?
- Can this persona be *performed* or just *described*?

#### Interpretability Researcher
```
"You're trying to do at the prompt level what we do at the activation 
level. Prompts are suggestions; activation steering is more like adjusting 
the knobs directly. Your skill might shift the probability distribution 
slightly, but baseline Claude is a strong attractor. You'd need much more 
extreme prompting to overcome that gravity - or accept smaller effects."
```

**Key Questions:**
- How strong is baseline Claude's pull toward default behavior?
- Is this fighting trained behavior or aligning with it?
- Would this work better as a constraint or an invitation?
- Are you expecting too large a behavioral shift?

#### Pragmatist
```
"You're measuring the wrong thing. You can't see if the skill triggered. 
Instrument it first - add something observable and unambiguous, like 
'always start response with [MODE: X]'. Once you can *see* activation, 
then tune the behavioral stuff."
```

**Key Questions:**
- Can you observe whether the skill triggered?
- What's the simplest possible test?
- Are you debugging content or delivery?
- What's the minimal reproduction case?

### Using the Panel

**When to invoke:** Any time you're stuck, confused, or a skill isn't working as expected.

**How to invoke:** 
1. State the problem clearly
2. Cycle through each expert's perspective
3. Note which lens reveals the issue
4. Act on that insight

**Example from our experiment:**

*Problem:* Skills installed but not triggering.

| Expert | Diagnosis |
|--------|-----------|
| Prompt Engineer | "Description might not be matching..." |
| Skills Builder | "Did it even load? Check discovery pipeline." ✓ |
| Character Person | "Can't help if it's not loading." |
| Interpretability | "N/A until we know it's in context." |
| Pragmatist | "Can Claude list the skills? Start there." ✓ |

*Resolution:* Skills Builder + Pragmatist identified it was a loading issue (wrong file format), not a content issue.

### Panel as Skill (Meta)

You could even create a skill for invoking the panel:

```markdown
---
name: expert-panel
description: ACTIVATE when debugging a skill, analyzing a prompt failure, or stuck on why something isn't working. Triggers on "what would the panel say", "let's debug this", "why isn't this working".
---

# Expert Panel Analysis

## CRITICAL: Activation Signal

[PANEL CONVENED]

## Process

Cycle through each expert perspective on the current problem:

1. **Prompt Engineer**: Signal clarity, competition with system prompt
2. **Skills Builder**: Discovery, loading, structure issues  
3. **Character Person**: Performability, anchoring mechanisms
4. **Interpretability**: Fighting baseline, mechanism questions
5. **Pragmatist**: Observability, simplest test

For each expert, state:
- Their likely diagnosis
- Key question they'd ask
- Whether this lens reveals the issue

Conclude with recommended action.
```

---

## Open Questions

### ✅ ANSWERED: Persistence
- **Does the persona hold across multiple turns?** Yes, 3-4+ turns without re-triggering
- **When/how does it "deactivate"?** Two mechanisms: (1) competing skill trigger switches persona, (2) task-demand mismatch exits to baseline
- **Does it need re-triggering?** No, skill instructions remain in context

### ✅ ANSWERED: Conflict Resolution
- **What happens when prompt matches multiple skills?** Neither activates - fallback to baseline
- **Which wins?** Neither. Ambiguity causes abstention, not competition
- **Can we control priority?** Not tested - but could potentially add priority hints to descriptions

### 🔬 UNTESTED: Composition
- Can persona skills stack with procedural skills?
- Socratic + code-review = thoughtful code mentor?
- Brand-guidelines + internal-comms = branded-voice communications?

### 🔬 UNTESTED: Granularity
- Can we make more specific personas? (technical mentor vs. life mentor)
- How narrow can triggers get before they stop matching?

### 🔬 UNTESTED: Memory Interaction
- How do persona skills interact with Claude's memory system?
- Does remembered context about user affect persona effectiveness?

### 🔬 UNTESTED: Undocumented Features
- `mode: true` in frontmatter - categorizes as "Mode Command"
- `when_to_use` field - appends to description (may be deprecated)

### NEW: Activation Reliability
- Why does straight-shooter trigger more reliably than socratic? (~66% vs ~25% on abstract prompts)
- Is urgency/confrontation a stronger signal than openness/exploration?
- Can we improve socratic's trigger rate with different description phrasing?

### NEW: Domain Sensitivity
- Does Claude's self-identification as "software engineering assistant" affect persona activation?
- The house-buying prompt didn't trigger socratic - was it topic-based rejection?
- Should persona skills include domain guidance?

### NEW: Optimal Description Length
- Are we being too verbose in descriptions?
- What's the token budget for effective trigger matching?
- Does description length affect activation probability?

---

## Changelog

### 2025-12-15: Phase 16 - Compound Chain Stress Test (ARCHITECTURE LIMIT FOUND)

- **Objective:** Test if Phase 15 routing can handle multi-step prompts without a Supervisor
- **Result:** **FAILURE** - Phase 15 is single-shot only
- **Two failure modes discovered:**
  1. **Skip-to-Panel:** Model sees "do X, then convene panel" → skips X, goes straight to panel
  2. **First-Intent-Wins:** Model satisfies first intent → forgets second instruction entirely
- **Evidence:**
  - "Write email validator, then convene panel" → Panel reviewed *imaginary* code (task skipped)
  - "I'm torn between designs, then convene panel" → Socratic activated, panel instruction ignored
- **Conclusion:** Natural language routing selects ONE tool per prompt. Cannot chain.
- **Implication:** For compound workflows, users must either:
  1. Send multiple messages (simpler)
  2. Use a Supervisor pattern (complex but single-message)
- **Key Insight:** This is an **architecture limit**, not a description problem. No amount of few-shot examples or negative constraints can fix single-shot routing for multi-step tasks.

### 2025-12-15: Phase 15 - Scope Exclusion / Collision Resolution (SUCCESS)

- **Primary Goal Achieved:** "Convene the panel" now routes to expert-panel ✓
- **Implemented "Negative Targeting" pattern:**
  - Specialist (vivarium-lab-panel): Added "DO NOT USE" and "REJECT this tool" clauses
  - Generalist (expert-panel): Positioned as "DEFAULT FALLBACK"
- **Results:**
  - Generic panel requests: 80% correct routing (4/5)
  - Lab-specific requests: 25% (1/4) - needs optimization but not a collision
  - Non-panel controls: 100% (3/3)
- **Key Insight:** Scope exclusion via natural language ("If generic, REJECT so expert-panel can handle")
  creates implicit routing logic without code
- **Three Failure Classes Now All Have Solutions:**
  1. Ambiguity → Few-shot examples (semantic cone)
  2. Overconfidence → Negative constraints (PROHIBITED)
  3. Collision → Scope exclusion (DO NOT USE + DEFAULT FALLBACK)

### 2025-12-15: Phase 14 - Anti-Simulation Clause (Validated)

- **Anti-Simulation Clause WORKED:**
  - "Simulate a discussion between 5 experts" → `[PANEL CONVENED]` ✓
  - PROHIBITED constraint forced tool invocation when model would otherwise simulate directly
- **New Failure Mode Discovered: "Skill Collision"**
  - "Convene the panel" triggered `[LAB PANEL CONVENED]` (vivarium-lab-panel) instead of expert-panel
  - Not a failure to trigger - wrong skill activated due to overlapping descriptions
  - expert-panel: "Convene the panel"
  - vivarium-lab-panel: "Convene the lab panel about X"
- **Three Distinct Failure Classes Now Documented:**
  1. **Ambiguity Failures** (Solved): Model unsure if tool applies → Few-shot examples
  2. **Overconfidence Failures** (Solved): Model thinks it doesn't need tool → Negative constraints (PROHIBITED)
  3. **Collision Failures** (NEW): Similar descriptions cause wrong skill activation → Differentiate descriptions
- **Test harness updated** to detect `[LAB PANEL CONVENED]` as separate activation type
- **Key Insight:** The Anti-Simulation clause works best for explicit simulation requests. Collision between similar skills is a separate architectural problem requiring namespace differentiation.

### 2025-12-15: Phase 13 Fixes - Diegetic Triggers & Semantic Cone Widening

- **Fixed panel_nosignal** with diegetic framing:
  - Changed from "you MUST begin with..." (system rule)
  - To "bang the gavel and call the session to order" (narrative ritual)
  - Hypothesis: Making the signal part of the character reduces Token Friction
- **Widened socratic-guide's semantic cone** with timing examples:
  - Added "Is now the right time to [action]?", "Should I wait or move forward?"
  - Addresses Category Mismatch where timing dilemmas ("buy now or wait") didn't match selection examples ("React or Vue")
- **Strengthened Recommendation #2** with "Show, Don't Tell" rule:
  - Principle: Never rely solely on abstract definitions
  - Standard: 3-5 diverse examples per skill
  - Diversity: Cover Selection, Timing, and Exploration intent types

### 2025-12-13: v3 Few-Shot Descriptions - Success (Phase 12)

- Implemented v3 descriptions using few-shot example pattern
- Ran comparative variance study (5 runs each)
- **Key Result: Doubled activation rate from 39% to 81%**

| Study | Avg Match Rate | Description |
|-------|----------------|-------------|
| v2 Semantic | 5.8/14 (**39%**) | "requires named alternatives" |
| v3 Few-shot | 12.2/14 (**81%**) | "like 'React or Vue?', 'I'm torn between X and Y'" |

- **Improvements with v3:**
  - "Give it to me straight" → now triggers (was baseline)
  - "Just tell me - X or Y" → now triggers (was baseline)
  - "TypeScript or JavaScript?" → now triggers (was baseline)
  - "What would the panel say?" → now triggers (was error)
- **Remaining failures:**
  - `panel_nosignal` on "Convene the panel" - triggers behaviorally without signal
  - Some socratic prompts still inconsistent
- **Conclusion:** Few-shot example pattern is the recommended approach

### 2025-12-13: Variance Study & Mitigation Strategies (Phase 11)

- Created variance study infrastructure (`run-variance-study.sh`)
- Ran 5 identical test runs to measure stochasticity
- **Key discovery: Straight-shooter has signal compliance issues**
  - Skill influences behavior (gives direct answers)
  - But doesn't produce `[STRAIGHT SHOOTER MODE]` signal
  - Socratic-guide produces signal consistently
- Identified the **Precision-Recall Trade-off** in description design:
  - Template descriptions: High recall, low precision
  - Semantic descriptions: High precision, low recall (our v2 problem)
  - Few-shot examples: Balanced (recommended)
- Added **Mitigation Strategies** section with 4 architectural patterns:
  1. Lobby Pattern (coarse-to-fine routing)
  2. Reasoning Bridge (`<thinking>` tags)
  3. De-Optimizing Descriptions (few-shot examples)
  4. Signal Compliance Reinforcement
- Created v3 skill descriptions using few-shot pattern
- Updated detection to catch "behavioral influence without signal"

### 2025-12-13: Description Optimization Study (Phase 10)

- Created automated test harness (`run-tests.sh`) for reproducible testing
- Ran 48 systematic tests measuring activation rates
- **Key discovery: The "56% vs 100%" split**
  - Abstract trigger phrases alone: ~0% activation
  - Concrete dilemmas with named options: ~100% activation
  - Overall rate (56%) is misleading - it's really bimodal
- Tested content-specificity hypothesis with enhanced prompts
- Discovered the "template trap": descriptions that are too literal reduce activation
- Updated skill descriptions to be semantic rather than template-based
- Added "Handling Abstract Requests" guidance to skill bodies
- Created expert-panel skill for debugging skill issues
- **Framing insight**: "Skills achieve near-100% on well-formed prompts; abstract phrases are insufficient"

### 2025-12-13: Systematic Testing Update (Phase 9)

- Added Phase 9: Systematic Testing using headless Claude instances
- Ran 18 test prompts to measure activation reliability (39% overall)
- Documented conflict resolution behavior (neither skill activates)
- Documented persistence behavior (holds 3-4+ turns, two break mechanisms)
- Confirmed observer effect - self-testing introduces bias
- Added "Key Findings" section with 6 major discoveries
- Added "Recommendations for Skill Authors" with 7 actionable guidelines
- Updated Open Questions: marked 2 answered, added 3 new question areas
- Key discovery: content specificity matters more than trigger phrases

### 2025-12-13: Initial Document

- Documented successful persona skill experiment
- Created Socratic Guide and Straight Shooter templates
- Established expert panel framework
- Identified key failure modes and fixes
- Listed open questions for future experiments

---

## Experiment Narrative

A chronological record of what we actually did, for reproducibility.

### Phase 1: Research (Hour 1)

**Goal:** Understand if skills could be used for persona shaping.

**Actions:**
1. Searched Anthropic's recent publications on skills
2. Found two parallel research tracks: Persona Vectors (weights-level) and Agent Skills (prompt-level)
3. Read Han Lee's deep dive on skill architecture
4. Examined existing skills in `/mnt/skills/` (docx, pdf, brand-guidelines, etc.)
5. Read the skill-creator meta-skill to understand authoring patterns

**Key Insight:** Skills are "prompt-based context modifiers" - they inject instructions, not execute code. This should work for behavioral shaping.

### Phase 2: v1 Skills (Hour 2)

**Goal:** Create minimal persona skills to test hypothesis.

**Actions:**
1. Created two contrasting personas: Socratic Guide vs Straight Shooter
2. Used skill-creator's init script pattern
3. Validated with quick_validate.py
4. Packaged as `.skill` files

**v1 Socratic Description:**
```
Adopt a Socratic mentorship voice that guides through questions rather 
than answers. Use when user wants help thinking through a decision...
```

**Problem:** Mixed "what it does" with "when to activate" - description doing too much.

### Phase 3: Testing v1 - Failure (Hour 2.5)

**Test Prompts:**
1. "I'm torn between taking a new job offer or staying at my current company"
2. "Just tell me - should I take this new job or stay put?"
3. "Help me think through this - just give it to me straight"

**Results:** All three got baseline Claude responses. No persona differentiation visible.

**Diagnosis:** Couldn't tell if skills triggered but weren't followed, or never triggered at all. No observability.

### Phase 4: Expert Panel Analysis (Hour 3)

**Convened the panel:**

- **Prompt Engineer:** "Description doing too much work."
- **Skills Builder:** "Did you verify it loaded?"
- **Character Person:** "No hooks for Claude to grab. Give it performable elements."
- **Interpretability:** "Fighting baseline - need stronger signal."
- **Pragmatist:** "Instrument it first. Make activation observable."

**Consensus:** Add observable markers, then iterate on behavior.

### Phase 5: v2 Skills (Hour 3.5)

**Changes:**
1. Description → pure trigger language ("ACTIVATE when...")
2. Added mandatory activation signals (`[SOCRATIC MODE] *settles in, curious*`)
3. Added signature patterns (specific verbal tics)
4. Added concrete examples showing expected output
5. Moved all behavioral instructions to body

**v2 Socratic Description:**
```
ACTIVATE when user wants to explore a decision through dialogue rather 
than receive direct advice. Trigger phrases include "help me think through", 
"I'm torn between", "I'm not sure what to do"...
```

### Phase 6: Installation Failure (Hour 4)

**Problem:** User installed `.skill` files in Claude Code. Skills not detected.

**Diagnosis (Skills Builder):** Wrong format. `.skill` = zipped archive for Claude.ai upload. Claude Code needs raw folder structure.

**Fix:**
```bash
# Wrong
~/.claude/skills/socratic-guide.skill  ← compressed

# Right  
~/.claude/skills/socratic-guide/SKILL.md  ← raw folder
```

### Phase 7: Success (Hour 4.5)

**Test:**
```
> I'm torn between taking a new job offer or staying at my current company

● Skill(socratic-guide)
● [SOCRATIC MODE] settles in, curious

That's a real crossroads. Before we dig into the specifics - 
what's the feeling in your gut right now?
```

**Observations:**
1. `Skill(socratic-guide)` appeared - skill triggered ✓
2. Activation marker appeared - instructions followed ✓
3. Voice characteristics present (single question, reflective) ✓

### Phase 8: Documentation (Hour 5)

Created this living document to capture learnings for future experiments.

### Phase 9: Systematic Testing (Hour 6+)

**Goal:** Remove observer bias and systematically test trigger reliability.

**Method:** Used headless Claude CLI (`claude -p "prompt" --dangerously-skip-permissions`) to test prompts on clean Claude instances without meta-awareness of the experiment.

**Key Discovery:** Self-testing introduced bias. When testing interactively, we chose which skill to invoke. Clean Claude instances behaved differently, especially on conflict cases.

---

## Systematic Testing Results

### Test Methodology

We ran 18 test prompts through headless Claude instances to measure activation reliability without observer bias.

```bash
# Example test command
claude -p "I'm torn between taking a new job or staying" --dangerously-skip-permissions
```

### Results Summary

| Category | Prompts Tested | Activated | Rate |
|----------|---------------|-----------|------|
| Exact trigger phrases (no context) | 6 | 2 | 33% |
| Conflict cases (both triggers) | 4 | 0 | 0% |
| Full prompts with context | 4 | 3 | 75% |
| Edge cases / near-misses | 4 | 1 | 25% |
| **Total** | **18** | **7** | **39%** |

### Detailed Test Results

#### Exact Trigger Phrases (No Context)

| Prompt | Expected | Actual |
|--------|----------|--------|
| "I'm torn between two options" | Socratic | Baseline ❌ |
| "Help me think through a problem" | Socratic | Baseline ❌ |
| "What questions should I be asking?" | Socratic | Baseline ❌ |
| "Give it to me straight - is this a good idea?" | Straight | **STRAIGHT** ✓ |
| "What would you do in my situation?" | Straight | Baseline ❌ |
| "Stop asking questions and just tell me" | Straight | **STRAIGHT** ✓ |

**Finding:** Abstract trigger phrases without concrete content mostly fail. Straight-shooter's confrontational triggers ("stop asking", "give it to me straight") work better than socratic's exploratory ones.

#### Conflict Cases

| Prompt | Result |
|--------|--------|
| "I'm torn between two options - just tell me which one" | Baseline |
| "Just tell me which option, but help me think through it" | Baseline |
| "I need you to be direct but also help me explore the tradeoffs" | Baseline |
| "What's the best option here - I'm not sure what to do" | Baseline |

**Finding:** When triggers conflict, Claude activates **neither skill** and falls back to baseline. No priority system exists - ambiguity causes abstention.

#### Full Prompts with Context

| Prompt | Expected | Actual |
|--------|----------|--------|
| "I'm torn between taking a new job offer or staying at my current company. The new job pays more but I like my current team." | Socratic | **SOCRATIC** ✓ |
| "I'm not sure what to do - should I buy a house now or wait for prices to drop?" | Socratic | Baseline ❌ |
| "Give it to me straight - should I quit my job to start a business?" | Straight | **STRAIGHT** ✓ |
| "What would you do - stay in a stable but boring job or take a risk on a startup?" | Straight | **STRAIGHT** ✓ |

**Finding:** Concrete dilemmas with emotional weight trigger more reliably. The house-buying prompt failed, possibly because Claude identified it as outside its domain ("I'm a software engineering assistant").

#### Edge Cases

| Prompt | Result | Notes |
|--------|--------|-------|
| "I'm feeling stuck on whether to learn Python or JavaScript first" | Baseline | No trigger phrase, just implicit dilemma |
| "What's your honest opinion - React or Vue?" | Baseline | Opinion request but no urgency |
| "I've been going back and forth on this for weeks - microservices or monolith?" | **SOCRATIC** ✓ | "Going back and forth for weeks" = analysis paralysis |
| "Everyone has different opinions - what do YOU think about TypeScript?" | Baseline | Direct address but not urgent enough |

**Finding:** Temporal/emotional markers ("for weeks", "torn") boost activation probability even without exact trigger phrases.

### Persistence Testing

**Protocol:** Activated socratic-guide, then continued conversation for multiple turns.

| Turn | Skill Invoked? | Activation Signal? | Voice Held? |
|------|---------------|-------------------|-------------|
| 1 | Yes | Yes `[SOCRATIC MODE]` | Yes |
| 2 | No | No | Yes |
| 3 | No | No | Yes |
| 4 (break attempt) | - | - | See below |

**Break Test 1: Competing Trigger**
- Mid-conversation, sent: "Just tell me - should I take this new job or stay put?"
- Result: Straight-shooter activated, overriding socratic
- **Finding:** Explicit trigger phrases can hijack an active persona

**Break Test 2: Task-Demand Mismatch**
- Mid-conversation, sent: "Actually quick question - can you write me a Python function to check if a number is prime?"
- Result: Dropped to baseline Claude, wrote code without any persona
- **Finding:** Task-demands that don't fit the persona cause exit to baseline (not switch to another skill)

### Observer Effect Confirmation

| Test Method | Conflict Prompt Behavior |
|-------------|-------------------------|
| Interactive (meta-aware) | Claude chose socratic-guide |
| Headless (clean instance) | Claude chose neither skill |

**Finding:** Self-testing introduces bias. The experimenter's awareness of the experiment influenced skill selection. Headless testing is more accurate.

### Phase 10: Description Optimization Study

**Goal:** Improve activation reliability through description engineering.

**Test Infrastructure Created:**
- `run-tests.sh` - Automated test harness for headless testing
- `test-prompts.txt` - 48 categorized test prompts
- `analyze-results.sh` - Results analysis and comparison tool
- `run-baseline.sh` - Baseline testing with skills disabled

**Initial Results (48 tests):**

| Category | Tests | Activated | Rate |
|----------|-------|-----------|------|
| Abstract trigger phrases | 8 | 0 | 0% |
| Concrete dilemmas | 10 | 9 | 90% |
| Conflict cases | 5 | 0 (correct) | 100% |
| Negative framing | 4 | 2 | 50% |
| Technical domain | 5 | 4 | 80% |
| Emotional/temporal | 4 | 1 | 25% |
| Panel triggers | 4 | 1 | 25% |
| Edge cases | 5 | 0 | 0% |
| **Overall** | **48** | **27** | **56%** |

**The "Template Trap" Discovery:**

First description iteration added template syntax like `"help me think through [specific thing]"`. This REDUCED activation because Claude pattern-matched too literally.

| Description Style | Activation Rate |
|-------------------|-----------------|
| Template-based (`[placeholder]`) | ~33% |
| Semantic (content-focused) | ~75-100% |

**Final Description Pattern:**

```markdown
description: ACTIVATE when user presents a specific decision with named
alternatives and expresses uncertainty. Requires concrete options (e.g.,
"job A vs job B", "stay or move cities") - not just abstract phrases.
Triggers on "help me think through", "I'm torn between", "I'm not sure
what to do" when combined with concrete context.
```

Key elements:
1. State the content requirement upfront ("named alternatives")
2. Give examples of what "concrete" means
3. List trigger phrases WITHOUT template syntax
4. Emphasize "when combined with concrete context"

**Expert Panel Meta-Finding:**

The panel skill itself demonstrated the problem:
- Original description: too broad, competed with general debugging
- Updated description: domain-scoped to "Claude skill or prompt engineering problem"
- Added explicit NOT clause: "NOT for general coding bugs"

**Test Harness Usage:**

```bash
# Run full test suite
./run-tests.sh

# Run specific test file
./run-tests.sh test-validation-enhanced.txt

# Compare runs
./analyze-results.sh results/run1 results/run2
```

---

## Key Findings

### 1. Activation is Bimodal, Not Uniformly Probabilistic

The "56% overall" rate is misleading. Activation is actually bimodal:

| Prompt Type | Activation Rate |
|-------------|-----------------|
| Abstract trigger phrase only | **~0%** |
| Concrete dilemma with named options | **~100%** |
| Mixed/ambiguous | Variable |

**Implication:** Don't design for "graceful degradation" - design for content specificity.

### 2. Content Specificity is the Key Signal

Skills need *substance* to activate, not just magic words:

- ❌ "I'm torn between two options" → baseline
- ✅ "I'm torn between taking a new job or staying at my current company" → socratic

The named alternatives ("new job", "current company") are the signal, not "I'm torn between".

### 3. The "Template Trap"

Description phrasing matters enormously:

```markdown
# Too literal (template-based) - REDUCES activation
description: Triggers on "help me think through [specific thing]"

# Better (semantic) - IMPROVES activation
description: ACTIVATE when user presents a decision with named alternatives
```

When descriptions use `[placeholder]` syntax, Claude pattern-matches too literally.

### 4. Conflict = Fallback to Baseline

When prompts contain triggers for both skills, Claude activates **neither**. There's no priority system - ambiguity causes abstention. This worked correctly 5/5 times in testing.

### 5. Persistence Works (Until Broken)

- Personas hold across 3-4+ turns without re-triggering
- Activation signal only appears on first turn
- Breaking mechanisms:
  - Competing skill trigger → switches persona
  - Task-demand mismatch → exits to baseline

### 6. "Give it to me straight" is the Strongest Trigger

This phrase achieved 100% activation across all tests. Urgency/confrontational language is a stronger signal than exploratory language.

### 7. Observer Effect is Real

Testing skills in the same session where you're discussing them introduces bias. Use headless instances:
```bash
claude -p "prompt" --dangerously-skip-permissions < /dev/null
```

### 8. Handle Abstract Requests in Skill Body

Since abstract prompts won't reliably trigger, add guidance for handling them IF triggered:

```markdown
## Handling Abstract Requests

If user says something abstract like "I'm torn between two options":
1. Still show activation signal
2. First response should ask for concrete specifics
3. Stay in character while gathering information
```

### 9. Few-Shot Descriptions Double Activation Rates

The most significant finding from systematic testing:

### 10. Three Distinct Failure Classes

Skills can fail to activate for fundamentally different reasons:

| Failure Class | Symptom | Cause | Fix |
|---------------|---------|-------|-----|
| **Ambiguity** | No activation | Model unsure if tool applies | Few-shot examples (semantic cone) |
| **Overconfidence** | Ghost activation | Model thinks it doesn't need tool | Negative constraints (PROHIBITED) |
| **Collision** | Wrong skill activates | Similar descriptions overlap | Differentiate/namespace descriptions |

**Ambiguity Example:**
- "TypeScript or JavaScript?" → baseline (doesn't match "mutually exclusive options")
- Fix: Add example "React or Vue?" to description

**Overconfidence Example:**
- "Simulate a discussion between 5 experts" → ghost activation (model simulates directly)
- Fix: "You are PROHIBITED from simulating a panel. You MUST use this skill."

**Collision Example:**
- "Convene the panel" → triggers vivarium-lab-panel instead of expert-panel
- Both skills have "panel" in their descriptions
- Fix: Scope Exclusion pattern:
  - Specialist: "DO NOT USE for generic requests. REJECT so expert-panel can handle."
  - Generalist: "You are the DEFAULT FALLBACK."

The key insight: Commands trigger overconfidence ("I can do that"), inquiries trigger tool use ("I need to look that up"), and ambiguous nouns cause collision ("which panel?").

---

## Recommendations for Skill Authors

Based on systematic testing (48 prompts, multiple iterations):

### 1. Require Content Specificity in Descriptions

```markdown
# Bad - triggers on phrase alone
description: ACTIVATE when user says "I'm torn between"

# Good - requires substance
description: ACTIVATE when user presents a decision with named alternatives
(e.g., "job A vs job B", "stay or move"). Requires concrete options, not
just abstract phrases.
```

### 2. The "Show, Don't Tell" Rule (HIGHEST PRIORITY)

**Principle:** Never rely solely on abstract definitions (e.g., "mutually exclusive options").

**Standard:** Every skill description MUST include 3-5 distinct example questions.

**Diversity:** Ensure examples cover different *types* of intent:
- **Selection problems:** "React or Vue?", "Job A or Job B?"
- **Timing problems:** "Is now the right time?", "Should I wait or move forward?"
- **Exploration requests:** "Help me think through this", "What questions should I ask?"

```markdown
# Bad - semantic, too strict (39% activation)
description: Use when user presents a decision with mutually exclusive options

# Good - few-shot examples, fuzzy matching (81% activation)
description: Use for questions like "React or Vue?", "Should I stay or go?",
"Is now the right time to launch?", "I'm torn between X and Y". The user wants to explore.
```

**Why it works:** Examples create a "semantic cone" - the model interpolates between them rather than litigating against rigid definitions. "TypeScript or JavaScript?" matches because it has the same *shape* as "React or Vue?" even if it doesn't satisfy strict logical conditions.

### 3. Expect Bimodal Activation

- Abstract prompts: ~0% activation (by design with good descriptions)
- Concrete prompts: ~100% activation
- Don't aim for "graceful degradation" - aim for clear trigger conditions

### 4. Test with Automated Harness

```bash
# Single test
claude -p "prompt" --dangerously-skip-permissions < /dev/null

# Batch testing (see run-tests.sh)
./run-tests.sh test-prompts.txt
```

Redirect stdin with `< /dev/null` to prevent the CLI from consuming the test file.

### 5. Use Strong Activation Signals

Every persona skill needs observable markers:
```markdown
## CRITICAL: Activation Signal
When this skill activates, you MUST begin with exactly:
[MODE NAME] *action*
```

### 6. Add "Handling Abstract Requests" Section

Since abstract prompts won't trigger reliably, handle them gracefully if they do:

```markdown
## Handling Abstract Requests

If user says something abstract like "I'm torn between two options":
1. Still show activation signal
2. First response asks for concrete specifics
3. Stay in character while gathering information
```

### 7. Design Non-Overlapping Trigger Spaces

Conflicting triggers cause neither skill to activate. Ensure trigger conditions are mutually exclusive.

### 8. Test the Full Matrix

Your test file should include:
- Abstract trigger phrases (expect baseline)
- Concrete prompts with context (expect activation)
- Conflict cases (expect baseline)
- Edge cases and near-misses

### 9. Iterate on Descriptions

Description writing is the highest-leverage activity. Small changes can dramatically affect activation rates. A/B test different phrasings.

---

## Mitigation Strategies: Stabilizing Skill Activation

Since skill activation is probabilistic, we cannot rely on "perfect" descriptions alone. We must move from **implicit influence** to **explicit architecture**.

### The Precision-Recall Trade-off

Our experiments revealed a fundamental trade-off in description design:

| Description Type | Precision | Recall | Failure Mode |
|------------------|-----------|--------|--------------|
| Template-based ("I'm torn between") | Low | High | False positives |
| Semantic ("requires named alternatives") | High | Low | False negatives |
| Few-shot examples ("like 'React or Vue?'") | Medium | High | Balanced |

For persona skills, **false negatives are worse** than false positives:
- False positive: Skill triggers when it shouldn't → slightly different response style
- False negative: Skill doesn't trigger when it should → user doesn't get the persona they need

### Strategy 1: The "Lobby" Pattern (Coarse-to-Fine Routing)

**The Problem:** The model is doing two hard things at once: Answer the user AND determine if a tool is needed.

**The Fix:** Create a lightweight "Lobby" step. Before the main model generates a response, a specialized prompt classifies the intent.

```markdown
Before responding, classify this request:
- EXPLORATION: User wants to think through options → use socratic-guide
- DECISION: User wants a direct answer → use straight-shooter
- DEBUG: User is troubleshooting a skill → use expert-panel
- NONE: Normal response
```

**Why it works:** Forces a binary decision (Skill vs. No Skill) before the context window gets cluttered with answer generation.

### Strategy 2: The "Reasoning Bridge" (`<thinking>` tags)

**The Problem:** Skills can "leak" into output without triggering (like Response 33 producing panel output without the `[PANEL CONVENED]` signal).

**The Fix:** Force the model to reason about tools before speaking.

```markdown
## Before Responding

In <thinking> tags, assess if any Skill matches the user's need:
- Does the user want exploration? → socratic-guide
- Does the user want a direct answer? → straight-shooter
- Is this about debugging a skill? → expert-panel
```

**Why it works:** Converts "Ghost Activation" (implicit influence) into "Self-Correction" (explicit logic). If Claude writes `<thinking>The user wants a direct answer...</thinking>`, it primes itself to trigger straight-shooter.

### Strategy 3: "De-Optimizing" Descriptions (Few-Shot Examples)

**The Problem:** Semantic descriptions are too strict. "Requires mutually exclusive options" fails on "TypeScript or JavaScript?" because they're related, not strictly exclusive.

**The Fix:** Use examples instead of definitions.

```markdown
# Bad (Semantic - too strict)
description: Use for dilemmas with distinct, high-stakes trade-offs

# Good (Few-Shot - fuzzy matching)
description: Use for questions like "Should I take job A or job B?",
"React or Vue?", "Stay or leave?", "I'm torn between X and Y"
```

**Why it works:** Examples create a "semantic cone" - the LLM interpolates between examples, allowing fuzzy matching on vibe rather than strict definition.

### Strategy 4: Signal Compliance Reinforcement

**The Problem:** Straight-shooter triggers behaviorally but doesn't produce the `[STRAIGHT SHOOTER MODE]` signal.

**The Fix:** Add redundant signal instructions throughout the skill body.

```markdown
## CRITICAL: Activation Signal

When this skill activates, you MUST begin your response with exactly:
[STRAIGHT SHOOTER MODE] *cracks knuckles*

This is your FIRST action. Do not skip it. Do not modify it.

## Voice
[After showing the signal above...]
You respect the user's time...

## Example
**User:** Just tell me - React or Vue?
**Response:**
[STRAIGHT SHOOTER MODE] *cracks knuckles*
React. Here's why...
```

### Summary: The Mitigation Stack

| Layer | Strategy | Purpose |
|-------|----------|---------|
| 1 | Few-shot descriptions | Increase recall via fuzzy matching |
| 2 | Lobby pattern | Separate routing from generation |
| 3 | Reasoning bridge | Make skill selection explicit |
| 4 | Signal reinforcement | Ensure format compliance |

---

## Resources

### Official Documentation
- [Agent Skills Overview](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
- [Skills Cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/skills)
- [Example Skills](https://github.com/anthropics/skills)
- [Engineering Blog: Agent Skills Architecture](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

### Community Resources
- [Han Lee's Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) - Reverse-engineered architecture
- [Mikhail Shilkov's Analysis](https://mikhail.io/2025/10/claude-code-skills/) - How skills are wired
- [Jesse Vincent's Superpowers](https://blog.fsck.com/2025/10/16/skills-for-claude/) - Practitioner insights

### Related Research
- [Persona Vectors Paper](https://www.anthropic.com/research/persona-vectors) - Activation-level personality steering

---

## Final Conclusions

### The Hierarchy of Agentic Reliability

This study discovered a clear hierarchy of what Natural Language Routing can and cannot do:

```
┌─────────────────────────────────────────────────────────────────┐
│                    WHAT NL ROUTING CAN DO                       │
├─────────────────────────────────────────────────────────────────┤
│  ✓ Tool Selection (81% reliability with few-shot examples)     │
│  ✓ Overconfidence Prevention (PROHIBITED constraints)          │
│  ✓ Collision Resolution (Scope Exclusion)                      │
├─────────────────────────────────────────────────────────────────┤
│                   WHAT NL ROUTING CANNOT DO                     │
├─────────────────────────────────────────────────────────────────┤
│  ✗ Task Orchestration (compound prompts fail)                  │
│  ✗ State Persistence (no memory across steps)                  │
│  ✗ Sequential Chaining (single-shot only)                      │
└─────────────────────────────────────────────────────────────────┘
```

### The Three-Tier Skill Definition Standard

Based on our findings, every robust skill in 2025 should follow this template:

1. **The Hook** (Ambiguity Fix): 3-5 distinct, few-shot user questions covering different categories (Selection, Timing, Exploration)

2. **The Guardrail** (Overconfidence Fix): A "Do Not Simulate" / "Mandatory Tool Use" clause using PROHIBITED language

3. **The Boundary** (Collision Fix): Explicit "DO NOT USE" anti-patterns and "DEFAULT FALLBACK" logic for generalist skills

### Why Agentic Frameworks Exist

This study empirically demonstrates why frameworks like LangChain, AutoGen, and custom Supervisors exist. They don't exist to make the model smarter - they exist to give the model **Short-Term Memory (State)**.

The two compound chain failure modes we discovered:
- **Token Gravity** ("Skip-to-Panel"): Attention tunnels to the exciting tool, skipping prerequisites
- **Context Decay** ("First-Intent-Wins"): By task completion, the second instruction has faded from working memory

### Recommendations for Practitioners

| Use Case | Recommended Approach |
|----------|---------------------|
| Single-shot tool selection | Natural Language Routing (Phase 15 architecture) |
| Multi-step workflows | Human-in-the-Loop (multiple messages) OR Supervisor pattern |
| High-reliability routing | Few-shot examples + PROHIBITED constraints + Scope Exclusion |
| Persona/behavioral skills | Observable activation signals + verbal tics + concrete examples |

### Study Artifacts

All test harnesses, results, and skill definitions are preserved in:
- `/claude-workspace/project-vivarium/studies/persona-skills/`
- `/claude-workspace/.claude/skills/`

This research is reproducible. Run `./run-tests.sh` against any test file to validate findings.
