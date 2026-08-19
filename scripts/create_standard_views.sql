-- =====================================================
-- 医院等级评审系统 - 标准接口视图创建脚本
-- 基于：评审系统接口规范_标准版V2.5
-- 目标库：d_hos_indicator_mtr_20260720
-- 创建时间：2026-08-13
-- =====================================================

USE d_hos_indicator_mtr_20260720;

-- =====================================================
-- 2.2.1 病案首页基本信息（QM_I_INPATIENT_INFO）
-- 数据源：d_mr 表
-- =====================================================
CREATE OR REPLACE VIEW QM_I_INPATIENT_INFO AS
SELECT
    -- 核心标识
    A48 AS PATIENTID,              -- 住院号
    A49 AS VISITNO,                -- 住院次数/就诊编号
    A01 AS P3,                     -- 病案号

    -- 患者基本信息
    A02 AS P4,                     -- 姓名 (PATIENTNAME)
    A14 AS P5,                     -- 性别 (1男/2女)
    A11 AS P6,                     -- 出生日期
    A13 AS P7,                     -- 年龄（岁）
    A12C AS ZY,                    -- 职业
    A20 AS P13,                    -- 证件号码
    A22 AS LXDH,                   -- 联系电话
    A24 AS XZZ,                    -- 现住址

    -- 就诊信息
    A15C AS P1,                    -- 医疗付款方式
    A38C AS P804,                  -- 入院途径
    B12 AS P22,                    -- 入院时间 (INDATE)
    B13C AS P23,                   -- 入院科室名称 (INDEPTNAME)
    B14 AS P231,                   -- 入院病区名称
    B15 AS P25,                    -- 出院时间 (OUTDATE)
    B16C AS P26,                   -- 出院科室名称 (OUTDEPTNAME)
    B16 AS P261,                   -- 出院病区名称
    B20 AS P27,                    -- 实际住院天数

    -- 诊断信息
    C01C AS P28,                   -- 门（急）诊诊断编码
    C02N AS P281,                  -- 门（急）诊诊断描述
    B21C AS INDIAGNOSE,            -- 入院诊断

    -- 医护人员
    B22C AS P431,                  -- 科主任姓名
    B23C AS P432,                  -- 主任（副主任）医师
    B24C AS P433,                  -- 主治医师姓名
    B25C AS P434,                  -- 住院医师姓名 (DOCTNAME)
    B26C AS INDOCTNAME,            -- 收治入院医生姓名
    B27 AS P45,                    -- 质控医师姓名
    B28 AS P46,                    -- 质控护师姓名

    -- 费用信息
    D01 AS P782,                   -- 住院总费用
    D09 AS P751,                   -- 住院总费用其中自付金额
    D11 AS P752,                   -- 一般医疗服务费
    D12 AS P754,                   -- 一般治疗操作费
    D13 AS P755,                   -- 护理费
    D14 AS P756,                   -- 综合医疗服务类其他费用
    D15 AS P757,                   -- 病理诊断费
    D16 AS P758,                   -- 实验室诊断费
    D17 AS P759,                   -- 影像学诊断费
    D18 AS P760,                   -- 临床诊断项目费
    D19 AS P761,                   -- 非手术治疗项目费
    D20 AS P762,                   -- 临床物理治疗费
    D21 AS P763,                   -- 手术治疗费
    D22 AS P764,                   -- 麻醉费
    D23 AS P765,                   -- 手术费
    D24 AS P767,                   -- 康复费
    D25 AS P768,                   -- 中医治疗费
    D26 AS P769,                   -- 西药费
    D27 AS P770,                   -- 抗菌药物费用
    D28 AS P771,                   -- 中成药费
    D29 AS P772,                   -- 中草药费
    D30 AS P773,                   -- 血费
    D31 AS P774,                   -- 白蛋白类制品费
    D32 AS P775,                   -- 球蛋白类制品费
    D33 AS P776,                   -- 凝血因子类制品费
    D34 AS P777,                   -- 细胞因子类制品费

    -- 其他字段
    B30C AS P741,                  -- 离院方式
    B31 AS P743,                   -- 转院机构名称
    B34C AS P44,                   -- 病案质量
    A17 AS P66,                    -- 年龄（不足1周岁的，单位：天）
    A16 AS P681,                   -- 新生儿出生体重1
    A18x01 AS P682,                -- 新生儿出生体重2
    A18x02 AS P683,                -- 新生儿出生体重3
    A18x03 AS P684,                -- 新生儿出生体重4
    A18x04 AS P685,                -- 新生儿出生体重5

    -- 符合情况
    C24C AS P414,                  -- 手术冰冻与石蜡诊断符合
    C25 AS P413,                   -- 恶性肿瘤术前诊断与术后病理诊断符合情况

    -- 患者基本信息（用于关联）
    A02 AS PATIENTNAME,            -- 患者姓名
    A19C AS PATIENTTYPE,           -- 患者费别名称
    A21C AS SEX,                   -- 性别
    A13 AS AGE,                    -- 年龄
    A20N AS PATIENTJOB,            -- 病人职别
    A23C AS PATIENTSOURCE,         -- 入院途径
    A22 AS IDCARD,                 -- 证件号码
    A24 AS ADDR,                   -- 地址
    A22 AS PHONE,                  -- 联系电话

    -- 科室名称
    B13C AS INDEPTNAME,            -- 入院科室名称
    B16C AS OUTDEPTNAME,           -- 出院科室名称

    -- 时间戳
    create_time,
    update_time
