-- Correct earlier failed-action refunds, including linked timezone windows.
WITH RECURSIVE affected(reservation_id,window_id) AS (
  SELECT r.id,r.window_id FROM reservations r JOIN actions a ON a.id=r.action_id
  WHERE r.state='RELEASED' AND a.state='FAILED'
  UNION
  SELECT t.reservation_id,CASE WHEN c.source_id=t.window_id THEN c.target_id ELSE c.source_id END
  FROM affected t JOIN budget_window_carries c ON c.source_id=t.window_id OR c.target_id=t.window_id
)
UPDATE budget_windows SET submitted=submitted+(
  SELECT count(*) FROM affected WHERE window_id=budget_windows.id
);
UPDATE run_counters SET submitted=submitted+(
  SELECT count(*) FROM reservations r JOIN actions a ON a.id=r.action_id
  WHERE r.state='RELEASED' AND a.state='FAILED'
    AND a.run_id=run_counters.run_id AND a.policy_id=run_counters.policy_id
);
UPDATE reservations SET state='CONSUMED'
WHERE state='RELEASED' AND action_id IN (SELECT id FROM actions WHERE state='FAILED');
