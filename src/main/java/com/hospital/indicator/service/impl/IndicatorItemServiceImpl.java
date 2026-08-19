package com.hospital.indicator.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.hospital.indicator.common.BusinessException;
import com.hospital.indicator.dto.*;
import com.hospital.indicator.entity.IndicatorItem;
import com.hospital.indicator.mapper.IndicatorItemMapper;
import com.hospital.indicator.service.IndicatorItemService;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 指标项服务实现类
 *
 * @author Claude
 * @date 2025-12-30
 */
@Slf4j
@Service
public class IndicatorItemServiceImpl extends ServiceImpl<IndicatorItemMapper, IndicatorItem> implements IndicatorItemService {

    /**
     * 参数占位符正则表达式（匹配 #{paramName} 格式）
     */
    private static final Pattern PARAM_PATTERN = Pattern.compile("#\\{(\\w+)\\}");

    @Resource
    private JdbcTemplate jdbcTemplate;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public IndicatorItem saveOrUpdateIndicatorItem(IndicatorItemSaveDTO dto) {
        // 校验指标项编码唯一性
        LambdaQueryWrapper<IndicatorItem> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(IndicatorItem::getItemCode, dto.getItemCode());
        if (dto.getId() != null) {
            queryWrapper.ne(IndicatorItem::getId, dto.getId());
        }
        if (this.count(queryWrapper) > 0) {
            throw new BusinessException("指标项编码已存在：" + dto.getItemCode());
        }

        // 校验SQL有效性（如果有SQL）
        if (StringUtils.isNotBlank(dto.getQuerySql()) && !validateSql(dto.getQuerySql())) {
            throw new BusinessException("SQL语句格式不正确");
        }

        // 转换DTO为实体
        IndicatorItem entity = new IndicatorItem();
        BeanUtils.copyProperties(dto, entity);

        // 保存或更新
        this.saveOrUpdate(entity);
        return entity;
    }

    @Override
    public IndicatorItemExecuteResultDTO executeQuery(String itemCode, String startDate, String endDate, Map<String, Object> params) {
        IndicatorItemExecuteResultDTO result = new IndicatorItemExecuteResultDTO();

        try {
            // 1. 根据编码查找指标项
            LambdaQueryWrapper<IndicatorItem> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(IndicatorItem::getItemCode, itemCode);
            IndicatorItem item = this.getOne(queryWrapper);

            if (item == null) {
                throw new BusinessException("指标项不存在：" + itemCode);
            }

            if (item.getStatus() != 1) {
                throw new BusinessException("指标项已禁用：" + itemCode);
            }

            if (StringUtils.isBlank(item.getQuerySql())) {
                throw new BusinessException("指标项未配置SQL查询：" + itemCode);
            }

            // 2. 准备参数Map
            Map<String, Object> paramMap = new HashMap<>();
            paramMap.put("startDate", startDate);
            paramMap.put("endDate", endDate);
            if (params != null) {
                paramMap.putAll(params);
            }

            // 3. 替换SQL中的参数占位符
            String querySql = replaceSqlParams(item.getQuerySql(), paramMap);
            log.info("执行指标项查询 [{}]: {}", itemCode, querySql);

            // 4. 执行SQL查询
            Object queryResult = baseMapper.executeSingleValueQuery(querySql);

            // 5. 封装返回结果
            Map<String, Object> resultMap = new HashMap<>();
            resultMap.put("result_value", queryResult);
            resultMap.put("item_code", itemCode);
            resultMap.put("item_name", item.getItemName());
            resultMap.put("unit", item.getUnit());

            result.setSuccess(true);
            result.setResult(resultMap);
            result.setQuerySql(querySql);

        } catch (Exception e) {
            log.error("执行指标项查询失败 [{}]: {}", itemCode, e.getMessage(), e);
            result.setSuccess(false);
            result.setErrorMessage(e.getMessage());
        }

        return result;
    }

