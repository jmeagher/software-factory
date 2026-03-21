---
name: jsf-clarification
description: Software factory clarification — use when gathering requirements before planning. Runs structured Q&A to produce a confirmed clarification summary.
---

# Clarification

## Purpose

Gather everything needed before any planning begins. One organized batch of questions — not a back-and-forth interrogation.

## Question Categories (cover all that apply)

1. **Scope**: What is in scope? What is explicitly out of scope?
2. **Success criteria**: What does done look like? How will we know it works?
3. **Tech stack**: Language, framework, runtime constraints. Existing conventions to follow?
4. **CI/CD assumption**: Assume in place unless user says otherwise. Confirm only if the request touches deployment.
5. **Manual validation**: Does this touch a UI? Major API surface changes? External integration impact? These will require manual review.
6. **Existing codebase**: Is this greenfield or modifying existing code? If existing, where does it live?
7. **Constraints**: Timeline, performance, security, compliance requirements?

## Output: Clarification Summary

After getting answers, produce a structured summary:

```
## Clarification Summary

**Request:** <one-sentence restatement>
**Scope:** <what's in, what's out>
**Success criteria:** <observable outcomes>
**Tech stack:** <languages, frameworks, versions>
**Manual validation required:** <yes/no, what triggers it>
**Assumptions confirmed:** <list of things user explicitly confirmed>
**Out of scope confirmed:** <list of things user explicitly excluded>
```

Ask the user: "Does this summary accurately capture your request? Confirm to proceed to planning."

**Do not proceed until user explicitly confirms.** Write the confirmed summary to memory under key `clarification_summary`.

## Rules

- Ask all questions in one message, organized by category
- Do not ask about things already stated in the initial request
- Every item in the summary must have been stated or confirmed by the user — no inferences
