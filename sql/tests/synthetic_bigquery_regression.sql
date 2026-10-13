-- Self-contained BigQuery Standard SQL regression demo.
-- Uses only synthetic orders and temporary tables; does not access production data.
-- Run the entire script in the BigQuery SQL editor.
CREATE TEMP TABLE raw_orders AS
SELECT '42' AS _id, 'Vinohrady' AS restaurant, 'created' AS status,
       TIMESTAMP '2026-10-01 09:00:00+00' AS orderLocalTime,
       100 AS total, '2026-10-01T09:00:00Z' AS timestamps_created,
       '2026-10-01T09:01:00Z' AS loaded_at
UNION ALL SELECT '42', 'Vinohrady', 'completed', TIMESTAMP '2026-10-01 09:00:00+00',
       120, '2026-10-01T10:00:00Z', '2026-10-01T10:01:00Z'
UNION ALL SELECT '42', 'Zizkov', 'completed', TIMESTAMP '2026-10-01 11:00:00+00',
       200, '2026-10-01T11:00:00Z', '2026-10-01T11:01:00Z'
UNION ALL SELECT '77', 'Vinohrady', 'cancelled', TIMESTAMP '2026-10-02 08:00:00+00',
       0, '2026-10-02T08:00:00Z', '2026-10-02T08:01:00Z'
UNION ALL SELECT CAST(NULL AS STRING), 'Vinohrady', 'created',
       TIMESTAMP '2026-10-02 12:00:00+00', 50,
       '2026-10-02T12:00:00Z', '2026-10-02T12:01:00Z';

CREATE TEMP TABLE dedup_orders (
  _id STRING, restaurant STRING, status STRING, orderLocalTime TIMESTAMP, total INT64
);

-- Same composite key and source selection rules as sql/deduplicate_orders.sql.
MERGE dedup_orders AS T
USING (
  SELECT _id, restaurant, status, orderLocalTime, total
  FROM raw_orders AS R
  WHERE _id IS NOT NULL AND restaurant IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY restaurant, _id
    ORDER BY SAFE_CAST(timestamps_created AS TIMESTAMP) DESC,
             SAFE_CAST(loaded_at AS TIMESTAMP) DESC,
             TO_JSON_STRING(R) DESC
  ) = 1
) AS S
ON T.restaurant = S.restaurant AND T._id = S._id
WHEN MATCHED THEN UPDATE SET
  status = S.status, orderLocalTime = S.orderLocalTime, total = S.total
WHEN NOT MATCHED THEN
  INSERT (_id, restaurant, status, orderLocalTime, total)
  VALUES (S._id, S.restaurant, S.status, S.orderLocalTime, S.total);

ASSERT (SELECT COUNT(*) = 3 FROM dedup_orders)
  AS 'Expected three unique (restaurant, order) combinations';
ASSERT (
  SELECT COUNT(*) = 1 FROM dedup_orders
  WHERE restaurant = 'Vinohrady' AND _id = '42'
    AND total = 120 AND status = 'completed'
) AS 'Latest Vinohrady update should win';
ASSERT (
  SELECT COUNT(*) = 1 FROM dedup_orders
  WHERE restaurant = 'Zizkov' AND _id = '42' AND total = 200
) AS 'Same order id at another restaurant must remain distinct';
ASSERT (
  SELECT COUNT(*) = 0 FROM dedup_orders
  WHERE _id IS NULL OR restaurant IS NULL
) AS 'Null business keys must be excluded';

-- Re-run the MERGE using the same source set: no duplicate target rows.
MERGE dedup_orders AS T
USING (
  SELECT _id, restaurant, status, orderLocalTime, total
  FROM raw_orders AS R
  WHERE _id IS NOT NULL AND restaurant IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY restaurant, _id
    ORDER BY SAFE_CAST(timestamps_created AS TIMESTAMP) DESC,
             SAFE_CAST(loaded_at AS TIMESTAMP) DESC,
             TO_JSON_STRING(R) DESC
  ) = 1
) AS S
ON T.restaurant = S.restaurant AND T._id = S._id
WHEN MATCHED THEN UPDATE SET
  status = S.status, orderLocalTime = S.orderLocalTime, total = S.total
WHEN NOT MATCHED THEN
  INSERT (_id, restaurant, status, orderLocalTime, total)
  VALUES (S._id, S.restaurant, S.status, S.orderLocalTime, S.total);

ASSERT (SELECT COUNT(*) = 3 FROM dedup_orders)
  AS 'Re-running merge must be idempotent on this sample';

-- Metrics match the logic in sql/daily_metrics.sql.
CREATE TEMP TABLE daily_metrics AS
SELECT DATE(orderLocalTime) AS order_date, restaurant,
       COUNT(DISTINCT _id) AS orders, SUM(total) AS revenue,
       COUNTIF(status = 'cancelled') AS cancelled_orders
FROM dedup_orders GROUP BY 1, 2;

ASSERT (
  SELECT COUNT(*) = 1 FROM daily_metrics
  WHERE order_date = DATE '2026-10-01' AND restaurant = 'Vinohrady'
    AND orders = 1 AND revenue = 120 AND cancelled_orders = 0
) AS 'Vinohrady daily metrics mismatch';
ASSERT (
  SELECT COUNT(*) = 1 FROM daily_metrics
  WHERE order_date = DATE '2026-10-01' AND restaurant = 'Zizkov'
    AND orders = 1 AND revenue = 200
) AS 'Zizkov daily metrics mismatch';
ASSERT (
  SELECT COUNT(*) = 1 FROM daily_metrics
  WHERE order_date = DATE '2026-10-02' AND restaurant = 'Vinohrady'
    AND orders = 1 AND revenue = 0 AND cancelled_orders = 1
) AS 'Cancellation daily metrics mismatch';

SELECT 'PASS - synthetic deduplication and metrics assertions' AS result;
