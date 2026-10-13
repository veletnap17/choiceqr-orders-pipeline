-- Run AFTER sql/deduplicate_orders.sql.
-- Replace project_id and dataset/table names before running in BigQuery.
-- ASSERT stops the script with an error if the condition is not satisfied.

ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT restaurant, _id
    FROM `project_id.Data_total.orders_all_dedup`
    GROUP BY restaurant, _id
    HAVING COUNT(*) > 1
  )
) AS 'Duplicate (restaurant, _id) keys found in deduplicated orders';

ASSERT (
  SELECT COUNT(*) = 0
  FROM `project_id.Data_total.orders_all_dedup`
  WHERE _id IS NULL OR restaurant IS NULL
) AS 'NULL order id or restaurant in deduplicated orders';

-- Diagnostic query: NULL source keys are skipped by the MERGE.
SELECT
  COUNTIF(_id IS NULL) AS raw_null_order_ids,
  COUNTIF(restaurant IS NULL) AS raw_null_restaurants,
  COUNT(*) AS raw_total_rows
FROM `project_id.Data_total.orders_all_raw`;
