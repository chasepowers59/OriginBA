# Skill Authoring Guide (OriginBA)

## Purpose
Define repeatable instructions that make report delivery consistent, testable, and deployment-safe.

## Skill Template
Use this structure for every new skill document:

1. **Goal**
2. **Inputs Required**
3. **Steps**
4. **Validation**
5. **Failure Handling**
6. **Output Contract**

## Authoring Rules
1. Use imperative steps (do X, then Y).
2. Include exact file paths and naming conventions.
3. Include at least one validation command per skill.
4. Define stop conditions (when to escalate to user/admin).
5. Keep environment assumptions explicit (Studio 9.x, domain-based, datasource aliases only).

## Good Skill Example Pattern
1. Confirm domain URI and field IDs from schema export.
2. Build JRXML with domain query fields and null-safe filters.
3. Build matching input control JSONs.
4. Validate XML/JSON parse.
5. Smoke test in Studio with minimal fields first.

## Anti-Patterns
1. Vague guidance without validation steps.
2. Optional language for required compliance steps.
3. Mixing domain and SQL instructions in one skill without clear trigger conditions.
4. Missing rollback/archive strategy for cleanup tasks.
