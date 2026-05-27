SELECT
  DATE(orderLocalTime) AS order_date,
  restaurant,
  COUNT(DISTINCT _id) AS orders,
  SUM(total) AS revenue,
  COUNTIF(status = 'cancelled') AS cancelled_orders
FROM
  `project_id.Data_total.orders_all_dedup`
GROUP BY
  1, 2
ORDER BY
  1 DESC
