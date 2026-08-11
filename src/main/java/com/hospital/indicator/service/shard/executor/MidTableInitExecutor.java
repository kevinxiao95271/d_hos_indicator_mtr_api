package com.hospital.indicator.service.shard.executor;

import com.hospital.indicator.service.shard.ShardTaskService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.List;
import java.util.Map;

/**
 * 中间表初始化执行器
 *
 * <p>为分片任务框架提供中间表数据初始化能力。支持按时间切片批量初始化历史数据。</p>
 *
 * <p>使用场景：
 * <ul>
 *   <li>单病种数据初始化（按月切片，每月一片）</li>
 *   <li>专业质控数据初始化（按季度切片）</li>
 *   <li>年度数据回溯（按年切片）</li>
 * </ul>
 *
 * <p>参数格式：
 * <pre>
 * {
 *   "tableName": "mid_pneumonia",     // 目标中间表名
 *   "sourceSql": "SELECT ...",        // 初始化SQL（带 #{startDate} #{endDate} 占位符）
 *   "startDate": "2026-01-01",        // 本片开始日期
 *   "endDate": "2026-01-31"           // 本片结束日期
 * }
 * </pre>
 *
 * @author Claude
 * @date 2026-08-10
 */
@Slf4j
@Component
public class MidTableInitExecutor implements ShardTaskService.ShardTaskExecutor {

    @Autowired
    private ShardTaskService shardTaskService;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @PostConstruct
    public void register() {
        shardTaskService.registerExecutor("MID_TABLE_INIT", this);
        log.info("MidTableInitExecutor 已注册到分片任务框架");
    }

    @Override
    public String execute(Map<String, Object> params) throws Exception {
        String tableName = (String) params.get("tableName");
        String sourceSql = (String) params.get("sourceSql");
        String startDate = (String) params.get("startDate");
        String endDate = (String) params.get("endDate");

        if (tableName == null || sourceSql == null || startDate == null || endDate == null) {
            throw new IllegalArgumentException("缺少必要参数: tableName, sourceSql, startDate, endDate");
        }

        log.info("初始化中间表: table={}, startDate={}, endDate={}", tableName, startDate, endDate);

        // 替换占位符
        String actualSql = sourceSql
                .replace("#{startDate}", "'" + startDate + "'")
                .replace("#{endDate}", "'" + endDate + "'");

        // 执行 INSERT INTO ... SELECT ... 或 DELETE + INSERT
        int affectedRows;

        if (sourceSql.trim().toUpperCase().startsWith("INSERT")) {
            // 直接执行 INSERT
            affectedRows = jdbcTemplate.update(actualSql);
        } else {
            // 先删除该时间段的旧数据，再插入新数据
            String deleteSql = String.format(
                    "DELETE FROM %s WHERE data_date >= '%s' AND data_date <= '%s'",
                    tableName, startDate, endDate
            );
            jdbcTemplate.update(deleteSql);

            // 执行 INSERT
            String insertSql = String.format("INSERT INTO %s %s", tableName, actualSql);
            affectedRows = jdbcTemplate.update(insertSql);
        }

        String summary = String.format("table=%s, rows=%d, date=%s~%s",
                tableName, affectedRows, startDate, endDate);
        log.info("中间表初始化完成: {}", summary);

        return summary;
    }
}
