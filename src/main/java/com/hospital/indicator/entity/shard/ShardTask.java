package com.hospital.indicator.entity.shard;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 分片任务
 *
 * <p>一次"大查询/批量计算"提交对应一条任务。任务被拆成若干分片(shard_task_slice)执行,
 * 本表记录任务整体状态与进度,供前端轮询展示。</p>
 *
 * @author Claude
 * @date 2026-08-09
 */
@Data
@TableName("shard_task")
@Schema(description = "分片任务")
public class ShardTask implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 业务类型:指标计算 */
    public static final String BIZ_INDICATOR_CALC = "INDICATOR_CALC";
    /** 业务类型:中间表初始化 */
    public static final String BIZ_MID_TABLE_INIT = "MID_TABLE_INIT";
    /** 业务类型:中间表列规则 */
    public static final String BIZ_MID_TABLE_COL_RULE = "MID_TABLE_COL_RULE";
    /** 业务类型:专病入组 */
    public static final String BIZ_SPECIAL_DISEASE_ENROLL = "SPECIAL_DISEASE_ENROLL";
    /** 业务类型:追溯查询 */
    public static final String BIZ_TRACE_QUERY = "TRACE_QUERY";

    /** 拆片策略:时间片 */
    public static final String STRATEGY_TIME_SLICE = "TIME_SLICE";
    /** 拆片策略:键值片(编码/科室列表) */
    public static final String STRATEGY_KEY_SLICE = "KEY_SLICE";
    /** 拆片策略:行数片(UPDATE/INSERT 兜底) */
    public static final String STRATEGY_ROW_SLICE = "ROW_SLICE";
    /** 拆片策略:单条不改(存储过程/GROUP BY 聚合等) */
    public static final String STRATEGY_NO_SHARD = "NO_SHARD";

    /** 状态:排队 */
    public static final String STATUS_PENDING = "PENDING";
    /** 状态:执行中 */
    public static final String STATUS_RUNNING = "RUNNING";
    /** 状态:成功 */
    public static final String STATUS_SUCCESS = "SUCCESS";
    /** 状态:部分失败 */
    public static final String STATUS_PARTIAL_FAILED = "PARTIAL_FAILED";
    /** 状态:失败 */
    public static final String STATUS_FAILED = "FAILED";
    /** 状态:已取消 */
    public static final String STATUS_CANCELED = "CANCELED";

    /** 失败策略:STOP(默认,任一失败即中止) */
    public static final String FAIL_POLICY_STOP = "STOP";
    /** 失败策略:CONTINUE(失败后继续下一片) */
    public static final String FAIL_POLICY_CONTINUE = "CONTINUE";

    @Schema(description = "主键ID")
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    @Schema(description = "业务类型:INDICATOR_CALC / MID_TABLE_INIT / MID_TABLE_COL_RULE / SPECIAL_DISEASE_ENROLL / TRACE_QUERY")
    @TableField("biz_type")
    private String bizType;

    @Schema(description = "业务标识,如 metricCode=A01&timeDim=MONTH&start=2026-01&end=2026-06")
    @TableField("biz_key")
    private String bizKey;

    @Schema(description = "实际使用的拆片策略:TIME_SLICE / KEY_SLICE / ROW_SLICE / NO_SHARD")
    @TableField("shard_strategy")
    private String shardStrategy;

    @Schema(description = "总分片数")
    @TableField("total_slices")
    private Integer totalSlices;

    @Schema(description = "已完成分片数")
    @TableField("done_slices")
    private Integer doneSlices;

    @Schema(description = "任务状态:PENDING / RUNNING / SUCCESS / PARTIAL_FAILED / FAILED / CANCELED")
    @TableField("status")
    private String status;

    @Schema(description = "进度百分比(0~100)")
    @TableField("progress_percent")
    private BigDecimal progressPercent;

    @Schema(description = "失败策略:STOP(默认,任一失败即中止) / CONTINUE(失败后继续下一片)")
    @TableField("fail_policy")
    private String failPolicy;

    @Schema(description = "提交人")
    @TableField("submitter")
    private String submitter;

    @Schema(description = "失败汇总信息")
    @TableField("error_msg")
    private String errorMsg;

    @Schema(description = "创建时间")
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @Schema(description = "更新时间")
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
