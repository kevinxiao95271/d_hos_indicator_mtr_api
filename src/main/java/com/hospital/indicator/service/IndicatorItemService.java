package com.hospital.indicator.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.hospital.indicator.dto.*;
import com.hospital.indicator.entity.IndicatorItem;

import java.util.Map;

/**
 * 指标项服务接口
 *
 * @author Claude
 * @date 2025-12-30
 */
public interface IndicatorItemService extends IService<IndicatorItem> {

    /**
     * 保存或更新指标项
     *
     * @param dto 指标项保存DTO
     * @return 保存后的指标项
     */
    IndicatorItem saveOrUpdateIndicatorItem(IndicatorItemSaveDTO dto);

    /**
     * 执行指标项查询
     * 该方法根据指标项编码查找对应的指标项配置，
     * 替换SQL中的参数占位符（如#{startDate}、#{endDate}），
     * 然后执行SQL查询并返回结果
     *
     * @param itemCode  指标项编码
     * @param startDate 开始日期（格式：yyyy-MM-dd）
     * @param endDate   结束日期（格式：yyyy-MM-dd）
     * @param params    其他扩展参数（可选）
     * @return 查询结果
     */
    IndicatorItemExecuteResultDTO executeQuery(String itemCode, String startDate, String endDate, Map<String, Object> params);

    /**
     * 校验指标项SQL的有效性
     * 用于前端保存指标项时验证SQL语法是否正确
     *
     * @param sql SQL语句
     * @return 是否有效
     */
    boolean validateSql(String sql);

    /**
     * EXPLAIN分析SQL
     * @param sql SQL语句
     * @return EXPLAIN结果
     */
    ExplainResult analyzeWithExplain(String sql);

    /**
     * 从SQL中识别可用于切片的日期字段
     * @param sql SQL语句
     * @param params 参数
     * @return 字段名，如：入院日期
     */
    String detectSliceField(String sql, Map<String, Object> params);

    /**
     * 仅分析，不执行
     * @param itemCode 指标项编码
     * @param params 参数
     * @return 分析结果（包含EXPLAIN信息和切片建议）
     */
    Map<String, Object> analyzeOnly(String itemCode, Map<String, Object> params);

    /**
     * 直接执行（不切片）
     * @param itemCode 指标项编码
     * @param params 参数
     * @return 执行结果
     */
    Map<String, Object> executeDirect(String itemCode, Map<String, Object> params);

    /**
     * 切片执行
     * @param itemCode 指标项编码
     * @param params 参数
     * @param sliceConfig 切片配置
     * @return 执行结果
     */
    Map<String, Object> executeWithSlice(String itemCode, Map<String, Object> params, SliceConfig sliceConfig);

    /**
     * 根据itemCode获取指标项
     * @param itemCode 指标项编码
     * @return 指标项
     */
    IndicatorItem getByItemCode(String itemCode);

}
