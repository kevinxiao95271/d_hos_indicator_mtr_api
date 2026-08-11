package com.hospital.indicator.util;

import org.junit.jupiter.api.Test;

import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * SliceGenerator 单元测试
 *
 * <p>纯单测，不依赖数据库，验证切片生成逻辑正确性</p>
 *
 * @author Claude
 * @date 2026-08-10
 */
class SliceGeneratorTest {

    @Test
    void testGenerateTimeSlices_Monthly_Success() {
        System.out.println("\n========== 测试: 按月生成时间切片 ==========");

        List<Map<String, Object>> slices = SliceGenerator.generateTimeSlices(
                "2026-01-01", "2026-03-31", "MONTH");

        assertEquals(3, slices.size(), "2026年Q1应生成3个月切片");

        Map<String, Object> slice1 = slices.get(0);
        assertEquals("2026-01-01", slice1.get("startDate"));
        assertEquals("2026-01-31", slice1.get("endDate"));
        System.out.println("切片1: " + slice1);

        Map<String, Object> slice2 = slices.get(1);
        assertEquals("2026-02-01", slice2.get("startDate"));
        assertEquals("2026-02-28", slice2.get("endDate"));
        System.out.println("切片2: " + slice2);

        Map<String, Object> slice3 = slices.get(2);
        assertEquals("2026-03-01", slice3.get("startDate"));
        assertEquals("2026-03-31", slice3.get("endDate"));
        System.out.println("切片3: " + slice3);

        System.out.println("✓ 按月切片生成正确\n");
    }

    @Test
    void testGenerateTimeSlices_Quarterly_Success() {
        System.out.println("\n========== 测试: 按季度生成时间切片 ==========");

        List<Map<String, Object>> slices = SliceGenerator.generateTimeSlices(
                "2026-01-01", "2026-12-31", "QUARTER");

        assertEquals(4, slices.size(), "全年应生成4个季度切片");

        Map<String, Object> q1 = slices.get(0);
        assertEquals("2026-01-01", q1.get("startDate"));
        assertEquals("2026-03-31", q1.get("endDate"));
        System.out.println("Q1: " + q1);

        Map<String, Object> q4 = slices.get(3);
        assertEquals("2026-10-01", q4.get("startDate"));
        assertEquals("2026-12-31", q4.get("endDate"));
        System.out.println("Q4: " + q4);

        System.out.println("✓ 按季度切片生成正确\n");
    }

    @Test
    void testGenerateKeySlices_Success() {
        System.out.println("\n========== 测试: 按键值生成切片 ==========");

        List<String> deptList = Arrays.asList("D001", "D002", "D003", "D004", "D005");
        List<Map<String, Object>> slices = SliceGenerator.generateKeySlices(deptList, 2);

        assertEquals(3, slices.size(), "5个科室按每批2个应生成3个切片");

        @SuppressWarnings("unchecked")
        List<String> batch1 = (List<String>) slices.get(0).get("keyList");
        assertEquals(2, batch1.size());
        assertEquals("D001", batch1.get(0));
        assertEquals("D002", batch1.get(1));
        System.out.println("批次1: " + batch1);

        @SuppressWarnings("unchecked")
        List<String> batch3 = (List<String>) slices.get(2).get("keyList");
        assertEquals(1, batch3.size());
        assertEquals("D005", batch3.get(0));
        System.out.println("批次3: " + batch3);

        System.out.println("✓ 键值切片生成正确\n");
    }

    @Test
    void testGenerateRowSlices_Success() {
        System.out.println("\n========== 测试: 按行数生成切片 ==========");

        List<Map<String, Object>> slices = SliceGenerator.generateRowSlices(1, 1000, 10);

        assertEquals(10, slices.size(), "1000行按10片应生成10个切片");

        Map<String, Object> slice1 = slices.get(0);
        assertEquals(1L, slice1.get("minId"));
        assertEquals(100L, slice1.get("maxId"));
        System.out.println("切片1: " + slice1);

        Map<String, Object> slice10 = slices.get(9);
        assertEquals(901L, slice10.get("minId"));
        assertEquals(1000L, slice10.get("maxId"));
        System.out.println("切片10: " + slice10);

        System.out.println("✓ 行数切片生成正确\n");
    }

