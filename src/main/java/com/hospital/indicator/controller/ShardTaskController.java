package com.hospital.indicator.controller;

import com.hospital.indicator.common.Result;
import com.hospital.indicator.context.UserContext;
import com.hospital.indicator.entity.shard.ShardTask;
import com.hospital.indicator.service.shard.ShardTaskService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 分片任务接口
 *
 * <p>大查询自动分片拆解的对外入口:提交任务(异步执行)、查询进度、取消、重试失败片。</p>
 *
 * @author Claude
 * @date 2026-08-09
 */
@Tag(name = "分片任务", description = "大查询自动分片拆解:提交任务、查询进度、取消、重试失败片")
@RestController
@RequestMapping("/api/shard-task")
public class ShardTaskController {

    @Autowired
    private ShardTaskService shardTaskService;

    @Operation(summary = "提交分片任务(异步执行,立即返回 taskId)")
    @PostMapping
    public Result<Long> submit(@RequestBody SubmitRequest request) {
        String operator = getOperator();
        Long taskId = shardTaskService.submit(request.getBizType(), request.getBizKey(), request.getSlices(), operator);
        return Result.success("任务已提交,开始异步执行", taskId);
    }

    @Operation(summary = "查询任务进度(含分片明细)")
    @GetMapping("/{taskId}")
    public Result<ShardTaskService.ShardTaskDetail> getDetail(@PathVariable Long taskId) {
        return Result.success(shardTaskService.getDetail(taskId));
    }

    @Operation(summary = "取消任务(未执行片跳过,执行中片在片边界中断)")
    @PostMapping("/{taskId}/cancel")
    public Result<Void> cancel(@PathVariable Long taskId) {
        shardTaskService.cancel(taskId);
        return Result.success();
    }

    @Operation(summary = "重试失败片(仅 FAILED 片重新入队)")
    @PostMapping("/{taskId}/retry-failed")
    public Result<Void> retryFailed(@PathVariable Long taskId) {
        shardTaskService.retryFailed(taskId);
        return Result.success();
    }

    private String getOperator() {
        try {
            UserContext ctx = UserContext.get();
            return ctx != null && ctx.getUsername() != null ? ctx.getUsername() : "anonymous";
        } catch (Exception e) {
            return "anonymous";
        }
    }

    public static class SubmitRequest {
        private String bizType;
        private String bizKey;
        private List<Map<String, Object>> slices;

        public String getBizType() { return bizType; }
        public void setBizType(String bizType) { this.bizType = bizType; }
        public String getBizKey() { return bizKey; }
        public void setBizKey(String bizKey) { this.bizKey = bizKey; }
        public List<Map<String, Object>> getSlices() { return slices; }
        public void setSlices(List<Map<String, Object>> slices) { this.slices = slices; }
    }
}