FROM d_mr
WHERE del_flag = '0';

-- =====================================================
-- 2.2.2 患者诊断信息（QM_I_INPATIENT_OTHERDIAG）
-- 数据源：d_mr_other_1_20 表（假设存在诊断明细表）
-- 注：如果诊断存储在 d_mr 的 C06x01C~C06x40C 字段中，需要 UNION ALL 展开
-- =====================================================
CREATE OR REPLACE VIEW QM_I_INPATIENT_OTHERDIAG AS
SELECT
    A48 AS PATIENTID,              -- 住院号
    A49 AS VISITNO,                -- 就诊标识
    C06x01C AS P324,               -- 诊断编码
    C07x01N AS P325,               -- 诊断疾病描述
    C08x01C AS P806,               -- 入院病情
    1 AS SORT,                     -- 诊断顺序
    C06x01C AS ZZBM,               -- 医生提交时填写的诊断编码
    C07x01N AS ZZMC                -- 医生提交时填写的诊断名称
FROM d_mr WHERE C06x01C IS NOT NULL AND C06x01C != ''
UNION ALL
SELECT A48, A49, C06x02C, C07x02N, C08x02C, 2, C06x02C, C07x02N FROM d_mr WHERE C06x02C IS NOT NULL AND C06x02C != ''
UNION ALL
SELECT A48, A49, C06x03C, C07x03N, C08x03C, 3, C06x03C, C07x03N FROM d_mr WHERE C06x03C IS NOT NULL AND C06x03C != ''
UNION ALL
SELECT A48, A49, C06x04C, C07x04N, C08x04C, 4, C06x04C, C07x04N FROM d_mr WHERE C06x04C IS NOT NULL AND C06x04C != ''
UNION ALL
SELECT A48, A49, C06x05C, C07x05N, C08x05C, 5, C06x05C, C07x05N FROM d_mr WHERE C06x05C IS NOT NULL AND C06x05C != ''
UNION ALL
SELECT A48, A49, C06x06C, C07x06N, C08x06C, 6, C06x06C, C07x06N FROM d_mr WHERE C06x06C IS NOT NULL AND C06x06C != ''
UNION ALL
SELECT A48, A49, C06x07C, C07x07N, C08x07C, 7, C06x07C, C07x07N FROM d_mr WHERE C06x07C IS NOT NULL AND C06x07C != ''
UNION ALL
SELECT A48, A49, C06x08C, C07x08N, C08x08C, 8, C06x08C, C07x08N FROM d_mr WHERE C06x08C IS NOT NULL AND C06x08C != ''
UNION ALL
SELECT A48, A49, C06x09C, C07x09N, C08x09C, 9, C06x09C, C07x09N FROM d_mr WHERE C06x09C IS NOT NULL AND C06x09C != ''
UNION ALL
SELECT A48, A49, C06x10C, C07x10N, C08x10C, 10, C06x10C, C07x10N FROM d_mr WHERE C06x10C IS NOT NULL AND C06x10C != '';

-- =====================================================
-- 2.2.3 手术及操作信息（QM_I_INPATIENT_OPERATION）
-- 数据源：d_mr 表的 C14x01C~手术相关字段
-- =====================================================
CREATE OR REPLACE VIEW QM_I_INPATIENT_OPERATION AS
SELECT
    A48 AS PATIENTID,              -- 住院号
    A49 AS VISITNO,                -- 就诊编号
    C14x01C AS P490,               -- 手术操作编码
    C15x01N AS P492,               -- 手术操作名称
    C16x01 AS P491,                -- 手术操作时间
    C21x01C AS P820,               -- 手术级别
    C16x01 AS P493,                -- 手术操作部位
    C18x01 AS P494,                -- 手术持续时间
    C22x01C AS P495,               -- 术者
    C22x01C AS SZGH,               -- 术者工号
    C23x01 AS SZSZKS,              -- 术者所在科室
    C19x01 AS P496,                -- Ⅰ助
    C19x01 AS YZGH,                -- Ⅰ助工号
    C20x01 AS P497,                -- Ⅱ助
    C17x01 AS P498,                -- 麻醉方式
    C17x01 AS P4981,               -- 麻醉分级
    C21x01C AS P499,               -- 切口愈合等级
    C23x01 AS P4910,               -- 麻醉医师
    1 AS SORT,                     -- 手术顺序
    C15x01N AS SSMC,               -- 医生填写的手术名称
    C14x01C AS SSBM                -- 医生填写的手术编码
