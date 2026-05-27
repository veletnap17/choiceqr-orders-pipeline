MERGE `project_id.Data_total.orders_all_dedup` T
USING (
  SELECT *
  FROM (
    SELECT *,
           ROW_NUMBER() OVER (
             PARTITION BY _id
             ORDER BY timestamps_created DESC
           ) AS rn
    FROM `project_id.Data_total.orders_all_raw`
    WHERE _id IS NOT NULL
  )
  WHERE rn = 1
) S
ON T._id = S._id

WHEN MATCHED THEN
UPDATE SET
  T.status = S.status,
  T.orderLocalTime = S.orderLocalTime,
  T.total = S.total,
  T.restaurant = S.restaurant

WHEN NOT MATCHED THEN
INSERT ROW
