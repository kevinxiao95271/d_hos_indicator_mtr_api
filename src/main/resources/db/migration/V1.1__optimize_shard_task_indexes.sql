-- 分片任务表索引优化脚本
-- 日期: 2026-08-10
-- 说明: 添加复合索引以优化分片任务查询性能

-- 1. 为 shard_task 表添加复合索引
-- 场景：按业务类型+状态查询任务列表
ALTER TABLE shard_task
ADD INDEX IF NOT EXISTS idx_biz_status (`biz_type`, `status`, `create_time`);

-- 2. 为 shard_task_slice 表添加复合索引
-- 场景：查询某任务的待处理/失败切片
ALTER TABLE shard_task_slice
ADD INDEX IF NOT EXISTS idx_task_status_no (`task_id`, `status`, `slice_no`);

-- 3. 为 shard_task_slice 表添加执行时间索引
-- 场景：分析慢切片，统计平均执行时间
ALTER TABLE shard_task_slice
ADD INDEX IF NOT EXISTS idx_start_end_time (`start_time`, `end_time`);

SELECT 'Index optimization completed successfully!' as status;
