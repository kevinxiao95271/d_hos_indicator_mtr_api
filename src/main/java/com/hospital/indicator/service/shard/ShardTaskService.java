package com.hospital.indicator.service.shard;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.hospital.indicator.common.BusinessException;
import com.hospital.indicator.common.ErrorCode;
import com.hospital.indicator.entity.shard.ShardTask;
import com.hospital.indicator.entity.shard.ShardTaskSlice;
import com.hospital.indicator.mapper.shard.ShardTaskMapper;
import com.hospital.indicator.mapper.shard.ShardTaskSliceMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 分片任务服务
 *
 * <p>大查询自动分片拆解的调度核心。提交一个大任务 → 拆成若干切片 → 线程池顺序执行 → 每片完成立即回写进度。</p>
 *
 * <p>本框架是包装层:业务侧只需实现 {@link ShardTaskExecutor}(给定参数执行一片),</p>
 * <p>拆片、调度、进度、取消、重试均由本类负责。设计见 docs/大查询自动分片拆解设计.md。</p>
 *
 * @author Claude
 * @date 2026-08-09
 */
@Slf4j
@Service
public class ShardTaskService {

    private final ShardTaskMapper taskMapper;
    private final ShardTaskSliceMapper sliceMapper;

    /** 业务执行器注册表:key=bizType */
    private final Map<String, ShardTaskExecutor> executors = new ConcurrentHashMap<>();

    /** 运行中任务(taskId)集合,用于取消时判断 */
    private final Set<Long> runningTaskIds = ConcurrentHashMap.newKeySet();

    /** 每任务的取消标志:taskId → canceled */
    private final Map<Long, AtomicBoolean> cancelFlags = new ConcurrentHashMap<>();

    private ThreadPoolTaskExecutor pool;
    private long sliceTimeoutSeconds = 30;

    public ShardTaskService(ShardTaskMapper taskMapper, ShardTaskSliceMapper sliceMapper) {
        this.taskMapper = taskMapper;
        this.sliceMapper = sliceMapper;
    }

    @Value("${indicator.shard.slice.timeout-seconds:30}")
    public void setSliceTimeoutSeconds(long seconds) {
        this.sliceTimeoutSeconds = seconds;
    }

    /**
     * 业务执行器接口:业务侧实现"给定参数执行一片"。
     */
    public interface ShardTaskExecutor {
        /**
         * 执行一片。参数即提交时该片的参数(JSON)。
         *
         * @return 本片结果摘要(行数/值),写入 slice.result_summary
         * @throws Exception 执行异常
         */
        String execute(Map<String, Object> params) throws Exception;
    }

    /** 注册业务执行器 */
    public void registerExecutor(String bizType, ShardTaskExecutor executor) {
        executors.put(bizType, executor);
    }

    @PostConstruct
    public void initPool() {
        pool = new ThreadPoolTaskExecutor();
        pool.setThreadNamePrefix("shard-pool-");
        pool.setCorePoolSize(2);
        pool.setMaxPoolSize(4);
        pool.setQueueCapacity(200);
        pool.initialize();
        log.info("ShardTaskService 初始化完成: 线程池 core=2, max=4, queue=200, 单片超时={}s", sliceTimeoutSeconds);
    }

    @PreDestroy
    public void shutdown() {
        if (pool != null) pool.shutdown();
    }

    /**
     * 提交分片任务。返回 taskId,任务异步执行,不阻塞请求线程。
     *
     * @param bizType   业务类型(如 INDICATOR_CALC)
     * @param bizKey    业务标识(如 metricCode=A01&timeDim=MONTH)
     * @param slices    分片参数列表,每个元素对应一个切片
     * @param submitter 提交人
     * @return 任务ID
     */
    @Transactional(rollbackFor = Exception.class)
    public Long submit(String bizType, String bizKey, List<Map<String, Object>> slices, String submitter) {
        return submit(bizType, bizKey, slices, submitter, ShardTask.FAIL_POLICY_STOP);
    }

