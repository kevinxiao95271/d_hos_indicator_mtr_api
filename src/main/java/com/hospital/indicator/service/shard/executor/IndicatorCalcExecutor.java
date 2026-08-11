package com.hospital.indicator.service.shard.executor;

import com.hospital.indicator.service.IndicatorItemService;
import com.hospital.indicator.service.shard.ShardTaskService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;

/**
 * 指标计算执行器
 *
 * <p>将指标项的 SQL 执行能力接入分片任务框架。支持按时间切片批量计算指标。</p>
 *
 * <p>使用场景：
 * <ul>
 *   <li>批量计算某指标过去12个月的数据（按月切片）</li>
 *   <li>批量计算某指标过去4个季度的数据（按季切片）</li>
 *   <li>年度指标回溯计算（按年切片）</li>
 * </ul>
 *
 * <p>参数格式：
 * <pre>
 * {
 *   "itemCode": "a0050",           // 指标项编码
 *   "startDate": "2026-01-01",     // 本片开始日期
 *   "endDate": "2026-01-31"        // 本片结束日期
 * }
 * </pre>
 *
 * @author Claude
 * @date 2026-08-10
 */
@Slf4j
@Component
public class IndicatorCalcExecutor implements ShardTaskService.ShardTaskExecutor {

    @Autowired
    private ShardTaskService shardTaskService;

    @Autowired
    private IndicatorItemService indicatorItemService;

    @PostConstruct
    public void register() {
        shardTaskService.registerExecutor("INDICATOR_CALC", this);
        log.info("IndicatorCalcExecutor 已注册到分片任务框架");
    }

    @Override
    public String execute(Map<String, Object> params) throws Exception {
        String itemCode = (String) params.get("itemCode");
        String startDate = (String) params.get("startDate");
        String endDate = (String) params.get("endDate");

        if (itemCode == null || startDate == null || endDate == null) {
            throw new IllegalArgumentException("缺少必要参数: itemCode, startDate, endDate");
        }

        log.info("执行指标计算: itemCode={}, startDate={}, endDate={}", itemCode, startDate, endDate);

        // 调用现有的 executeDirect 方法
        Map<String, Object> sqlParams = new HashMap<>();
        sqlParams.put("startDate", startDate);
        sqlParams.put("endDate", endDate);
        Map<String, Object> result = indicatorItemService.executeDirect(itemCode, sqlParams);

        // 提取结果值
        Object value = result.get("value");
        Long rows = (Long) result.get("rows");

        String summary = String.format("value=%s, rows=%d", value, rows != null ? rows : 0);
        log.info("指标计算完成: {}", summary);

        return summary;
    }
}
