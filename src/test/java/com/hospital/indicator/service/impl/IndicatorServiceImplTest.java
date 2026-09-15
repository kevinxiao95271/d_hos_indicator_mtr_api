package com.hospital.indicator.service.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.hospital.indicator.common.BusinessException;
import com.hospital.indicator.common.ErrorCode;
import com.hospital.indicator.dto.IndicatorSaveDTO;
import com.hospital.indicator.dto.IndicatorTreeDTO;
import com.hospital.indicator.entity.Indicator;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.BeanUtils;

import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.spy;

class IndicatorServiceImplTest {

    @Test
    void shouldRejectDuplicateMetricCode() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        Indicator duplicate = new Indicator();
        duplicate.setId(1L);
        duplicate.setMetricCode("DUPLICATE");
        doReturn(duplicate).when(service).getOne(any());

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(autoLeaf("DUPLICATE", null)));

        assertEquals(ErrorCode.INDICATOR_CODE_DUPLICATE, error.getCode());
    }

    @Test
    void shouldRejectMetricCodeDuplicatedByLegacyCode() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        Indicator duplicate = new Indicator();
        duplicate.setId(1L);
        duplicate.setMetricCode("2.1.7");
        duplicate.setLegacyCode("A4901");
        doReturn(duplicate).when(service).getOne(any());

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(autoLeaf("A4901", null)));

        assertEquals(ErrorCode.INDICATOR_CODE_DUPLICATE, error.getCode());
    }

    @Test
    void shouldRejectMissingParent() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(autoLeaf("CHILD", "NOT_EXISTS")));

        assertEquals(ErrorCode.NOT_FOUND, error.getCode());
    }

    @Test
    void shouldPersistBusinessDirectionAndDeriveLevel() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        Indicator parent = new Indicator();
        parent.setMetricCode("PARENT");
        parent.setIndicatorLevel(2);
        parent.setIsLeaf(0);
        parent.setMetricPool("POOL_NATIONAL");
        doReturn(null, parent).when(service).getOne(any());
        doReturn(true).when(service).saveOrUpdate(any(Indicator.class));

        IndicatorSaveDTO dto = autoLeaf("CHILD", "PARENT");
        dto.setBusinessDirection("INPATIENT,OUTPATIENT");
        dto.setIndicatorLevel(99);
        Indicator saved = service.saveOrUpdateIndicator(dto);

        assertEquals(3, saved.getIndicatorLevel());
        assertEquals("INPATIENT,OUTPATIENT", saved.getBusinessDirection());
    }

    @Test
    void shouldResolveParentByLegacyCodeAndPersistCanonicalParentCode() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        Indicator parent = category("2.1", "A4900", "POOL_GRADE", 2);
        doReturn(null, parent).when(service).getOne(any());
        doReturn(true).when(service).saveOrUpdate(any(Indicator.class));

        IndicatorSaveDTO dto = autoLeaf("2.1.7", " A4900 ");
        dto.setMetricPool("POOL_GRADE");
        Indicator saved = service.saveOrUpdateIndicator(dto);

        assertEquals("2.1", saved.getParentCode());
        assertEquals(3, saved.getIndicatorLevel());
    }

    @Test
    void shouldAllowLegacyCodeOnUpdateAndKeepCanonicalMetricCode() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        Indicator existing = new Indicator();
        existing.setId(7L);
        existing.setMetricCode("2.1.7");
        existing.setLegacyCode("A4901");
        doReturn(existing).when(service).getById(7L);
        doReturn(existing).when(service).getOne(any());
        doReturn(0L).when(service).count(any());
        doReturn(true).when(service).saveOrUpdate(any(Indicator.class));

        IndicatorSaveDTO dto = autoLeaf(" A4901 ", null);
        dto.setId(7L);
        Indicator saved = service.saveOrUpdateIndicator(dto);

        assertEquals("2.1.7", saved.getMetricCode());
    }

    @Test
    void shouldRejectManualIndicatorWithExpressionCalculation() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        IndicatorSaveDTO dto = autoLeaf("MANUAL", null);
        dto.setInputType("MANUAL");
        dto.setCalculationType("EXPRESSION");

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(dto));

        assertEquals(ErrorCode.INDICATOR_CONFIG_CONFLICT, error.getCode());
    }

    @ParameterizedTest
    @ValueSource(strings = {"a1/a2", "a1/a2*10", "a1/a2*1000", "a1/a2*100.5"})
    void shouldRejectInvalidPercentageScales(String expression) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        IndicatorSaveDTO dto = ratioLeaf("PERCENT_RATE", "测试病死率", expression, "%");

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(dto));

        assertEquals(ErrorCode.INDICATOR_CONFIG_CONFLICT, error.getCode());
    }

    @ParameterizedTest
    @ValueSource(strings = {"a1/a2", "a1/a2*100", "a1/a2*10000", "a1/a2*1000.5"})
    void shouldRejectInvalidPermilleScales(String expression) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        IndicatorSaveDTO dto = ratioLeaf("PERMILLE_RATE", "测试发生率", expression, "‰");

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(dto));

        assertEquals(ErrorCode.INDICATOR_CONFIG_CONFLICT, error.getCode());
    }

    @ParameterizedTest
    @MethodSource("validRatioExpressions")
    void shouldPersistRateWithMatchingScaleAndUnit(
            String metricName, String expression, String unit) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        doReturn(true).when(service).saveOrUpdate(any(Indicator.class));
        IndicatorSaveDTO dto = ratioLeaf("RATE", metricName, expression, unit);

        Indicator saved = service.saveOrUpdateIndicator(dto);

        assertEquals(expression, saved.getExpression());
        assertEquals(unit, saved.getUnit());
    }

    static Stream<Arguments> validRatioExpressions() {
        return Stream.of(
                Arguments.of("测试病死率", "a1/a2*100", "%"),
                Arguments.of("测试占比", "a1/a2 * 100", "%"),
                Arguments.of("测试病死率", "(a1/a2) * 100.0", "%"),
                Arguments.of("测试发生率", "a1/a2*100.00   ", "%"),
                Arguments.of("测试发生率", "a1/a2*1000", "‰"),
                Arguments.of("测试占比", "a1/a2 * 1000", "‰"),
                Arguments.of("测试发生率", "(a1/a2) * 1000.0", "‰"),
                Arguments.of("测试发生率", "a1/a2*1000.00   ", "‰"));
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {" ", "\t"})
    void shouldRejectRateWithoutPercentOrPermilleUnit(String unit) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        IndicatorSaveDTO dto = ratioLeaf("RATE", "测试病死率", "a1/a2*100", unit);

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(dto));

        assertEquals(ErrorCode.INDICATOR_CONFIG_CONFLICT, error.getCode());
    }

    @ParameterizedTest
    @ValueSource(strings = {"A4901", "2", ".2.1", "2.1.", "2..1", "2-1", "2. 1", " "})
    void shouldRejectNonStandardCodeForGradeLeaf(String metricCode) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        IndicatorSaveDTO dto = autoLeaf(metricCode, null);
        dto.setMetricPool("POOL_GRADE");

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(dto));

        assertEquals(ErrorCode.PARAM_INVALID, error.getCode());
    }

    @ParameterizedTest
    @ValueSource(strings = {"2.1.7 测试病死率", "2.1.7测试病死率", "  2.1.7  测试病死率"})
    void shouldRejectCodePrefixInGradeMetricName(String metricName) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        IndicatorSaveDTO dto = autoLeaf("2.1.7", null);
        dto.setMetricPool("POOL_GRADE");
        dto.setMetricName(metricName);

        BusinessException error = assertThrows(BusinessException.class,
                () -> service.saveOrUpdateIndicator(dto));

        assertEquals(ErrorCode.PARAM_INVALID, error.getCode());
    }

    @ParameterizedTest
    @MethodSource("poolAndNodeTypeCases")
    void shouldApplyGradeCodeRulesOnlyToGradeLeaves(
            String pool, int isLeaf, String code, String name) {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        doReturn(true).when(service).saveOrUpdate(any(Indicator.class));
        IndicatorSaveDTO dto = autoLeaf(code, null);
        dto.setMetricPool(pool);
        dto.setIsLeaf(isLeaf);
        dto.setMetricName(name);
        if (isLeaf == 0) {
            dto.setCalculationType("NONE");
        }

        Indicator saved = service.saveOrUpdateIndicator(dto);

        assertEquals(code, saved.getMetricCode());
        assertEquals(name, saved.getMetricName());
    }

    static Stream<Arguments> poolAndNodeTypeCases() {
        return Stream.of(
                Arguments.of("POOL_NATIONAL", 1, "A4901", "2.1.7 测试病死率"),
                Arguments.of("POOL_NATIONAL", 0, "A4901", "2.1.7 分类"),
                Arguments.of("POOL_GRADE", 0, "A4901", "2.1.7 分类"),
                Arguments.of("POOL_GRADE", 1, "2.1.7", "测试病死率"));
    }

    @Test
    void shouldNormalizeWhitespaceAndDefaultBlankPoolAndInputType() {
        IndicatorServiceImpl service = spy(new IndicatorServiceImpl());
        doReturn(null).when(service).getOne(any());
        doReturn(true).when(service).saveOrUpdate(any(Indicator.class));
        IndicatorSaveDTO dto = autoLeaf(" NATIONAL_CODE ", " \t ");
        dto.setMetricName("  测试指标  ");
        dto.setMetricPool(" ");
        dto.setInputType("\t");

        Indicator saved = service.saveOrUpdateIndicator(dto);

        assertEquals("NATIONAL_CODE", saved.getMetricCode());
        assertEquals("测试指标", saved.getMetricName());
        assertEquals("POOL_NATIONAL", saved.getMetricPool());
        assertEquals("AUTO", saved.getInputType());
        assertNull(saved.getParentCode());
        assertEquals(1, saved.getIndicatorLevel());
    }

    @Test
    void shouldBuildDisplayNameFromCodeAndPureName() {
        Indicator indicator = new Indicator();
        indicator.setMetricCode("2.1.7");
        indicator.setMetricName("测试病死率");

        assertEquals("2.1.7测试病死率", indicator.getDisplayName());
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {" ", "\t"})
    void shouldReturnMetricNameWhenDisplayCodeIsNullOrBlank(String metricCode) {
        Indicator indicator = new Indicator();
        indicator.setMetricCode(metricCode);
        indicator.setMetricName("测试指标");

        assertEquals("测试指标", indicator.getDisplayName());
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {" ", "\t"})
    void shouldReturnMetricCodeWhenDisplayNameIsNullOrBlank(String metricName) {
        Indicator indicator = new Indicator();
        indicator.setMetricCode("2.1.7");
        indicator.setMetricName(metricName);

        assertEquals("2.1.7", indicator.getDisplayName());
    }

    @Test
    void shouldReturnNullDisplayNameWhenCodeAndNameAreNull() {
        assertNull(new Indicator().getDisplayName());
    }

    @Test
    void shouldExposeDisplayNameInListSerialization() throws Exception {
        Indicator indicator = gradeIndicator();

        String json = new ObjectMapper().writeValueAsString(indicator);

        assertTrue(json.contains("\"displayName\":\"2.7.1xxxx病死率\""));
    }

    @Test
    void shouldCopyDisplayNameToTreeNode() {
        Indicator indicator = gradeIndicator();
        IndicatorTreeDTO treeNode = new IndicatorTreeDTO();

        BeanUtils.copyProperties(indicator, treeNode);

        assertEquals("2.7.1xxxx病死率", treeNode.getDisplayName());
    }

    private Indicator gradeIndicator() {
        Indicator indicator = new Indicator();
        indicator.setMetricCode("2.7.1");
        indicator.setLegacyCode("A4901");
        indicator.setMetricName("xxxx病死率");
        return indicator;
    }

    private Indicator category(
            String metricCode, String legacyCode, String metricPool, int indicatorLevel) {
        Indicator indicator = new Indicator();
        indicator.setMetricCode(metricCode);
        indicator.setLegacyCode(legacyCode);
        indicator.setMetricPool(metricPool);
        indicator.setIndicatorLevel(indicatorLevel);
        indicator.setIsLeaf(0);
        return indicator;
    }

    private IndicatorSaveDTO ratioLeaf(String code, String name, String expression, String unit) {
        IndicatorSaveDTO dto = autoLeaf(code, null);
        dto.setMetricName(name);
        dto.setCalculationType("EXPRESSION");
        dto.setExpression(expression);
        dto.setRelatedItems("[\"a1\",\"a2\"]");
        dto.setUnit(unit);
        return dto;
    }

    private IndicatorSaveDTO autoLeaf(String code, String parentCode) {
        IndicatorSaveDTO dto = new IndicatorSaveDTO();
        dto.setMetricCode(code);
        dto.setMetricName("测试指标");
        dto.setParentCode(parentCode);
        dto.setIsLeaf(1);
        dto.setMetricType("QUANTITATIVE");
        dto.setCalculationType("ITEM");
        dto.setExpression("a0050");
        dto.setRelatedItems("[\"a0050\"]");
        dto.setInputType("AUTO");
        dto.setMetricPool("POOL_NATIONAL");
        dto.setStatus(1);
        return dto;
    }
}