    /**
     * 提交分片任务(可指定失败策略)。
     *
     * @param failPolicy STOP(任一失败即中止,默认) / CONTINUE(失败后继续下一片)
     */
    @Transactional(rollbackFor = Exception.class)
    public Long submit(String bizType, String bizKey, List<Map<String, Object>> slices,
                       String submitter, String failPolicy) {
        if (executors.get(bizType) == null) {
            throw new BusinessException(ErrorCode.PARAM_INVALID, "未注册的业务类型: " + bizType);
        }
        if (slices == null || slices.isEmpty()) {
            throw new BusinessException(ErrorCode.PARAM_INVALID, "分片列表为空,无法提交");
        }
        if (failPolicy == null || (!ShardTask.FAIL_POLICY_STOP.equals(failPolicy)
                && !ShardTask.FAIL_POLICY_CONTINUE.equals(failPolicy))) {
            throw new BusinessException(ErrorCode.PARAM_INVALID, "非法失败策略: " + failPolicy);
        }

        ShardTask task = new ShardTask();
        task.setBizType(bizType);
        task.setBizKey(bizKey);
        task.setShardStrategy(detectStrategy(slices));
        task.setFailPolicy(failPolicy);
        task.setTotalSlices(slices.size());
        task.setDoneSlices(0);
        task.setStatus(ShardTask.STATUS_PENDING);
        task.setProgressPercent(BigDecimal.ZERO);
        task.setSubmitter(submitter);
        taskMapper.insert(task);

        for (int i = 0; i < slices.size(); i++) {
            ShardTaskSlice slice = new ShardTaskSlice();
            slice.setTaskId(task.getId());
            slice.setSliceNo(i + 1);
            slice.setSliceParams(toJson(slices.get(i)));
            slice.setStatus(ShardTaskSlice.STATUS_PENDING);
            sliceMapper.insert(slice);
        }

        // 关键:异步执行必须等事务提交后再触发,否则异步线程读不到未提交的任务/切片
        // (真实DB事务隔离下 selectById 返回 0)。用 afterCommit 回调。
        final Long taskId = task.getId();
        if (org.springframework.transaction.support.TransactionSynchronizationManager.isSynchronizationActive()) {
            org.springframework.transaction.support.TransactionSynchronizationManager.registerSynchronization(
                    new org.springframework.transaction.support.TransactionSynchronization() {
                        @Override
                        public void afterCommit() {
                            pool.execute(() -> runTask(taskId));
                        }
                    });
        } else {
            pool.execute(() -> runTask(taskId));
        }

        log.info("提交分片任务: taskId={}, bizType={}, totalSlices={}, strategy={}, failPolicy={}",
                taskId, bizType, slices.size(), task.getShardStrategy(), failPolicy);
        return taskId;
    }

    /** 查询任务进度(含分片明细) */
    public ShardTaskDetail getDetail(Long taskId) {
        ShardTask task = taskMapper.selectById(taskId);
        if (task == null) throw new BusinessException(ErrorCode.NOT_FOUND, "分片任务不存在: taskId=" + taskId);

        List<ShardTaskSlice> slices = sliceMapper.selectList(
                new QueryWrapper<ShardTaskSlice>()
                        .eq("task_id", taskId)
                        .orderByAsc("slice_no"));
        return new ShardTaskDetail(task, slices);
    }

    /** 取消任务:未执行片跳过,执行中片由执行器检查取消标志中断 */
    public void cancel(Long taskId) {
        ShardTask task = taskMapper.selectById(taskId);
        if (task == null) throw new BusinessException(ErrorCode.NOT_FOUND, "分片任务不存在: taskId=" + taskId);

        String status = task.getStatus();
        if (!ShardTask.STATUS_PENDING.equals(status) && !ShardTask.STATUS_RUNNING.equals(status)) {
            throw new BusinessException(ErrorCode.TASK_STATUS_CONFLICT, "任务已结束(" + status + "),无法取消");
        }

        // 置取消标志 → 执行中的片会在片边界检测并中断;未执行的片标记 CANCELED
        AtomicBoolean flag = cancelFlags.computeIfAbsent(taskId, k -> new AtomicBoolean(false));
        flag.set(true);

        List<ShardTaskSlice> pending = sliceMapper.selectList(
                new QueryWrapper<ShardTaskSlice>()
                        .eq("task_id", taskId)
                        .eq("status", ShardTaskSlice.STATUS_PENDING));
        pending.forEach(s -> {
            s.setStatus(ShardTaskSlice.STATUS_CANCELED);
            sliceMapper.updateById(s);
        });

        // 任务终态:若有 RUNNING 片,等其结束后统一置 CANCELED;否则立即收尾
        Long running = sliceMapper.selectCount(
                new QueryWrapper<ShardTaskSlice>()
                        .eq("task_id", taskId)
                        .eq("status", ShardTaskSlice.STATUS_RUNNING));
        if (running == null || running == 0) {
            finishTask(taskId, ShardTask.STATUS_CANCELED, null);
        }
        log.info("取消分片任务: taskId={}", taskId);
    }

