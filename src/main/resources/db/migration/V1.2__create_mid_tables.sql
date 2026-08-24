-- 中间表定义脚本
-- 供 MidTableInitExecutor 使用的示例中间表（含测试表）
-- INSERT INTO ... SELECT ... 模式，列数必须与 SELECT 对齐，不添加自增主键

CREATE TABLE IF NOT EXISTS mid_test_table (
    data_date  DATE    NOT NULL COMMENT '数据所属日期（切片起始日）',
    cnt        BIGINT  NOT NULL DEFAULT 0 COMMENT '统计数量',
    INDEX idx_data_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分片框架测试中间表';
