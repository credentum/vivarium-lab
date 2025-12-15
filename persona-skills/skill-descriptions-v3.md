# Skill Descriptions v3: Few-Shot Pattern

Based on the "De-Optimizing" insight: Use examples instead of semantic definitions.

## The Problem with Semantic Descriptions

```markdown
# v2 (Too Strict - Semantic)
description: ACTIVATE when user presents a specific decision with named
alternatives and expresses uncertainty. Requires concrete options.
```

LLM interpretation: "TypeScript or JavaScript? That's not 'uncertainty' -
they know the options. SKIP."

## The Fix: Few-Shot Examples

```markdown
# v3 (Looser - Example-Based)
description: Use for questions like: "Should I take job A or job B?",
"React or Vue?", "Stay or leave?", "Buy now or wait?", "I'm torn between X and Y"
```

LLM interpretation: "TypeScript or JavaScript? That's like 'React or Vue?' -
MATCH."

---

## Revised Descriptions

### Socratic Guide v3

```yaml
---
name: socratic-guide
description: Use for questions like "I'm torn between X and Y", "Help me think through this", "Should I do A or B?", "I'm not sure what to do about [situation]", "What questions should I ask myself?". The user wants to explore, not be told what to do.
---
```

### Straight Shooter v3

```yaml
---
name: straight-shooter
description: Use for questions like "Just tell me - X or Y?", "Give it to me straight", "What would you do?", "Stop asking questions", "Which one is better?", "I need a decision NOW". The user wants a direct answer, not exploration.
---
```

### Expert Panel v3

```yaml
---
name: expert-panel
description: Use for questions like "Why isn't this skill working?", "What would the experts say?", "Convene the panel", "Debug this prompt", "Why isn't this triggering?". Specifically for skill/prompt engineering problems.
---
```

---

## Key Changes

| Aspect | v2 (Semantic) | v3 (Few-Shot) |
|--------|---------------|---------------|
| Logic | Definitions | Examples |
| Matching | Strict semantic | Fuzzy vibe-match |
| Failure mode | False negatives | False positives |
| Trade-off | High precision, low recall | Lower precision, higher recall |

## Why This Works

1. **Examples create a "semantic cone"** - the LLM interpolates between examples
2. **No strict requirements** - no "must have named alternatives" to fail on
3. **Captures the vibe** - "React or Vue?" matches "X or Y?" pattern
4. **Graceful degradation** - might trigger on edge cases, but that's better than not triggering on core cases

## The Precision-Recall Trade-off

For persona skills, we want **high recall** (trigger when we should) even at the cost of **lower precision** (occasional false triggers).

Why? Because:
- False positive: Skill triggers when it shouldn't → user gets slightly different response style
- False negative: Skill doesn't trigger when it should → user doesn't get the persona they need

False negatives are worse for persona skills.

---

## Additional Mitigation: Reasoning Bridge

Add to system prompt or skill body:

```markdown
## Before Responding

Assess if this matches a persona skill:
- Does the user want exploration? → socratic-guide
- Does the user want a direct answer? → straight-shooter
- Is this about debugging a skill? → expert-panel
- None of the above? → respond normally
```

This forces explicit reasoning before response generation.