FROM d_mr
WHERE C14x01C IS NOT NULL AND C14x01C != '';

-- =====================================================
-- 2.1.4 住院患者就诊信息（QM_I_HIS_INPATIENT_INFO）
-- 数据源：d_mr 表
-- =====================================================
CREATE OR REPLACE VIEW QM_I_HIS_INPATIENT_INFO AS
SELECT
    A48 AS PATIENTID,              -- 住院号
    A49 AS VISITNO,                -- 住院次数
    A01 AS P3,                     -- 病案号
    A02 AS PATIENTNAME,            -- 患者姓名
    A19C AS PATIENTTYPE,           -- 患者费别名称
    A13 AS AGE,                    -- 年龄
    A14 AS SEX,                    -- 性别
    B13C AS INDEPTNAME,            -- 入院科室名称
    B12 AS INDATE,                 -- 入院时间
    B16C AS OUTDEPTNAME,           -- 出院科室名称
    B15 AS OUTDATE,                -- 出院时间
    B26C AS INDOCTNAME,            -- 收治入院医生姓名
    B25C AS DOCTNAME,              -- 住院医师姓名
    B21C AS INDIAGNOSE,            -- 入院诊断
    A20N AS PATIENTJOB,            -- 病人职别
    A23C AS PATIENTSOURCE,         -- 入院途径
    A20 AS IDCARD,                 -- 证件号码
    A24 AS ADDR,                   -- 地址
    A22 AS PHONE                   -- 联系电话
FROM d_mr
WHERE del_flag = '0';

-- =====================================================
-- 占位视图 - 其他系统数据（当前测试库无数据源）
-- =====================================================

-- 2.1.1 门诊患者就诊信息
CREATE OR REPLACE VIEW QM_I_HIS_OUTPATIENT_INFO AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS RQ,
    NULL AS DEPTNAME,
    NULL AS DOCTNAME,
    NULL AS VISITTYPE,
    NULL AS PATIENTNAME,
    NULL AS PATIENTTYPE,
    NULL AS AGE,
    NULL AS SEX,
    NULL AS ADDRESS,
    NULL AS THBZ,
    NULL AS IDCARD,
    NULL AS PHONE
FROM DUAL WHERE 1=0;

-- 2.1.2 门诊患者处方信息
CREATE OR REPLACE VIEW QM_I_HIS_OUTPATIENT_PRESC AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS RQ,
    NULL AS DEPTNAME,
    NULL AS DRUGNAME,
    NULL AS AMOUNT,
    NULL AS COSTS
FROM DUAL WHERE 1=0;

-- 2.1.3 门诊患者费用信息
CREATE OR REPLACE VIEW QM_I_HIS_OUTPATIENT_COST AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS CHARGEDATE,
    NULL AS ITEMNAME,
    NULL AS ITEMCOST
FROM DUAL WHERE 1=0;

-- 2.1.5 住院患者费用明细
CREATE OR REPLACE VIEW QM_I_HIS_INPATIENT_COST AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS PATIENTDEPTNAME,
    NULL AS CHARGEDATE,
    NULL AS ITEMCODE,
    NULL AS ITEMNAME,
    NULL AS ITEMAMOUNT,
    NULL AS ITEMPRICE,
    NULL AS ITEMCOST
FROM DUAL WHERE 1=0;

-- 2.1.6 住院患者医嘱信息
CREATE OR REPLACE VIEW QM_I_HIS_INPATIENT_ADVICE AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS PATIENTDEPTNAME,
    NULL AS ADVICEID,
    NULL AS ADVICENAME,
    NULL AS STARTTIME,
    NULL AS STOPTIME
FROM DUAL WHERE 1=0;

-- 2.1.7 住院患者转科信息
CREATE OR REPLACE VIEW QM_I_INPATIENT_CHANGEDEPT AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS SOURCEDEPTNAME,
    NULL AS CHANGEDATE,
    NULL AS TARGETDEPTNAME,
    NULL AS INDATE
FROM DUAL WHERE 1=0;

-- 2.1.8 护士排班信息
CREATE OR REPLACE VIEW QM_I_HIS_HSPBXX AS
SELECT
    NULL AS RQ,
    NULL AS KS,
    NULL AS USERID,
    NULL AS USERNAME,
    NULL AS BC,
    NULL AS SC,
    NULL AS NX
