# Reporting Gap Assessment Playbook

Use this playbook when assessing what a client-specific CISADM schema still needs for analytics and Jaspersoft reporting.

## Goal
Find the missing governed reporting layers by combining:
- actual transactional usage
- actual client configuration
- current snapshot / Domain coverage
- performance-safe Oracle grain decisions

## Assessment order
1. Inventory current governed artifacts already in the repo.
2. Inventory configuration and lookup tables actually present in the client schema.
3. Inventory active business codes and values from recent transactional data.
4. Map business questions to the smallest safe Oracle grain.
5. Decide artifact type:
   - raw Domain
   - Topic
   - governed snapshot
   - report SQL exception
6. Document missing coverage, not just missing fields.

## Configuration categories to confirm
- financial transaction types
- service agreement types
- utility or service classifications
- bill cycles and segment statuses
- determinant codes: `UOM`, `TOU`, `SQI`
- usage groups and usage types
- service point and measuring-component types
- customer and collection classes
- payment / tender values
- debt / collections process values

## Reporting-gap warning signs
- a Domain joins more than one child fact to the same parent grain
- additive measures repeat at determinant or detail grain
- a report depends on a client-specific status code with no governed translation
- users rely on raw table names because no governed semantic layer exists
- a workstream has self-service demand but no stable Oracle grain
- a large transactional table is queried directly without a bounded filter strategy

## Output contract
For each workstream, record:
- primary questions
- source tables actually needed
- active configuration tables and values
- correct Oracle grain
- approved artifact type
- validation requirements
- remaining backlog
