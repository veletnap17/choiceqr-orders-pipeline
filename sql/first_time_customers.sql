SELECT
  delivery_customer_phone,
  MIN(DATE(orderLocalTime)) AS first_order_date
FROM
  `project_id.Data_total.orders_all_dedup`
WHERE
  status != 'cancelled'
GROUP BY
  1
