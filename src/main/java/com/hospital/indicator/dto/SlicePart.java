package com.hospital.indicator.dto;

import lombok.Data;
import java.util.Map;

@Data
public class SlicePart {
    private int index;                      // 切片索引
    private String name;                    // 切片名称（如：2026-01-01 ~ 2026-02-01）
    private Map<String, Object> params;     // 切片参数

    public SlicePart() {}

    public SlicePart(int index, String name, Map<String, Object> params) {
        this.index = index;
        this.name = name;
        this.params = params;
    }
}
