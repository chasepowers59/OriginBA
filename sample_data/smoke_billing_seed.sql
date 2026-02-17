-- Lightweight smoke dataset (12 rows) for quick report validation.
-- Target tables: STG_CUSTOMERS, STG_BILL_LINE_ITEMS
-- Bind variables:
--   :client_id  (e.g. 'SMOKE_CLIENT_1001')
--   :start_dt   (DATE)

INSERT INTO STG_CUSTOMERS (CLIENT_ID, CUSTOMER_ID, CUSTOMER_NAME)
SELECT :client_id,
       900000 + LEVEL,
       'Smoke Customer ' || LEVEL
FROM DUAL
CONNECT BY LEVEL <= 4;

INSERT INTO STG_BILL_LINE_ITEMS (
    CLIENT_ID, BILL_ID, CUSTOMER_ID, LINE_ID, BILL_DATE, DUE_DATE,
    ITEM_CODE, ITEM_DESCRIPTION, QUANTITY, UNIT_PRICE, LINE_AMOUNT
)
SELECT
    :client_id,
    700000 + CEIL(LEVEL / 3),
    900000 + MOD(LEVEL - 1, 4) + 1,
    LEVEL,
    :start_dt + MOD(LEVEL, 2),
    :start_dt + 15 + MOD(LEVEL, 2),
    'ITEM' || TO_CHAR(MOD(LEVEL, 5) + 1),
    'Smoke line item ' || LEVEL,
    1 + MOD(LEVEL, 3),
    10 + MOD(LEVEL, 7),
    (1 + MOD(LEVEL, 3)) * (10 + MOD(LEVEL, 7))
FROM DUAL
CONNECT BY LEVEL <= 12;

COMMIT;
