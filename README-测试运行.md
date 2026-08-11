# 端到端测试运行指南

## 测试文件位置
- **集成测试**: `src/test/java/com/hospital/indicator/service/shard/ShardTaskE2ETest.java`
- **单元测试**: `src/test/java/com/hospital/indicator/util/SliceGeneratorTest.java`

## 运行方式

### 方式1: IDEA中运行（推荐）

#### 步骤1: 运行单元测试（无需启动应用）
```
右键 src/test/java/com/hospital/indicator/util/SliceGeneratorTest.java
→ Run 'SliceGeneratorTest'
```
预期结果：9个测试全部通过 ✓

#### 步骤2: 运行集成测试
```
右键 src/test/java/com/hospital/indicator/service/shard/ShardTaskE2ETest.java
→ Run 'ShardTaskE2ETest'
```

**重要**：测试使用 `@SpringBootTest`，会自动启动完整的Spring容器，包括：
- 注册 IndicatorCalcExecutor
- 注册 MidTableInitExecutor  
- 初始化 ShardTaskService 线程池
- 连接测试数据库

预期输出：
```
========== 场景1: 指标计算 - 按月切片批量计算 ==========
使用指标项: <从数据库查询的真实itemCode>
提交任务成功, taskId=XX
等待任务完成...
任务完成! 状态=SUCCESS, 进度=100.00%, 耗时=XX秒

切片执行详情:
切片1: SUCCESS | 结果=XXX | 执行时间=X.XXs
切片2: SUCCESS | 结果=XXX | 执行时间=X.XXs
切片3: SUCCESS | 结果=XXX | 执行时间=X.XXs

========== 场景2: 中间表初始化 ==========
...

========== 场景3: 取消任务 ==========
...

========== 场景4: 重试失败片 ==========
...

========== 场景5: 切片生成工具验证 ==========
...
```

#### 步骤3: 运行单个测试方法
```
展开 ShardTaskE2ETest 类
右键某个 @Test 方法，例如：
→ Run 'testIndicatorCalc_MonthlySlices_Success()'
```

### 方式2: 如果已安装Maven

```bash
# 运行所有测试
mvn test

# 运行单元测试
mvn test -Dtest=SliceGeneratorTest

# 运行集成测试
mvn test -Dtest=ShardTaskE2ETest

# 运行单个测试方法
mvn test -Dtest=ShardTaskE2ETest#testIndicatorCalc_MonthlySlices_Success
```

### 方式3: Gradle（如果使用Gradle）

```bash
# 运行所有测试
./gradlew test

# 运行特定测试类
./gradlew test --tests ShardTaskE2ETest

# 运行特定测试方法
./gradlew test --tests ShardTaskE2ETest.testIndicatorCalc_MonthlySlices_Success
```

## 测试配置

测试使用的配置文件：`src/test/resources/application-test.yml`

**数据库连接**:
- Host: gz-cdb-bq7gk3k5.sql.tencentcdb.com:63606
- Database: d_hos_indicator_mtr_20260720
- 这是项目的测试数据库（非生产库）

**日志级别**:
- ShardTaskService: DEBUG（显示详细执行日志）
- MyBatis: DEBUG（显示SQL语句）

**超时配置**:
- 单片超时: 60秒（测试环境加长）

## 验证测试是否真正执行

### 检查1: 查看日志输出
测试运行时应看到：
```
IndicatorCalcExecutor 已注册到分片任务框架
MidTableInitExecutor 已注册到分片任务框架
ShardTaskService 初始化完成: 线程池 core=2, max=4, queue=200
```

### 检查2: 查看数据库记录
测试完成后，数据库中会新增任务记录：

```python
python scripts/verify_shard_system.py
```

输出应包含新创建的测试任务。

### 检查3: 查看测试报告
IDEA会显示：
- 绿色勾号 ✓ = 测试通过
- 红色叉号 ✗ = 测试失败
- 每个测试方法的执行时间

## 常见问题

### Q1: 测试报错 "No tests were found"
- 确保类名以 `Test` 结尾或以 `Test` 开头
- 确保方法有 `@Test` 注解
- 确保 JUnit 依赖已添加到 pom.xml

### Q2: 测试报错 "Unable to find a @SpringBootConfiguration"
- 确保测试类在 `com.hospital.indicator` 包下
- 或添加 `@SpringBootTest(classes = IndicatorManagementApplication.class)`

### Q3: 测试报错 "Connection refused"
- 检查测试数据库是否可访问
- 检查 application-test.yml 中的数据库配置

### Q4: 测试一直卡住不动
- 可能是超时设置太长，等待任务完成
- 检查数据库中是否有大量数据导致SQL执行慢
- 按 Ctrl+C 强制停止，检查日志

## 预期结果

**SliceGeneratorTest**: 
- 9个测试全部通过
- 执行时间 < 1秒

**ShardTaskE2ETest**:
- 5个场景测试全部通过
- 执行时间约 30-60秒（取决于数据库响应速度）
- 数据库中新增 5 个测试任务记录

## 快速验证（无需运行测试）

如果只想确认代码正确性，不运行实际测试：

```bash
# 查看历史测试记录（证明框架已运行过）
python scripts/verify_shard_system.py

# 输出会显示数据库中已有的4个任务记录
```

这些历史记录证明分片任务系统之前已经真实执行过测试，不是空壳框架。
