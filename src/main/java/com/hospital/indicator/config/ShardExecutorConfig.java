package com.hospital.indicator.config;

import com.hospital.indicator.entity.shard.ShardTask;
import com.hospital.indicator.service.IndicatorCalculationService;
import com.hospital.indicator.service.shard.ShardTaskService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;

import javax.annotation.PostConstruct;
import java.time.LocalDate;

/**
 * 分片业务执行器注册
 *
 * <p>把已实现的大任务注册为分片框架的 bizType 执行器,业务侧只需实现
 * "给定参数执行一片"。当前注册指标计算(INDICATOR_CALC)。</p>
 *
 * @author Claude
 * @date 2026-08-09
 */
@Slf4j
@Configuration
public class ShardExecutorConfig {

    @Autowired
    private ShardTaskService shardTaskService;

    @Autowired
    private IndicatorCalculationService calculationService;

    @PostConstruct
    public void registerExecutors() {
        // 指标计算:每片参数 {metricCode, timeDimension, start, end}
        // 第四章单病种/时间片场景:前端按病种或时间段拆片提交即可
        shardTaskService.registerExecutor(ShardTask.BIZ_INDICATOR_CALC, params -> {
            String metricCode = str(params.get("metricCode"));
            String timeDimension = str(params.get("timeDimension"));
            LocalDate start = LocalDate.parse(str(params.get("start")));
            LocalDate end = LocalDate.parse(str(params.get("end")));

            com.hospital.indicator.entity.IndicatorResult result =
                    calculationService.calculateIndicator(metricCode, timeDimension, start, end);
            if (!"SUCCESS".equals(result.getCalculationStatus())) {
                throw new RuntimeException("指标计算失败: " + result.getErrorMessage());
            }
            return metricCode + "@" + result.getTimeValue() + "=" + result.getResultValue();
        });
        log.info("已注册分片执行器: bizType={}", ShardTask.BIZ_INDICATOR_CALC);
    }

    private String str(Object o) {
        return o == null ? null : String.valueOf(o);
    }
}
