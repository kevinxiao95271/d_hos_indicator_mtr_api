package com.hospital.indicator.entity.shard;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 分片任务切片
 *
 * <p>任务的最小执行单元。每个切片独立执行、独立记录状态,执行完立即回写,任务进度随之增长。</p>
 *
 * @author Claude
 * @date 2026-08-09
 */
@Data
@TableName("shard_task_slice")
@Schema(description = "分片任务切片")
public class ShardTaskSlice implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 状态:排队 */
    public static final String STATUS_PENDING = "PENDING";
    /** 状态:执行中 */
    public static final String STATUS_RUNNING = "RUNNING";
    /** 状态:成功 */
    public static final String STATUS_SUCCESS = "SUCCESS";
    /** 状态:失败 */
    public static final String STATUS_FAILED = "FAILED";
    /** 状态:已取消 */
    public static final String STATUS_CANCELED = "CANCELED";

    @Schema(description = "主键ID")
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    @Schema(description = "所属任务ID")
    @TableField("task_id")
    private Long taskId;

    @Schema(description = "片序号,顺序执行/展示用")
    @TableField("slice_no")
    private Integer sliceNo;

    @Schema(description = "本片参数JSON,如 {\"metricCode\":\"A01\",\"start\":\"2026-03-01\",\"end\":\"2026-03-31\"}")
    @TableField("slice_params")
    private String sliceParams;

    @Schema(description = "本片状态:PENDING / RUNNING / SUCCESS / FAILED / CANCELED")
    @TableField("status")
    private String status;

    @Schema(description = "本片结果摘要(行数/值)")
    @TableField("result_summary")
    private String resultSummary;

    @Schema(description = "本片错误信息")
    @TableField("error_msg")
    private String errorMsg;

    @Schema(description = "执行开始时间")
    @TableField("start_time")
    private LocalDateTime startTime;

    @Schema(description = "执行结束时间")
    @TableField("end_time")
    private LocalDateTime endTime;

    @Schema(description = "创建时间")
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
