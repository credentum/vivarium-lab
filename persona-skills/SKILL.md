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
