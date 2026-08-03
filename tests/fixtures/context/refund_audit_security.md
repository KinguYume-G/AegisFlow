# Refund audit export security

Refund audit CSV output masks payment card data and never contains a Secret or API Token.
Audit timestamps are emitted in UTC, and the CSV begins with a UTF-8 BOM.
