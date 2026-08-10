package com.hospital.indicator.service.shard;

import com.hospital.indicator.common.BusinessException;
import com.hospital.indicator.entity.shard.ShardTask;
import com.hospital.indicator.entity.shard.ShardTaskSlice;
import com.hospital.indicator.mapper.shard.ShardTaskMapper;
import com.hospital.indicator.mapper.shard.ShardTaskSliceMapper;
import com.hospital.indicator.service.shard.ShardTaskService.ShardTaskExecutor;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * 分片任务服务单元测试
 *
 * <p>纯单测(不连数据库):mock Mapper,验证状态流转、进度、取消、失败重试、超时。</p>
 *
 * @author Claude
 * @date 2026-08-09
 */
class ShardTaskServiceTest {

    private ShardTaskMapper taskMapper;
    private ShardTaskSliceMapper sliceMapper;
    private ShardTaskService service;

    /** 内存数据库替身:模拟 MyBatis Plus 的 selectById / insert / update 行为 */
    private final Map<Long, ShardTask> taskStore = new LinkedHashMap<>();
    private final Map<Long, List<ShardTaskSlice>> sliceStore = new LinkedHashMap<>();
    private long nextTaskId = 1;
    private long nextSliceId = 1;

    /** Java 8 兼容的 Map 构造 */
    private static Map<String, Object> maps(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    /** 深拷贝,模拟真实 DB 的快照隔离:selectById 返回独立副本,避免别名污染 */
    private static ShardTask deepCopy(ShardTask t) {
        if (t == null) return null;
        ShardTask c = new ShardTask();
        c.setId(t.getId());
        c.setBizType(t.getBizType());
        c.setBizKey(t.getBizKey());
        c.setShardStrategy(t.getShardStrategy());
        c.setTotalSlices(t.getTotalSlices());
        c.setDoneSlices(t.getDoneSlices());
        c.setStatus(t.getStatus());
        c.setProgressPercent(t.getProgressPercent());
        c.setFailPolicy(t.getFailPolicy());
        c.setSubmitter(t.getSubmitter());
        c.setErrorMsg(t.getErrorMsg());
        c.setCreateTime(t.getCreateTime());
        c.setUpdateTime(t.getUpdateTime());
        return c;
    }

    private static ShardTaskSlice deepCopy(ShardTaskSlice s) {
        if (s == null) return null;
        ShardTaskSlice c = new ShardTaskSlice();
        c.setId(s.getId());
        c.setTaskId(s.getTaskId());
        c.setSliceNo(s.getSliceNo());
        c.setSliceParams(s.getSliceParams());
        c.setStatus(s.getStatus());
        c.setResultSummary(s.getResultSummary());
        c.setErrorMsg(s.getErrorMsg());
        c.setStartTime(s.getStartTime());
        c.setEndTime(s.getEndTime());
        c.setCreateTime(s.getCreateTime());
        return c;
    }

    @BeforeEach
    void setUp() {
        taskMapper = mock(ShardTaskMapper.class);
        sliceMapper = mock(ShardTaskSliceMapper.class);

        // ── taskMapper 行为 ──
        when(taskMapper.insert(any(ShardTask.class))).thenAnswer(inv -> {
            ShardTask t = inv.getArgument(0);
            t.setId(nextTaskId++);
            taskStore.put(t.getId(), t);
            return 1;
        });
        // 关键:selectById 返回深拷贝,避免外部引用直接改到 store 里的对象,导致任务状态被污染(永远 RUNNING)
        when(taskMapper.selectById(any(Long.class))).thenAnswer(inv -> {
            ShardTask t = taskStore.get(inv.getArgument(0));
            return t == null ? null : deepCopy(t);
        });
        when(taskMapper.updateById(any(ShardTask.class))).thenAnswer(inv -> {
            ShardTask t = deepCopy(inv.getArgument(0, ShardTask.class));
            taskStore.put(t.getId(), t);
            return 1;
        });
        when(taskMapper.update(any(), any())).thenAnswer(inv -> {
            // 模拟 MyBatis Plus 的 update(entity, wrapper):按 wrapper 条件更新 store
            Object wrapper = inv.getArgument(1);
            try {
                if (wrapper instanceof com.baomidou.mybatisplus.core.conditions.Wrapper) {
                    java.lang.reflect.Method m = com.baomidou.mybatisplus.core.conditions.AbstractWrapper.class
                            .getDeclaredMethod("getParamNameValuePairs");
                    m.setAccessible(true);
                    @SuppressWarnings("unchecked")
                    Map<String, Object> pairs = (Map<String, Object>) m.invoke(wrapper);
                    Object idVal = pairs.get("id");
                    ShardTask stored = taskStore.get(idVal);
                    if (stored == null) return 0;
                    if (pairs.containsKey("status")) stored.setStatus((String) pairs.get("status"));
                    if (pairs.containsKey("error_msg")) stored.setErrorMsg((String) pairs.get("error_msg"));
                    return 1;
                }
            } catch (Exception ignore) {
                // 反射失败则不更新,测试主要依赖 updateById 路径
            }
            return 0;
        });

        // ── sliceMapper 行为 ──
        when(sliceMapper.insert(any(ShardTaskSlice.class))).thenAnswer(inv -> {
            ShardTaskSlice s = inv.getArgument(0);
            s.setId(nextSliceId++);
            sliceStore.computeIfAbsent(s.getTaskId(), k -> new ArrayList<>()).add(s);
            return 1;
        });
        when(sliceMapper.selectById(any(Long.class))).thenAnswer(inv ->
                sliceStore.values().stream().flatMap(List::stream)
                        .filter(s -> s.getId().equals(inv.getArgument(0))).findFirst()
                        .map(ShardTaskServiceTest::deepCopy).orElse(null));
        when(sliceMapper.updateById(any(ShardTaskSlice.class))).thenAnswer(inv -> {
            ShardTaskSlice s = deepCopy(inv.getArgument(0, ShardTaskSlice.class));
            sliceStore.computeIfAbsent(s.getTaskId(), k -> new ArrayList<>()).stream()
                    .filter(x -> x.getId().equals(s.getId())).findFirst().ifPresent(x -> {
                        x.setStatus(s.getStatus());
                        x.setResultSummary(s.getResultSummary());
                        x.setErrorMsg(s.getErrorMsg());
                        x.setStartTime(s.getStartTime());
                        x.setEndTime(s.getEndTime());
                    });
            return 1;
        });
        when(sliceMapper.selectList(any())).thenAnswer(inv -> {
            // 简化:返回 store 中全部切片的深拷贝(测试串行单任务,只有一个 taskId)
            List<ShardTaskSlice> all = sliceStore.values().stream().flatMap(List::stream)
                    .map(ShardTaskServiceTest::deepCopy).collect(Collectors.toList());
            all.sort(Comparator.comparing(ShardTaskSlice::getSliceNo));
            return new ArrayList<>(all);
        });
        when(sliceMapper.selectCount(any())).thenAnswer(inv ->
                sliceStore.values().stream().flatMap(List::stream)
                        .filter(s -> ShardTaskSlice.STATUS_SUCCESS.equals(s.getStatus()))
                        .count());

        service = new ShardTaskService(taskMapper, sliceMapper);
        service.setSliceTimeoutSeconds(10);
        service.initPool();
    }

    @AfterEach
    void tearDown() {
        service.shutdown();
    }

    private void waitForTerminal(Long taskId) throws InterruptedException {
        long deadline = System.currentTimeMillis() + 5000;
        while (System.currentTimeMillis() < deadline) {
            ShardTask t = taskStore.get(taskId);
            if (t != null && !ShardTask.STATUS_RUNNING.equals(t.getStatus())
                    && !ShardTask.STATUS_PENDING.equals(t.getStatus())) return;
            Thread.sleep(20);
        }
        fail("任务未在超时时间内到达终态, taskId=" + taskId);
    }

    @Test
    void shouldRejectUnregisteredBizType() {
        List<Map<String, Object>> slices = Arrays.asList(maps("start", "2026-01-01"));
        assertThrows(BusinessException.class,
                () -> service.submit("UNKNOWN_BIZ", "k", slices, "tester"));
    }

    @Test
    void shouldRejectEmptySlices() {
        service.registerExecutor("T", p -> "ok");
        assertThrows(BusinessException.class,
                () -> service.submit("T", "k", Collections.emptyList(), "tester"));
    }

    @Test
    void shouldSubmitAndExecuteAllSlicesSuccess() throws InterruptedException {
        AtomicInteger executed = new AtomicInteger();
        service.registerExecutor("T", p -> {
            executed.incrementAndGet();
            return "row=1";
        });

        Long taskId = service.submit("T", "metricCode=A01", Arrays.asList(
                maps("start", "2026-01"), maps("start", "2026-02"), maps("start", "2026-03")
        ), "tester");

        waitForTerminal(taskId);
        ShardTask task = taskStore.get(taskId);
        assertEquals(ShardTask.STATUS_SUCCESS, task.getStatus());
        assertEquals(3, executed.get());
        assertEquals(3, task.getDoneSlices());
        assertEquals(100.0, task.getProgressPercent().doubleValue(), 0.01);
        // 所有片 SUCCESS
        assertTrue(sliceStore.get(taskId).stream().allMatch(s -> ShardTaskSlice.STATUS_SUCCESS.equals(s.getStatus())));
    }

    @Test
    void shouldMarkPartialFailedAndRetryFailedSlices() throws InterruptedException {
        AtomicInteger failCount = new AtomicInteger(0);
        service.registerExecutor("T", p -> {
            // 第2片(2026-02)失败
            if ("2026-02".equals(p.get("start"))) {
                if (failCount.getAndIncrement() == 0) throw new BusinessException("第2片模拟失败");
            }
            return "ok";
        });

        // CONTINUE 策略:第2片失败后继续第3片,最终 PARTIAL_FAILED
        Long taskId = service.submit("T", "k", Arrays.asList(
                maps("start", "2026-01"), maps("start", "2026-02"), maps("start", "2026-03")
        ), "tester", ShardTask.FAIL_POLICY_CONTINUE);

        waitForTerminal(taskId);
        ShardTask task = taskStore.get(taskId);
        assertEquals(ShardTask.STATUS_PARTIAL_FAILED, task.getStatus());
        assertEquals(2, task.getDoneSlices());
        // 第2片 FAILED,第1/3 SUCCESS
        assertEquals(ShardTaskSlice.STATUS_FAILED,
                sliceStore.get(taskId).get(1).getStatus());

        // 重试失败片
        service.retryFailed(taskId);
        waitForTerminal(taskId);
        ShardTask retried = taskStore.get(taskId);
        assertEquals(ShardTask.STATUS_SUCCESS, retried.getStatus());
        assertTrue(sliceStore.get(taskId).stream().allMatch(s -> ShardTaskSlice.STATUS_SUCCESS.equals(s.getStatus())));
    }

    @Test
    void shouldCancelPendingTask() throws InterruptedException {
        service.registerExecutor("T", p -> {
            // 每片执行 200ms,保证取消发生在执行中
            try { Thread.sleep(200); } catch (InterruptedException e) { throw new RuntimeException(e); }
            return "ok";
        });

        Long taskId = service.submit("T", "k", Arrays.asList(
                maps("start", "2026-01"), maps("start", "2026-02"), maps("start", "2026-03")
        ), "tester");

        // 等第一片开始执行后再取消
        Thread.sleep(300);
        service.cancel(taskId);
        waitForTerminal(taskId);

        ShardTask task = taskStore.get(taskId);
        assertEquals(ShardTask.STATUS_CANCELED, task.getStatus());
        // 所有片都不处于 RUNNING(要么 SUCCESS 要么 CANCELED)
        assertTrue(sliceStore.get(taskId).stream().noneMatch(s -> ShardTaskSlice.STATUS_RUNNING.equals(s.getStatus())));
    }

    @Test
    void shouldFailOnTimeout() throws InterruptedException {
        service.registerExecutor("T", p -> {
            // 单片 sleep 2s,超过 1s 超时阈值 → 必超时
            try { Thread.sleep(2000); } catch (InterruptedException e) { throw new RuntimeException(e); }
            return "slow";
        });
        service.setSliceTimeoutSeconds(1); // 1秒超时

        Long taskId = service.submit("T", "k", Arrays.asList(maps("start", "2026-01")), "tester");
        waitForTerminal(taskId);

        ShardTask task = taskStore.get(taskId);
        assertEquals(ShardTask.STATUS_FAILED, task.getStatus());
        assertEquals(ShardTaskSlice.STATUS_FAILED, sliceStore.get(taskId).get(0).getStatus());
        assertNotNull(sliceStore.get(taskId).get(0).getErrorMsg());
        assertTrue(sliceStore.get(taskId).get(0).getErrorMsg().contains("超时"));
    }

    @Test
    void shouldCancelStoppedOnFirstFailure() throws InterruptedException {
        AtomicInteger executed = new AtomicInteger();
        service.registerExecutor("T", p -> {
            executed.incrementAndGet();
            if ("2026-01".equals(p.get("start"))) throw new BusinessException("第一片失败");
            return "ok";
        });

        Long taskId = service.submit("T", "k", Arrays.asList(
                maps("start", "2026-01"), maps("start", "2026-02"), maps("start", "2026-03")
        ), "tester");

        waitForTerminal(taskId);
        ShardTask task = taskStore.get(taskId);
        // STOP 策略:第一片失败 → 任务 FAILED,剩余片 CANCELED
        assertEquals(ShardTask.STATUS_FAILED, task.getStatus());
        assertEquals(1, executed.get());
        assertEquals(ShardTaskSlice.STATUS_CANCELED, sliceStore.get(taskId).get(1).getStatus());
        assertEquals(ShardTaskSlice.STATUS_CANCELED, sliceStore.get(taskId).get(2).getStatus());
    }
}
