package com.hospital.indicator.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.util.Map;

@Data
@Schema(description = "指标项执行请求")
public class ExecuteRequest {

    @Schema(description = "查询参数（startDate, endDate等）")
    private Map<String, Object> params;

    @Schema(description = "执行模式：ANALYZE-仅分析, DIRECT-直接执行, SLICE-切片执行",
            allowableValues = {"ANALYZE", "DIRECT", "SLICE"})
    private String executionMode = "ANALYZE";  // 默认先分析

    @Schema(description = "切片配置（仅executionMode=SLICE时需要）")
    private SliceConfig sliceConfig;
}
