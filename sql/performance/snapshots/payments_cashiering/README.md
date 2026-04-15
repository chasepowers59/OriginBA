# Payments And Cashiering Discovery Workspace

This folder is for discovering the safest snapshot grain for payments and cashiering in this tenant.

Each active snapshot subfolder also carries its matching end-user Domain XML copy so the SQL assets and Jaspersoft artifact can be reviewed together.

The key question is whether the business truth is best represented as:
- one row per payment event
- one row per payment
- one row per tender
- one row per payment segment
- or a more tenant-specific tender-source / distribution-driven shape

## Why discovery is needed

This tenant may not use the standard payment-event-centered flow in a straightforward way.

The likely source objects are:
- `CI_PAY_EVENT`
- `CI_PAY`
- `CI_PAY_TNDR`
- `CI_PAY_SEG`
- `CI_TNDR_CTL`
- `CI_DEP_CTL`
- `CI_TNDR_DEP`
- `CI_PAY_TNDR_ST`
- `CI_PEVT_DST_DTL`
- `CI_APAY_SRC`

Some tenants mainly care about:
- tender source and tender control
- deposit reconciliation
- distribution rules on payment events
- staged inbound payment/tender activity

Those patterns can change the best snapshot grain.

## What the existing finance snapshots already cover

The current finance snapshots are useful for:
- payment-related FT and GL rows
- payment-segment linkage through `CI_PAY_SEG`

They are not the right truth source for:
- tender source/channel
- tender status and tender type mix
- staged payment/tender feeds
- deposit control and tender control operations
- cashiering workflow analysis

That is why a dedicated payments/cashiering discovery pass is needed even though FT and GL already show some payment-related records.

## Discovery workflow

1. Run `00a_config_discovery_validation.sql`.
2. Check which tables are materially populated in this tenant.
3. Check the real cardinality:
   - `PAY_EVENT -> PAY`
   - `PAY_EVENT -> PAY_TNDR`
   - `PAY -> PAY_SEG`
   - `PAY_TNDR -> TNDR_CTL -> DEP_CTL`
4. Decide whether the first snapshot should be:
   - `PAYMENT_RPT_CURR` at payment event or payment grain, or
   - `PAY_TNDR_RPT_CURR` at tender grain if tender source is the real business grain.

## Discovery outcome

Discovery showed that this tenant is best represented first at tender grain:
- `PAY_EVENT -> PAY_TNDR` is close to one-to-one
- `PAY -> PAY_SEG` is strongly one-to-many
- `CI_TNDR_CTL` and `CI_DEP_CTL` are materially populated and join cleanly from tenders
- `CI_PEVT_DST_DTL` is unused
- current activity is dominated by OriginPay plus standard cashier/mail/drop-off sources, not legacy auto-pay

## Implemented subset

- `pay_tndr_cashier/`: tender-centered payment and cashiering snapshot workspace with one row per `PAY_TENDER_ID`
- `pay_tndr_cashier/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
