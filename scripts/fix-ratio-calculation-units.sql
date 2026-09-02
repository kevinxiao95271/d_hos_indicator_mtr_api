-- 修复现有指标库中的比例计算口径。
-- 统一约定：
--   百分比结果按展示值存储：分子 / 分母 * 100，单位为 %
--   千分比结果按展示值存储：分子 / 分母 * 1000，单位为 ‰
-- 本脚本可重复执行，不会重复追加 * 100。

START TRANSACTION;

UPDATE t_indicator
SET target_value = CASE
        WHEN expression REGEXP '\\*[[:space:]]*100([.]0+)?[[:space:]]*$' THEN target_value
        WHEN target_value IS NULL THEN NULL
        ELSE target_value * 100
    END,
    expression = CASE
        WHEN expression REGEXP '\\*[[:space:]]*100([.]0+)?[[:space:]]*$' THEN expression
        ELSE CONCAT('(', expression, ') * 100')
    END,
    unit = '%',
    update_time = NOW()
WHERE is_leaf = 1
  AND calculation_type = 'EXPRESSION'
  AND metric_name IN (
      '手术患者并发症发生率',
      'I类切口手术部位感染率',
      '急性心肌梗死病死率',
      '心力衰竭病死率',
      '肺炎（住院、成人）病死率',
      '肺炎（住院、儿童）病死率',
      '脑梗死病死率',
      '髋关节置换术病死率',
      '膝关节置换术病死率',
      '冠状动脉旁路移植术病死率',
      '剖宫产病死率',
      '慢性阻塞性肺疾病病死率'
  );

-- 历史结果中保存了计算时使用的表达式。仅迁移尚未乘 100 的旧结果，
-- 从而保证脚本重复执行时不会再次放大。
UPDATE t_indicator_result r
JOIN t_indicator i ON i.metric_code = r.metric_code
SET r.result_value = r.result_value * 100,
    r.result_json = JSON_SET(
        r.result_json,
        '$.result_value', CAST(JSON_UNQUOTE(JSON_EXTRACT(r.result_json, '$.result_value')) AS DECIMAL(30, 4)) * 100,
        '$.unit', '%',
        '$.expression', i.expression
    ),
    r.update_time = NOW()
WHERE i.unit = '%'
  AND JSON_VALID(r.result_json)
  AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(r.result_json, '$.expression')), '')
      NOT REGEXP '\\*[[:space:]]*100([.]0+)?[[:space:]]*$';

UPDATE t_indicator_result_dept r
JOIN t_indicator i ON i.metric_code = r.metric_code
SET r.result_value = r.result_value * 100,
    r.result_json = JSON_SET(
        r.result_json,
        '$.result_value', CAST(JSON_UNQUOTE(JSON_EXTRACT(r.result_json, '$.result_value')) AS DECIMAL(30, 4)) * 100,
        '$.unit', '%',
        '$.expression', i.expression
    ),
    r.update_time = NOW()
WHERE i.unit = '%'
  AND JSON_VALID(r.result_json)
  AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(r.result_json, '$.expression')), '')
      NOT REGEXP '\\*[[:space:]]*100([.]0+)?[[:space:]]*$';

COMMIT;

SELECT metric_code, metric_name, expression, unit
FROM t_indicator
WHERE metric_name IN (
    '手术患者并发症发生率',
    'I类切口手术部位感染率',
    '急性心肌梗死病死率',
    '心力衰竭病死率',
    '肺炎（住院、成人）病死率',
    '肺炎（住院、儿童）病死率',
    '脑梗死病死率',
    '髋关节置换术病死率',
    '膝关节置换术病死率',
    '冠状动脉旁路移植术病死率',
    '剖宫产病死率',
    '慢性阻塞性肺疾病病死率'
)
ORDER BY metric_code;