    @Override
    public boolean validateSql(String sql) {
        if (StringUtils.isBlank(sql)) {
            return false;
        }

        try {
            // 基本的SQL关键字检查
            String upperSql = sql.trim().toUpperCase();

            // 必须是SELECT语句
            if (!upperSql.startsWith("SELECT")) {
                return false;
            }

            // 禁止包含危险操作（INSERT、UPDATE、DELETE、DROP、TRUNCATE等）
            if (upperSql.contains("INSERT") || upperSql.contains("UPDATE") ||
                    upperSql.contains("DELETE") || upperSql.contains("DROP") ||
                    upperSql.contains("TRUNCATE") || upperSql.contains("ALTER")) {
                return false;
            }

            // 检查SQL基本结构（必须包含FROM关键字）
            if (!upperSql.contains("FROM")) {
                return false;
            }

            return true;
        } catch (Exception e) {
            log.error("SQL校验异常: {}", e.getMessage(), e);
            return false;
        }
    }

    /**
     * 替换SQL中的参数占位符
     * 将 #{paramName} 替换为实际参数值
     *
     * @param sql      原始SQL
     * @param paramMap 参数Map
     * @return 替换后的SQL
     */
    private String replaceSqlParams(String sql, Map<String, Object> paramMap) {
        if (StringUtils.isBlank(sql) || paramMap == null || paramMap.isEmpty()) {
            return sql;
        }

        StringBuffer result = new StringBuffer();
        Matcher matcher = PARAM_PATTERN.matcher(sql);

        while (matcher.find()) {
            String paramName = matcher.group(1);  // 获取参数名（不包括 #{} ）
            Object paramValue = paramMap.get(paramName);

            // 如果参数不存在，抛出异常
            if (paramValue == null) {
                throw new BusinessException("SQL参数缺失：" + paramName);
            }

            // 替换参数（字符串类型需要加单引号）
            String replacement;
            if (paramValue instanceof String) {
                replacement = "'" + paramValue + "'";
            } else {
                replacement = paramValue.toString();
            }

            matcher.appendReplacement(result, replacement);
        }
        matcher.appendTail(result);

        return result.toString();
    }

    @Override
    public ExplainResult analyzeWithExplain(String sql) {
        try {
            String explainSql = "EXPLAIN " + sql;
            log.info("执行EXPLAIN分析: {}", explainSql);

            List<Map<String, Object>> explainRows = jdbcTemplate.queryForList(explainSql);

            return parseExplainResult(explainRows);

        } catch (Exception e) {
            log.error("EXPLAIN分析失败: {}", sql, e);
            return ExplainResult.conservative();
        }
    }

    private ExplainResult parseExplainResult(List<Map<String, Object>> explainRows) {
        ExplainResult result = new ExplainResult();

        long totalRows = 0;
        boolean hasFullTableScan = false;
        boolean hasIndexScan = false;
        StringBuilder accessType = new StringBuilder();

        for (Map<String, Object> row : explainRows) {
            Object rowsObj = row.get("rows");
            if (rowsObj != null) {
                totalRows += Long.parseLong(rowsObj.toString());
            }

            String type = (String) row.get("type");
            if ("ALL".equals(type)) {
                hasFullTableScan = true;
            } else if ("index".equals(type) || "range".equals(type)) {
                hasIndexScan = true;
            }
            if (accessType.length() > 0) {
                accessType.append(",");
            }
            accessType.append(type);

            String key = (String) row.get("key");
            result.addUsedIndex(key);

            log.debug("EXPLAIN行: type={}, rows={}, key={}", type, rowsObj, key);
        }

        result.setEstimatedRows(totalRows);
        result.setHasFullTableScan(hasFullTableScan);
        result.setHasIndexScan(hasIndexScan);
        result.setAccessType(accessType.toString());

        log.info("EXPLAIN分析结果: 预估{}行, 访问类型={}, 全表扫描={}",
                totalRows, accessType, hasFullTableScan);

        return result;
    }