FROM DUAL WHERE 1=0;

-- 2.1.9 HIS 人员信息
CREATE OR REPLACE VIEW QM_I_HIS_EMPOLYEE AS
SELECT
    NULL AS KSBH,
    NULL AS KSMC,
    NULL AS GH,
    NULL AS YGXM,
    NULL AS ZT,
    NULL AS XB,
    NULL AS YGLB,
    NULL AS YGZC,
    NULL AS KSPOWER
FROM DUAL WHERE 1=0;

-- 2.3.1 患者手麻信息
CREATE OR REPLACE VIEW QM_I_OP_INPATIENT_OPERATION AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS PATIENTNAME,
    NULL AS P5812,
    NULL AS P581,
    NULL AS P820,
    NULL AS P491
FROM DUAL WHERE 1=0;

-- 2.4.1 电子病历填写记录
CREATE OR REPLACE VIEW QM_I_EMR_PGXX AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS PGBTYPE,
    NULL AS KEY,
    NULL AS VALUE,
    NULL AS PGRQ
FROM DUAL WHERE 1=0;

-- 2.5.1 检验结果信息
CREATE OR REPLACE VIEW QM_I_LIS_BiaoBen AS
SELECT
    NULL AS HZLY,
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS SQSJ,
    NULL AS SDDH,
    NULL AS CJSJ,
    NULL AS JCXM
FROM DUAL WHERE 1=0;

-- 2.5.2 检验危急值信息
CREATE OR REPLACE VIEW QM_I_LIS_WeiJiZhi AS
SELECT
    NULL AS HZLY,
    NULL AS HZBH,
    NULL AS HZXM,
    NULL AS JYSJ,
    NULL AS XMMC,
    NULL AS JIEGUO
FROM DUAL WHERE 1=0;

-- 2.6.1 医学影像检查记录
CREATE OR REPLACE VIEW QM_I_PACS_MEDICAL_CHECKRESULT AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS VISITTYPE,
    NULL AS JCSJ,
    NULL AS ITEMNAME,
    NULL AS CHECKPART,
    NULL AS CHECKRESULT
FROM DUAL WHERE 1=0;

-- 2.6.2 病理标本检查记录
CREATE OR REPLACE VIEW QM_I_PACS_BL_CHECKRESULT AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS VISITTYPE,
    NULL AS LTSJ,
    NULL AS BBSJ
FROM DUAL WHERE 1=0;

-- 2.7.1 感染上报信息
CREATE OR REPLACE VIEW QM_I_INFECT_3G AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS PATIENTNAME,
    NULL AS INFECTEDTIME,
    NULL AS INFECTEDDEPTNAME,
    NULL AS INFECTEDTYPE
FROM DUAL WHERE 1=0;

-- 2.7.2 手术部位感染上报信息
CREATE OR REPLACE VIEW QM_I_INFECT_SS AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS PATIENTNAME,
    NULL AS INFECTEDTIME,
    NULL AS INFECTEDDEPTNAME,
    NULL AS OPERATETIME
FROM DUAL WHERE 1=0;

-- 2.8.1 急诊就诊信息
CREATE OR REPLACE VIEW QM_I_HIS_JZFZ AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS RQ,
    NULL AS LVL,
    NULL AS INDATE,
    NULL AS OUTDATE
FROM DUAL WHERE 1=0;

-- 2.9.1 不良事件上报信息
CREATE OR REPLACE VIEW QC_I_BLSJXX AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS P3,
    NULL AS REPORTDATE,
    NULL AS AERSDATE,
    NULL AS AERSCLASS
FROM DUAL WHERE 1=0;

-- 2.10.1 随访结果
CREATE OR REPLACE VIEW QM_I_SFXX AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS P3,
    NULL AS RQ,
    NULL AS PATIENTTYPE
FROM DUAL WHERE 1=0;

-- 2.11.1 输血记录单
CREATE OR REPLACE VIEW QM_I_SXSQDXX AS
SELECT
    NULL AS PATIENTID,
    NULL AS VISITNO,
    NULL AS 输血方式,
    NULL AS 既往输血史,
    NULL AS 血液成分1
FROM DUAL WHERE 1=0;

-- =====================================================
-- 验证视图创建结果
-- =====================================================
SELECT
    TABLE_NAME AS view_name,
    TABLE_COMMENT AS comment
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'd_hos_indicator_mtr_20260720'
  AND TABLE_TYPE = 'VIEW'
  AND TABLE_NAME LIKE 'QM_I_%' OR TABLE_NAME LIKE 'QC_I_%'
ORDER BY TABLE_NAME;
