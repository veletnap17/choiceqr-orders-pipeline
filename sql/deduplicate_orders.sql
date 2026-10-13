-- Portfolio example: maintain one analytical row per (restaurant, _id).
-- Replace project_id with your Google Cloud project and verify table schemas.
-- This MERGE intentionally maintains only the columns listed below.
-- Other target columns (if any) must be nullable or have defaults.
MERGE `project_id.Data_total.orders_all_dedup` AS T
USING (
  SELECT
    _id,
    restaurant,
    status,
    orderLocalTime,
    total
  FROM `project_id.Data_total.orders_all_raw` AS R
  WHERE _id IS NOT NULL
    AND restaurant IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY restaurant, _id
    ORDER BY
      SAFE_CAST(timestamps_created AS TIMESTAMP) DESC,
      SAFE_CAST(loaded_at AS TIMESTAMP) DESC,
      TO_JSON_STRING(R) DESC
  ) = 1
) AS S
ON T.restaurant = S.restaurant AND T._id = S._id

WHEN MATCHED THEN UPDATE SET
  status = S.status,
  orderLocalTime = S.orderLocalTime,
  total = S.total

WHEN NOT MATCHED THEN
  INSERT (_id, restaurant, status, orderLocalTime, total)
  VALUES (S._id, S.restaurant, S.status, S.orderLocalTime, S.total);