    /** 重跑失败片:将 FAILED 片重置为 PENDING 重新入队 */
    public void retryFailed(Long taskId) {
        ShardTask task = taskMapper.selectById(taskId);
        if (task == null) throw new BusinessException(ErrorCode.NOT_FOUND, "分片任务不存在: taskId=" + taskId);

        List<ShardTaskSlice> failed = sliceMapper.selectList(
                new QueryWrapper<ShardTaskSlice>()
                        .eq("task_id", taskId)
                        .eq("status", ShardTaskSlice.STATUS_FAILED));
        if (failed.isEmpty()) {
            throw new BusinessException(ErrorCode.TASK_STATUS_CONFLICT, "没有可重试的失败片");
        }

        failed.forEach(s -> {
            s.setStatus(ShardTaskSlice.STATUS_PENDING);
            s.setErrorMsg(null);
            sliceMapper.updateById(s);
        });

        // 重置任务状态,重新入队执行(同样等事务提交后)
        task.setStatus(ShardTask.STATUS_PENDING);
        task.setErrorMsg(null);
        taskMapper.updateById(task);
        final Long id = task.getId();
        if (org.springframework.transaction.support.TransactionSynchronizationManager.isSynchronizationActive()) {
            org.springframework.transaction.support.TransactionSynchronizationManager.registerSynchronization(
                    new org.springframework.transaction.support.TransactionSynchronization() {
                        @Override
                        public void afterCommit() {
                            pool.execute(() -> runTask(id));
                        }
                    });
        } else {
            pool.execute(() -> runTask(id));
        }
        log.info("重试失败片: taskId={}, failedSlices={}", taskId, failed.size());
    }

    // ─── 内部执行 ────────────────────────────────────────────────

    private void runTask(Long taskId) {
        ShardTask task = taskMapper.selectById(taskId);
        if (task == null) return;

        runningTaskIds.add(taskId);
        cancelFlags.remove(taskId); // 干净的开始
        AtomicBoolean canceled = cancelFlags.computeIfAbsent(taskId, k -> new AtomicBoolean(false));

        // 排队 → 执行中
        task.setStatus(ShardTask.STATUS_RUNNING);
        taskMapper.updateById(task);

        List<ShardTaskSlice> slices = sliceMapper.selectList(
                new QueryWrapper<ShardTaskSlice>()
                        .eq("task_id", taskId)
                        .orderByAsc("slice_no"));

        ShardTaskExecutor executor = executors.get(task.getBizType());
        // 失败策略:STOP(任一失败即中止,默认,快速失败)/ CONTINUE(失败后继续下一片)
        boolean stopOnError = !ShardTask.FAIL_POLICY_CONTINUE.equals(task.getFailPolicy());

        int done = 0;
        int failed = 0;
        boolean stoppedOnError = false;
        List<String> errors = new ArrayList<>();
        String terminalStatus = ShardTask.STATUS_SUCCESS;

        for (ShardTaskSlice slice : slices) {
            if (canceled.get()) {
                // 取消:未执行片标 CANCELED(已由 cancel() 处理),直接收尾
                terminalStatus = ShardTask.STATUS_CANCELED;
                break;
            }
            if (!ShardTaskSlice.STATUS_PENDING.equals(slice.getStatus())) {
                if (ShardTaskSlice.STATUS_SUCCESS.equals(slice.getStatus())) done++;
                continue; // 跳过非 PENDING 片(已取消/已失败保留)
            }

            slice.setStatus(ShardTaskSlice.STATUS_RUNNING);
            slice.setStartTime(LocalDateTime.now());
            sliceMapper.updateById(slice);

            try {
                String summary = executeWithTimeout(executor, parseJson(slice.getSliceParams()), sliceTimeoutSeconds);
                slice.setStatus(ShardTaskSlice.STATUS_SUCCESS);
                slice.setResultSummary(summary);
                slice.setEndTime(LocalDateTime.now());
                slice.setErrorMsg(null);
                sliceMapper.updateById(slice);
                done++;
            } catch (Exception e) {
                log.warn("分片执行失败: taskId={}, sliceNo={}, error={}", taskId, slice.getSliceNo(), e.getMessage());
                slice.setStatus(ShardTaskSlice.STATUS_FAILED);
                slice.setErrorMsg(truncate(e.getMessage(), 1000));
                slice.setEndTime(LocalDateTime.now());
                sliceMapper.updateById(slice);
                failed++;
                errors.add("第" + slice.getSliceNo() + "片: " + e.getMessage());

                if (stopOnError) {
                    // STOP 策略:终止任务,剩余 PENDING 片标 CANCELED,任务直接 FAILED(已中止,非部分完成)
                    cancelRemaining(taskId, slices, slice);
                    stoppedOnError = true;
                    break;
                }
            }

            // 每片完成立即回写进度
            updateProgress(taskId, done, failed);
        }

        // 终态判定:
        // - 取消 → CANCELED
        // - STOP 策略中止 → FAILED
        // - 有失败但走完( CONTINUE 策略) → PARTIAL_FAILED
        // - 全部成功 → SUCCESS
        if (canceled.get()) {
            terminalStatus = ShardTask.STATUS_CANCELED;
        } else if (stoppedOnError) {
            terminalStatus = ShardTask.STATUS_FAILED;
        } else {
            terminalStatus = failed > 0 ? ShardTask.STATUS_PARTIAL_FAILED : ShardTask.STATUS_SUCCESS;
        }

        // 最终进度(含失败片)
        int total = task.getTotalSlices() == null ? 0 : task.getTotalSlices();
        Long successCount = sliceMapper.selectCount(
                new QueryWrapper<ShardTaskSlice>()
                        .eq("task_id", taskId)
                        .eq("status", ShardTaskSlice.STATUS_SUCCESS));
        int finalDone = successCount == null ? 0 : successCount.intValue();
        updateProgress(taskId, finalDone, total - finalDone - failed);

        finishTask(taskId, terminalStatus, errors.isEmpty() ? null : String.join("; ", errors).substring(0, Math.min(String.join("; ", errors).length(), 2000)));
        runningTaskIds.remove(taskId);
    }