    @Override
    public String detectSliceField(String sql, Map<String, Object> params) {
        if (!params.containsKey("startDate") || !params.containsKey("endDate")) {
            return null;
        }

        Pattern pattern = Pattern.compile("(\\w+)\\s*>=\\s*#\\{startDate\\}", Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(sql);

        if (matcher.find()) {
            String fieldName = matcher.group(1);
            log.info("检测到切片字段: {}", fieldName);
            return fieldName;
        }

        log.warn("未能从SQL中检测到切片字段");
        return null;
    }

    @Override
    public Map<String, Object> analyzeOnly(String itemCode, Map<String, Object> params) {
        IndicatorItem item = getByItemCode(itemCode);
        String sql = replaceSqlParams(item.getQuerySql(), params);

        ExplainResult explainResult = analyzeWithExplain(sql);

        Map<String, Object> response = new HashMap<>();
        response.put("itemCode", itemCode);
        response.put("itemName", item.getItemName());

        Map<String, Object> explainInfo = new HashMap<>();
        explainInfo.put("estimatedRows", explainResult.getEstimatedRows());
        explainInfo.put("estimatedTime", explainResult.getEstimatedRows() / 10000);
        explainInfo.put("hasFullTableScan", explainResult.isHasFullTableScan());
        explainInfo.put("accessType", explainResult.getAccessType());
        explainInfo.put("usedIndexes", explainResult.getUsedIndexes());
        response.put("explainResult", explainInfo);

        int costThreshold = 100000;
        if (explainResult.getEstimatedRows() > costThreshold) {
            response.put("needConfirm", true);

            String sliceField = detectSliceField(item.getQuerySql(), params);
            if (sliceField != null) {
                Map<String, Object> sliceRecommendation = buildSliceRecommendation(
                        sliceField, params, explainResult.getEstimatedRows());
                response.put("sliceRecommendation", sliceRecommendation);

                response.put("warning", String.format(
                        "预计扫描%,d行，直接执行约%d秒，切片执行约%d秒（推荐）",
                        explainResult.getEstimatedRows(),
                        (int) explainInfo.get("estimatedTime"),
                        (int) sliceRecommendation.get("estimatedTimeWithSlice")
                ));
            } else {
                response.put("warning", String.format(
                        "预计扫描%,d行，约%d秒，未检测到切片字段，建议优化SQL或添加索引",
                        explainResult.getEstimatedRows(),
                        (int) explainInfo.get("estimatedTime")
                ));
            }
        } else {
            response.put("needConfirm", false);
            response.put("message", String.format(
                    "预估成本较低（%,d行），可直接执行",
                    explainResult.getEstimatedRows()
            ));
        }

        return response;
    }

    private Map<String, Object> buildSliceRecommendation(String sliceField,
                                                          Map<String, Object> params,
                                                          long estimatedRows) {
        Map<String, Object> recommendation = new HashMap<>();
        recommendation.put("sliceField", sliceField);

        LocalDate startDate = parseDate(params.get("startDate"));
        LocalDate endDate = parseDate(params.get("endDate"));
        long days = ChronoUnit.DAYS.between(startDate, endDate);

        String recommendInterval;
        int sliceCount;
        if (days > 365) {
            recommendInterval = "MONTH";
            sliceCount = (int) ChronoUnit.MONTHS.between(startDate, endDate);
        } else if (days > 90) {
            recommendInterval = "WEEK";
            sliceCount = (int) ChronoUnit.WEEKS.between(startDate, endDate);
        } else {
            recommendInterval = "DAY";
            sliceCount = (int) days;
        }

        recommendation.put("interval", recommendInterval);
        recommendation.put("sliceCount", Math.min(sliceCount, 12));
        recommendation.put("estimatedTimeWithSlice", estimatedRows / 100000);

        return recommendation;
    }

    private LocalDate parseDate(Object dateObj) {
        if (dateObj instanceof LocalDate) {
            return (LocalDate) dateObj;
        } else if (dateObj instanceof String) {
            return LocalDate.parse((String) dateObj);
        }
        throw new BusinessException("无效的日期格式: " + dateObj);
    }

    @Override
    public Map<String, Object> executeDirect(String itemCode, Map<String, Object> params) {
        IndicatorItem item = getByItemCode(itemCode);
        String sql = replaceSqlParams(item.getQuerySql(), params);

        log.info("直接执行指标项: {}", itemCode);
        long startTime = System.currentTimeMillis();

        Map<String, Object> result = jdbcTemplate.queryForMap(sql);

        long execTime = System.currentTimeMillis() - startTime;
        result.put("executionMode", "DIRECT");
        result.put("actualTime", execTime / 1000.0);

        log.info("直接执行完成，耗时{}ms", execTime);
        return result;
    }

    @Override
    public Map<String, Object> executeWithSlice(String itemCode, Map<String, Object> params, SliceConfig sliceConfig) {
        IndicatorItem item = getByItemCode(itemCode);

        List<SlicePart> slices = buildDateSlices(params, sliceConfig);

        log.info("开始切片执行，共{}个切片", slices.size());
        long startTime = System.currentTimeMillis();

        List<Map<String, Object>> sliceResults = slices.parallelStream()
                .map(slice -> {
                    try {
                        String sql = replaceSqlParams(item.getQuerySql(), slice.getParams());
                        Map<String, Object> result = jdbcTemplate.queryForMap(sql);

                        log.debug("切片{}执行完成: {}", slice.getName(), result);
                        return result;

                    } catch (Exception e) {
                        log.error("切片{}执行失败", slice.getName(), e);
                        throw new BusinessException("切片执行失败: " + slice.getName(), e);
                    }
                })
                .collect(Collectors.toList());

        Map<String, Object> merged = mergeSliceResults(sliceResults, item);

        long execTime = System.currentTimeMillis() - startTime;
        merged.put("executionMode", "SLICED");
        merged.put("sliceCount", slices.size());
        merged.put("actualTime", execTime / 1000.0);

        log.info("切片执行完成，耗时{}ms", execTime);
        return merged;
    }

    private List<SlicePart> buildDateSlices(Map<String, Object> params, SliceConfig sliceConfig) {
        List<SlicePart> slices = new ArrayList<>();

        LocalDate startDate = parseDate(params.get("startDate"));
        LocalDate endDate = parseDate(params.get("endDate"));
        String interval = sliceConfig.getInterval();
        int maxSlices = sliceConfig.getMaxSlices();

        LocalDate currentStart = startDate;
        int count = 0;

        while (currentStart.isBefore(endDate) && count < maxSlices) {
            LocalDate currentEnd = calculateNextSliceEnd(currentStart, interval, endDate);

            Map<String, Object> sliceParams = new HashMap<>(params);
            sliceParams.put("startDate", currentStart);
            sliceParams.put("endDate", currentEnd);

            SlicePart slice = new SlicePart(
                    count,
                    String.format("%s ~ %s", currentStart, currentEnd),
                    sliceParams
            );
            slices.add(slice);

            currentStart = currentEnd;
            count++;
        }

        log.info("生成{}个日期切片, 间隔={}", slices.size(), interval);
        return slices;
    }

    private LocalDate calculateNextSliceEnd(LocalDate start, String interval, LocalDate maxEnd) {
        LocalDate end;
        switch (interval.toUpperCase()) {
            case "DAY":
                end = start.plusDays(1);
                break;
            case "WEEK":
                end = start.plusWeeks(1);
                break;
            case "MONTH":
                end = start.plusMonths(1);
                break;
            case "QUARTER":
                end = start.plusMonths(3);
                break;
            case "YEAR":
                end = start.plusYears(1);
                break;
            default:
                throw new BusinessException("不支持的切片间隔: " + interval);
        }
        return end.isAfter(maxEnd) ? maxEnd : end;
    }

    private Map<String, Object> mergeSliceResults(List<Map<String, Object>> sliceResults, IndicatorItem item) {
        String aggregateFunction = item.getAggregateFunction();
        if (aggregateFunction == null) {
            aggregateFunction = "SUM";
        }

        Map<String, Object> merged = new HashMap<>();

        List<Number> values = sliceResults.stream()
                .map(r -> (Number) r.values().iterator().next())
                .collect(Collectors.toList());

        Number finalValue;
        switch (aggregateFunction.toUpperCase()) {
            case "COUNT":
            case "SUM":
                finalValue = values.stream()
                        .mapToLong(Number::longValue)
                        .sum();
                break;

            case "AVG":
                finalValue = values.stream()
                        .mapToDouble(Number::doubleValue)
                        .average()
                        .orElse(0.0);
                break;

            case "MAX":
                finalValue = values.stream()
                        .mapToLong(Number::longValue)
                        .max()
                        .orElse(0L);
                break;

            case "MIN":
                finalValue = values.stream()
                        .mapToLong(Number::longValue)
                        .min()
                        .orElse(0L);
                break;

            default:
                throw new BusinessException("不支持的聚合函数: " + aggregateFunction);
        }

        merged.put("value", finalValue);
        log.info("切片结果合并完成: {}个切片 -> {}", values.size(), finalValue);

        return merged;
    }

    @Override
    public IndicatorItem getByItemCode(String itemCode) {
        LambdaQueryWrapper<IndicatorItem> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(IndicatorItem::getItemCode, itemCode);
        IndicatorItem item = this.getOne(wrapper);

        if (item == null) {
            throw new BusinessException("指标项不存在: " + itemCode);
        }

        return item;
    }

}
