package com.hospital.indicator.dto;

import lombok.Data;
import java.util.ArrayList;
import java.util.List;

@Data
public class ExplainResult {

    private long estimatedRows;           // 预估扫描行数
    private boolean hasFullTableScan;     // 是否全表扫描
    private boolean hasIndexScan;         // 是否索引扫描
    private String accessType;            // 访问类型（ALL/index/range等）
    private List<String> usedIndexes = new ArrayList<>();  // 使用的索引

    /**
     * 保守估计（当EXPLAIN失败时使用）
     */
    public static ExplainResult conservative() {
        ExplainResult result = new ExplainResult();
        result.setEstimatedRows(1000000);  // 保守估计100万行
        result.setHasFullTableScan(true);
        result.setAccessType("UNKNOWN");
        return result;
    }

    public void addUsedIndex(String index) {
        if (index != null && !"NULL".equals(index)) {
            this.usedIndexes.add(index);
        }
    }
}