    /** 单片执行,带超时保护 */
    private String executeWithTimeout(ShardTaskExecutor executor, Map<String, Object> params, long timeoutSeconds)
            throws Exception {
        ExecutorService single = Executors.newSingleThreadExecutor();
        Future<String> future = null;
        try {
            future = single.submit(() -> executor.execute(params));
            return future.get(timeoutSeconds, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            if (future != null) future.cancel(true);
            throw new BusinessException(ErrorCode.SERVER_ERROR, "单片执行超时(" + timeoutSeconds + "s)");
        } finally {
            single.shutdownNow();
        }
    }

    private void cancelRemaining(Long taskId, List<ShardTaskSlice> slices, ShardTaskSlice current) {
        slices.stream()
                .filter(s -> s.getSliceNo() > current.getSliceNo() && ShardTaskSlice.STATUS_PENDING.equals(s.getStatus()))
                .forEach(s -> {
                    s.setStatus(ShardTaskSlice.STATUS_CANCELED);
                    sliceMapper.updateById(s);
                });
    }

    private void updateProgress(Long taskId, int done, int failed) {
        ShardTask task = taskMapper.selectById(taskId);
        if (task == null || task.getTotalSlices() == null || task.getTotalSlices() == 0) return;
        int total = task.getTotalSlices();
        int completed = done + failed;
        BigDecimal percent = BigDecimal.valueOf(completed * 100.0 / total).setScale(2, RoundingMode.HALF_UP);
        task.setDoneSlices(done);
        task.setProgressPercent(percent);
        taskMapper.updateById(task);
    }

    private void finishTask(Long taskId, String status, String errorMsg) {
        ShardTask task = taskMapper.selectById(taskId);
        if (task == null) return;
        task.setStatus(status);
        if (errorMsg != null) task.setErrorMsg(errorMsg);
        task.setUpdateTime(LocalDateTime.now());
        taskMapper.updateById(task);
        log.info("分片任务结束: taskId={}, status={}", taskId, status);
    }

    // ─── 简单工具 ────────────────────────────────────────────────

    /** 根据分片参数推断策略(委托给 SliceGenerator) */
    private String detectStrategy(List<Map<String, Object>> slices) {
        return com.hospital.indicator.util.SliceGenerator.detectStrategy(slices);
    }

    private String toJson(Map<String, Object> map) {
        return com.alibaba.fastjson.JSON.toJSONString(map);
    }

    private Map<String, Object> parseJson(String json) {
        if (json == null || json.trim().isEmpty()) return Collections.emptyMap();
        try {
            return com.alibaba.fastjson.JSON.parseObject(json);
        } catch (Exception e) {
            return Collections.emptyMap();
        }
    }

    private String truncate(String s, int max) {
        if (s == null) return null;
        return s.length() <= max ? s : s.substring(0, max);
    }

    // ─── 进度查询结果对象 ────────────────────────────────────────

    public static class ShardTaskDetail {
        public final ShardTask task;
        public final List<ShardTaskSlice> slices;

        public ShardTaskDetail(ShardTask task, List<ShardTaskSlice> slices) {
            this.task = task;
            this.slices = slices;
        }
    }
}
