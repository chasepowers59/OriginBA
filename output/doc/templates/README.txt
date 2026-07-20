OriginBA Standard Offering Report Library Validation Template
===========================================================

Files
-----
- OriginBA_Standard_Offering_Report_Library_Validation_TEMPLATE.docx
  Reusable fillable template with all 144 reports, 13 dashboards, and CLIENT_NAME placeholders.
- CLIENT_NAME_25.4_TEST_Role_Based_Access_Cover_Base.docx
  Origin cover-page base copied from the Role-Based Access Testing document.

Placeholders to replace
-----------------------
- CLIENT_NAME
- TEST_VERSION
- DATASOURCE_ALIAS
- AUTHOR_NAME
- PASS/FAIL/NA

Manual workflow
---------------
1. Open the template in Word.
2. Find/replace CLIENT_NAME, TEST_VERSION, DATASOURCE_ALIAS, and AUTHOR_NAME.
3. Execute each Standard Offering report, ad hoc view, and dashboard.
4. Update Validation and Notes for each row.
5. Update Validation Summary and Test Results Summary when complete.

Generator workflow
------------------
Create or refresh the reusable template:

  python3 scripts/doc/build_standard_offering_validation_doc.py --template

Generate a client-ready document:

  python3 scripts/doc/build_standard_offering_validation_doc.py \
    --client CityCorp \
    --test-version 25.4 \
    --datasource CityCorp_DS \
    --author "Chase Powers" \
    --status PASS

Generate for another client:

  python3 scripts/doc/build_standard_offering_validation_doc.py \
    --client Odessa \
    --test-version 25.4 \
    --datasource Odessa_DS \
    --author "Chase Powers" \
    --status PASS \
    --output output/doc/Odessa_Standard_Offering_Report_Library_Validation.docx

Notes
-----
- The report inventory is sourced from tmp/docs/report_library_catalog.json.
- Optional object-folder enrichment uses Downloads/standardoffering.zip when present.
- The CityCorp completed example remains at:
  output/doc/OriginBA_Standard_Offering_Report_Library_Validation.docx
