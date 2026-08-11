package com.hospital.indicator.util;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 切片生成工具类
 *
 * <p>为分片任务框架提供自动切片生成能力。支持：
 * <ul>
 *   <li>时间切片：按日/周/月/季/年拆分时间范围</li>
 *   <li>键值切片：将编码/科室列表拆成N个批次</li>
 *   <li>行数切片：将ID范围拆成N个区间</li>
 * </ul>
 *
 * @author Claude
 * @date 2026-08-10
 */
public class SliceGenerator {

    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    /**
     * 生成时间切片（按指定间隔拆分日期范围）
     *
     * @param startDate 开始日期（yyyy-MM-dd）
     * @param endDate   结束日期（yyyy-MM-dd）
     * @param interval  间隔：DAY / WEEK / MONTH / QUARTER / YEAR
     * @return 切片列表，每片包含 startDate 和 endDate
     */
    public static List<Map<String, Object>> generateTimeSlices(String startDate, String endDate, String interval) {
        LocalDate start = LocalDate.parse(startDate, DATE_FORMATTER);
        LocalDate end = LocalDate.parse(endDate, DATE_FORMATTER);

        if (start.isAfter(end)) {
            throw new IllegalArgumentException("开始日期不能晚于结束日期");
        }

        List<Map<String, Object>> slices = new ArrayList<>();
        LocalDate current = start;

        while (current.isBefore(end) || current.isEqual(end)) {
            LocalDate sliceEnd = calculateSliceEnd(current, end, interval);

            Map<String, Object> slice = new LinkedHashMap<>();
            slice.put("startDate", current.format(DATE_FORMATTER));
            slice.put("endDate", sliceEnd.format(DATE_FORMATTER));
            slices.add(slice);

            current = sliceEnd.plusDays(1);
        }

        return slices;
    }

    /**
     * 计算单个切片的结束日期
     */
    private static LocalDate calculateSliceEnd(LocalDate current, LocalDate globalEnd, String interval) {
        LocalDate sliceEnd;

        switch (interval.toUpperCase()) {
            case "DAY":
                sliceEnd = current;
                break;
            case "WEEK":
                sliceEnd = current.plusWeeks(1).minusDays(1);
                break;
            case "MONTH":
                sliceEnd = current.plusMonths(1).minusDays(1);
                break;
            case "QUARTER":
                sliceEnd = current.plusMonths(3).minusDays(1);
                break;
            case "YEAR":
                sliceEnd = current.plusYears(1).minusDays(1);
                break;
            default:
                throw new IllegalArgumentException("不支持的时间间隔: " + interval);
        }

        // 不能超过全局结束日期
        return sliceEnd.isAfter(globalEnd) ? globalEnd : sliceEnd;
    }

    /**
     * 生成键值切片（将列表拆成N个批次）
     *
     * @param keyList   键值列表（如科室编码、手术编码等）
     * @param chunkSize 每批大小
     * @return 切片列表，每片包含 keyList（子列表）
     */
    public static List<Map<String, Object>> generateKeySlices(List<String> keyList, int chunkSize) {
        if (keyList == null || keyList.isEmpty()) {
            throw new IllegalArgumentException("键值列表不能为空");
        }
        if (chunkSize <= 0) {
            throw new IllegalArgumentException("批次大小必须大于0");
        }

        List<Map<String, Object>> slices = new ArrayList<>();
        for (int i = 0; i < keyList.size(); i += chunkSize) {
            int end = Math.min(i + chunkSize, keyList.size());
            List<String> subList = keyList.subList(i, end);

            Map<String, Object> slice = new LinkedHashMap<>();
            slice.put("keyList", subList);
            slices.add(slice);
        }

        return slices;
    }

    /**
     * 生成键值切片（自动分成N片）
     *
     * @param keyList    键值列表
     * @param sliceCount 期望的切片数量
     * @return 切片列表
     */
    public static List<Map<String, Object>> generateKeySlicesAuto(List<String> keyList, int sliceCount) {
        if (keyList == null || keyList.isEmpty()) {
            throw new IllegalArgumentException("键值列表不能为空");
        }
        if (sliceCount <= 0) {
            throw new IllegalArgumentException("切片数量必须大于0");
        }

        int chunkSize = (int) Math.ceil((double) keyList.size() / sliceCount);
        return generateKeySlices(keyList, chunkSize);
    }

