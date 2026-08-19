package com.hospital.indicator.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "切片配置（临时，不持久化）")
public class SliceConfig {

    @Schema(description = "切片字段名（如：入院日期）")
    private String sliceField;

    @Schema(description = "切片间隔", allowableValues = {"DAY", "WEEK", "MONTH", "QUARTER", "YEAR"})
    private String interval;

    @Schema(description = "最大切片数")
    private Integer maxSlices = 12;
}