    @Test
    void testDetectStrategy_TimeSlice() {
        System.out.println("\n========== 测试: 策略检测 - 时间切片 ==========");

        List<Map<String, Object>> slices = SliceGenerator.generateTimeSlices(
                "2026-01-01", "2026-03-31", "MONTH");

        String strategy = SliceGenerator.detectStrategy(slices);
        assertEquals("TIME_SLICE", strategy);
        System.out.println("检测策略: " + strategy);
        System.out.println("✓ 时间切片策略识别正确\n");
    }

    @Test
    void testDetectStrategy_KeySlice() {
        System.out.println("\n========== 测试: 策略检测 - 键值切片 ==========");

        List<Map<String, Object>> slices = SliceGenerator.generateKeySlices(
                Arrays.asList("D001", "D002", "D003"), 2);

        String strategy = SliceGenerator.detectStrategy(slices);
        assertEquals("KEY_SLICE", strategy);
        System.out.println("检测策略: " + strategy);
        System.out.println("✓ 键值切片策略识别正确\n");
    }

    @Test
    void testDetectStrategy_RowSlice() {
        System.out.println("\n========== 测试: 策略检测 - 行数切片 ==========");

        List<Map<String, Object>> slices = SliceGenerator.generateRowSlices(1, 1000, 5);

        String strategy = SliceGenerator.detectStrategy(slices);
        assertEquals("ROW_SLICE", strategy);
        System.out.println("检测策略: " + strategy);
        System.out.println("✓ 行数切片策略识别正确\n");
    }

    @Test
    void testEstimateTimeSliceCount() {
        System.out.println("\n========== 测试: 估算切片数量 ==========");

        int monthCount = SliceGenerator.estimateTimeSliceCount("2026-01-01", "2026-12-31", "MONTH");
        assertEquals(12, monthCount);
        System.out.println("全年按月: " + monthCount + " 片");

        int quarterCount = SliceGenerator.estimateTimeSliceCount("2026-01-01", "2026-12-31", "QUARTER");
        assertEquals(4, quarterCount);
        System.out.println("全年按季度: " + quarterCount + " 片");

        int yearCount = SliceGenerator.estimateTimeSliceCount("2024-01-01", "2026-12-31", "YEAR");
        assertEquals(3, yearCount);
        System.out.println("3年按年: " + yearCount + " 片");

        System.out.println("✓ 切片数量估算正确\n");
    }

    @Test
    void testGenerateDeptTimeSlices() {
        System.out.println("\n========== 测试: 科室×时间二维切片 ==========");

        List<String> deptList = Arrays.asList("D001", "D002");
        List<Map<String, Object>> slices = SliceGenerator.generateDeptTimeSlices(
                deptList, "2026-01-01", "2026-02-28");

        // 2个科室 × 2个月 = 4个切片
        assertEquals(4, slices.size());

        Map<String, Object> slice1 = slices.get(0);
        assertEquals("D001", slice1.get("deptCode"));
        assertEquals("2026-01-01", slice1.get("startDate"));
        assertEquals("2026-01-31", slice1.get("endDate"));
        System.out.println("切片1: " + slice1);

        Map<String, Object> slice4 = slices.get(3);
        assertEquals("D002", slice4.get("deptCode"));
        assertEquals("2026-02-01", slice4.get("startDate"));
        assertEquals("2026-02-28", slice4.get("endDate"));
        System.out.println("切片4: " + slice4);

        System.out.println("✓ 二维切片生成正确\n");
    }

    @Test
    void testEdgeCases() {
        System.out.println("\n========== 测试: 边界情况 ==========");

        // 单月
        List<Map<String, Object>> singleMonth = SliceGenerator.generateTimeSlices(
                "2026-01-01", "2026-01-31", "MONTH");
        assertEquals(1, singleMonth.size());
        System.out.println("单月切片数: " + singleMonth.size());

        // 跨年
        List<Map<String, Object>> crossYear = SliceGenerator.generateTimeSlices(
                "2025-11-01", "2026-02-28", "MONTH");
        assertEquals(4, crossYear.size()); // 11月、12月、1月、2月
        System.out.println("跨年切片数: " + crossYear.size());

        // 闰年2月
        List<Map<String, Object>> leapYear = SliceGenerator.generateTimeSlices(
                "2024-02-01", "2024-02-29", "MONTH");
        assertEquals(1, leapYear.size());
        assertEquals("2024-02-29", leapYear.get(0).get("endDate"));
        System.out.println("闰年2月结束日期: " + leapYear.get(0).get("endDate"));

        System.out.println("✓ 边界情况处理正确\n");
    }
}
