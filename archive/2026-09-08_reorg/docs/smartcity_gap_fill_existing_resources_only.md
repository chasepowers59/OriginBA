# SmartCity Gap-Fill Plan Using Existing Resources Only

## Purpose

This document revises the gap-fill plan for SmartCity under a hard constraint:

- **No new Domains**
- **No new governed snapshots or Oracle truth layers**
- **Only existing Jaspersoft resources may be used**

That means each gap-fill recommendation must be built from:
- existing Domains
- existing Ad Hoc views
- existing dashboards
- existing report units and their current field sets

Where a gap cannot be filled cleanly with existing resources, it is marked as **Not cleanly feasible with current resources** rather than forcing brittle or misleading report logic.

## Guiding Rule

If an existing resource does not already expose the right grain and fields, do **not** fake the business question with weak logic just to fill a catalog slot.

## Revised Gap-Fill Recommendations

| Gap-Fill Report | Existing Resource Path | Feasible Now? | Revised Approach |
|---|---|---|---|
| `Reference Data Health Monitor` | `common` resources only | No, not cleanly | Defer unless an existing common Domain already exposes lookup/reference rows directly |
| `Customer Communication Readiness` | `customer_ops / Customer Contact`, `customer_ops / Customer`, `customer_ops / Account Alert` | No, not cleanly | Defer because the existing resources do not expose enough communication-readiness fields cleanly |
| `Pending Service Agreement Aging` | `new_services / New Services`, `new_services / Dashboard` | Completed | Already built from existing new-services Domain/report resources |
| `Payment Arrangement Summary` | `debt_mgmt / Collection Process`, `debt_mgmt / Dashboard`, any existing arrangement-related Domain fields | No, not cleanly | Defer because the required arrangement fields are not available in usable existing resources |
| `Service Point / Install Linkage Exceptions` | `field_ops / Field Activity`, `field_ops / Dashboard` | No, not cleanly | Defer because the existing field-ops resources do not expose the needed linkage grain cleanly |

---

## 1. Customer Communication Readiness

### Current Status

Deferred.

The report is not cleanly feasible with current existing resources.

Keep this on the future backlog until a current customer/contact resource exposes the needed communication-quality fields clearly enough.

---

## 2. Pending Service Agreement Aging

### Current Status

Completed.

This gap-fill has already been added to the standard offering using existing `new_services` resources.

---

## 3. Payment Arrangement Summary

### Current Status

Deferred.

The required payment arrangement fields are not available in a usable existing resource set, so this report should stay on the future backlog.

---

## 4. Service Point / Install Linkage Exceptions

### Current Status

Deferred.

The existing field-ops resources do not expose the linkage grain cleanly enough, so this report should stay on the future backlog.

---

## 5. Reference Data Health Monitor

### Use Existing Resources

Only existing `common` resources are allowed:
- `Batch`
- `Exception`
- `To Do / Exception`

### Reality Check

This gap is **not cleanly feasible** with current resources unless one of the existing common Domains already exposes:
- lookup field name
- lookup field value
- active/inactive status
- referenced entity count or equivalent row-level reference data

The current common resources appear to be focused on:
- batch processing
- operational exceptions
- to-do / support workload

Those do not naturally answer a reference-data governance question.

### Recommendation

Do not build this report from unrelated batch/exception resources.

Keep it on the SmartCity future backlog until an existing compatible resource is confirmed.

---

## Revised Build Order Under Existing-Resource Constraint

Already built:
1. `Pending Service Agreement Aging`

Do not build yet:
1. `Reference Data Health Monitor`
2. `Customer Communication Readiness`
3. `Payment Arrangement Summary`
4. `Service Point / Install Linkage Exceptions`

## Practical Next Step

Use `Pending Service Agreement Aging` as the completed example of how to close a SmartCity gap using only existing resources.

For the remaining deferred items, do not reopen design work unless the current Jaspersoft resources are expanded enough to support the business question cleanly.