    /**
     * 生成行数切片（按ID范围拆分）
     *
     * @param minId      最小ID
     * @param maxId      最大ID
     * @param sliceCount 切片数量
     * @return 切片列表，每片包含 minId 和 maxId
     */
    public static List<Map<String, Object>> generateRowSlices(long minId, long maxId, int sliceCount) {
        if (minId > maxId) {
            throw new IllegalArgumentException("最小ID不能大于最大ID");
        }
        if (sliceCount <= 0) {
            throw new IllegalArgumentException("切片数量必须大于0");
        }

        List<Map<String, Object>> slices = new ArrayList<>();
        long totalRows = maxId - minId + 1;
        long rowsPerSlice = (long) Math.ceil((double) totalRows / sliceCount);

        for (int i = 0; i < sliceCount; i++) {
            long sliceMinId = minId + i * rowsPerSlice;
            long sliceMaxId = Math.min(sliceMinId + rowsPerSlice - 1, maxId);

            if (sliceMinId > maxId) break;

            Map<String, Object> slice = new LinkedHashMap<>();
            slice.put("minId", sliceMinId);
            slice.put("maxId", sliceMaxId);
            slices.add(slice);
        }

        return slices;
    }

    /**
     * 自动生成科室切片（按科室列表+日期范围）
     *
     * @param deptList  科室列表
     * @param startDate 开始日期
     * @param endDate   结束日期
     * @return 切片列表，每片包含 deptCode, startDate, endDate（科室×时间笛卡尔积）
     */
    public static List<Map<String, Object>> generateDeptTimeSlices(List<String> deptList,
                                                                    String startDate,
                                                                    String endDate) {
        if (deptList == null || deptList.isEmpty()) {
            throw new IllegalArgumentException("科室列表不能为空");
        }

        // 先按月生成时间切片
        List<Map<String, Object>> timeSlices = generateTimeSlices(startDate, endDate, "MONTH");

        // 然后生成科室×时间的笛卡尔积
        List<Map<String, Object>> slices = new ArrayList<>();
        for (String deptCode : deptList) {
            for (Map<String, Object> timeSlice : timeSlices) {
                Map<String, Object> slice = new LinkedHashMap<>();
                slice.put("deptCode", deptCode);
                slice.put("startDate", timeSlice.get("startDate"));
                slice.put("endDate", timeSlice.get("endDate"));
                slices.add(slice);
            }
        }

        return slices;
    }

    /**
     * 检测切片类型（根据参数自动识别）
     *
     * @param slices 切片列表
     * @return 切片策略：TIME_SLICE / KEY_SLICE / ROW_SLICE / NO_SHARD
     */
    public static String detectStrategy(List<Map<String, Object>> slices) {
        if (slices == null || slices.isEmpty()) {
            return "NO_SHARD";
        }

        Map<String, Object> first = slices.get(0);

        // 时间切片：包含 startDate 和 endDate
        if (first.containsKey("startDate") && first.containsKey("endDate")) {
            return "TIME_SLICE";
        }

        // 键值切片：包含 keyList 或 deptCode
        if (first.containsKey("keyList") || first.containsKey("deptCode") || first.containsKey("codeList")) {
            return "KEY_SLICE";
        }

        // 行数切片：包含 minId 和 maxId
        if (first.containsKey("minId") && first.containsKey("maxId")) {
            return "ROW_SLICE";
        }

        // 无法识别
        return "NO_SHARD";
    }

    /**
     * 估算时间切片数量（不实际生成）
     *
     * @param startDate 开始日期
     * @param endDate   结束日期
     * @param interval  间隔
     * @return 切片数量
     */
    public static int estimateTimeSliceCount(String startDate, String endDate, String interval) {
        LocalDate start = LocalDate.parse(startDate, DATE_FORMATTER);
        LocalDate end = LocalDate.parse(endDate, DATE_FORMATTER);

        long days = ChronoUnit.DAYS.between(start, end) + 1;

        switch (interval.toUpperCase()) {
            case "DAY":
                return (int) days;
            case "WEEK":
                return (int) Math.ceil(days / 7.0);
            case "MONTH":
                return (int) ChronoUnit.MONTHS.between(start, end.plusDays(1));
            case "QUARTER":
                return (int) Math.ceil(ChronoUnit.MONTHS.between(start, end.plusDays(1)) / 3.0);
            case "YEAR":
                return (int) ChronoUnit.YEARS.between(start, end.plusDays(1));
            default:
                throw new IllegalArgumentException("不支持的时间间隔: " + interval);
        }
    }
}
