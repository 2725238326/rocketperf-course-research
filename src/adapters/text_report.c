#include "text_report.h"

#include <string.h>

#define RP_TEXT_LABEL_COLUMNS 28U
#define RP_TEXT_NUMBER_COLUMNS 14U

/* Approximate terminal cell width of a UTF-8 string: continuation bytes add
 * nothing, three-or-more-byte lead bytes count as East-Asian double width. */
static unsigned int text_width(const char *text)
{
    unsigned int width = 0U;
    for (const unsigned char *p = (const unsigned char *)text; *p != '\0'; ++p) {
        if ((*p & 0xC0U) == 0x80U) { continue; }
        width += (*p >= 0xE0U) ? 2U : 1U;
    }
    return width;
}

static int write_padded(FILE *stream, const char *label)
{
    const unsigned int width = text_width(label);
    if (fputs("  ", stream) < 0 || fputs(label, stream) < 0) { return 0; }
    for (unsigned int i = width; i < RP_TEXT_LABEL_COLUMNS; ++i) {
        if (fputc(' ', stream) == EOF) { return 0; }
    }
    return 1;
}

int rp_text_heading(FILE *stream, const char *title)
{
    return fprintf(stream, "\n========== %s ==========\n", title) >= 0;
}

int rp_text_note(FILE *stream, const char *text)
{
    return fprintf(stream, "  限制: %s\n", text) >= 0;
}

int rp_text_value(FILE *stream, const char *label, double value, const char *unit)
{
    return write_padded(stream, label) && fprintf(stream, "%.6g %s\n", value, unit) >= 0;
}

static int text_row3(FILE *stream, const char *label, double first, double second, double delta)
{
    return write_padded(stream, label) &&
        fprintf(stream, "%*.6g %*.6g %+.6g\n", (int)RP_TEXT_NUMBER_COLUMNS, first,
                (int)RP_TEXT_NUMBER_COLUMNS, second, delta) >= 0;
}

int rp_text_mixture(FILE *stream, const char *title, const RpGasMixture *gas)
{
    if (!rp_text_value(stream, "温度 T", gas->temperature_k, "K") ||
        !rp_text_value(stream, "压力 p", gas->pressure_pa, "Pa") ||
        !rp_text_value(stream, "摩尔质量 M", gas->molar_mass_kg_per_kmol, "kg/kmol") ||
        !rp_text_value(stream, "气体常数 R", gas->gas_constant_j_per_kg_k, "J/(kg·K)") ||
        !rp_text_value(stream, "冻结定压比热 cp", gas->cp_frozen_j_per_kg_k, "J/(kg·K)") ||
        !rp_text_value(stream, "比焓 h", gas->h_j_per_kg, "J/kg") ||
        !rp_text_value(stream, "比熵 s", gas->s_j_per_kg_k, "J/(kg·K)")) { return 0; }
    if (fprintf(stream, "  %s摩尔分数:\n", title != NULL ? title : "") < 0) { return 0; }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        if (fprintf(stream, "    %-5s %12.6g\n", rp_cho_species_id(i), gas->mole_fractions[i]) < 0) { return 0; }
    }
    return 1;
}

int rp_text_chamber_diagnostics(FILE *stream, const RpCombustionResult *result)
{
    return fprintf(stream,
        "  诊断: 元素残差 [%.3g %.3g %.3g], 平衡残差 %.3g, 焓残差 %.4g J/kg, "
        "平衡迭代 %u, HP迭代 %u\n",
        result->element_relative_residual[0], result->element_relative_residual[1],
        result->element_relative_residual[2], result->equilibrium_residual,
        result->enthalpy_residual_j_per_kg, result->equilibrium_iterations,
        result->hp_iterations) >= 0;
}

static int text_station(FILE *stream, const char *name, const RpFrozenFlowStation *station)
{
    return fprintf(stream, "  %s: T=%.6g K, p=%.6g Pa, V=%.6g m/s, Mach=%.4g, 流量密度=%.6g kg/(m2·s)\n",
                   name, station->gas.temperature_k, station->gas.pressure_pa,
                   station->velocity_m_per_s, station->mach, station->mass_flux_kg_per_m2_s) >= 0;
}

int rp_text_frozen_nozzle(FILE *stream, const RpFrozenNozzleResult *nozzle)
{
    if (fputs("  喷管 (燃烧室冻结, 无激波/分离):\n", stream) < 0 ||
        !text_station(stream, "喉部", &nozzle->throat) ||
        !text_station(stream, "出口", &nozzle->exit)) { return 0; }
    return rp_text_value(stream, "特征速度 c*", nozzle->cstar_m_per_s, "m/s") &&
        rp_text_value(stream, "真空有效速度", nozzle->vacuum_effective_velocity_m_per_s, "m/s") &&
        rp_text_value(stream, "有效速度", nozzle->effective_velocity_m_per_s, "m/s") &&
        rp_text_value(stream, "推力系数 CF", nozzle->thrust_coefficient, "-") &&
        fprintf(stream, "  诊断: 连续残差 %.3g, 声速残差 %.3g\n",
                nozzle->continuity_relative_residual, nozzle->sonic_relative_residual) >= 0;
}

int rp_text_fixed_geometry(FILE *stream, const RpFrozenNozzleFixedResult *geometry)
{
    return rp_text_value(stream, "喉部面积 At", geometry->throat_area_m2, "m2") &&
        rp_text_value(stream, "出口面积 Ae", geometry->exit_area_m2, "m2") &&
        rp_text_value(stream, "质量流量 mdot", geometry->mass_flow_kg_per_s, "kg/s") &&
        rp_text_value(stream, "推力 F", geometry->thrust_n, "N") &&
        rp_text_value(stream, "比冲 Isp", geometry->specific_impulse_s, "s");
}

int rp_text_ideal_result(FILE *stream, const RpNozzleInput *input,
                         const RpNozzleResult *result)
{
    if (!rp_text_heading(stream, "理想气体喷管 L0 (定比热)") ||
        !rp_text_value(stream, "比热比 gamma", input->gamma, "-") ||
        !rp_text_value(stream, "气体常数 R", input->gas_constant_j_kg_k, "J/(kg·K)") ||
        !rp_text_value(stream, "总温 T0", input->stagnation_temperature_k, "K") ||
        !rp_text_value(stream, "总压 P0", input->stagnation_pressure_pa, "Pa") ||
        !rp_text_value(stream, "喉部面积 At", input->throat_area_m2, "m2") ||
        !rp_text_value(stream, "面积比 Ae/At", input->area_ratio, "-") ||
        !rp_text_value(stream, "环境压力 pa", input->ambient_pressure_pa, "Pa")) { return 0; }
    return rp_text_value(stream, "出口马赫 Mach", result->exit_mach, "-") &&
        rp_text_value(stream, "出口温度", result->exit_temperature_k, "K") &&
        rp_text_value(stream, "出口压力", result->exit_pressure_pa, "Pa") &&
        rp_text_value(stream, "出口速度", result->exit_velocity_m_s, "m/s") &&
        rp_text_value(stream, "出口面积 Ae", result->exit_area_m2, "m2") &&
        rp_text_value(stream, "特征速度 c*", result->characteristic_velocity_m_s, "m/s") &&
        rp_text_value(stream, "质量流量 mdot", result->mass_flow_kg_s, "kg/s") &&
        rp_text_value(stream, "推力 F", result->thrust_n, "N") &&
        rp_text_value(stream, "推力系数 CF", result->thrust_coefficient, "-") &&
        rp_text_value(stream, "比冲 Isp", result->specific_impulse_s, "s") &&
        fprintf(stream, "  诊断: 求根迭代 %u, 面积相对残差 %.3g\n",
                result->root_iterations, result->relative_area_residual) >= 0 &&
        rp_text_note(stream, "定比热理想气体教学模型;无化学反应、损失、激波、分离或循环。");
}

int rp_text_liquid_state(FILE *stream, const char *name, const RpLiquidFeedState *state)
{
    return fprintf(stream, "  %s: 密度=%.6g kg/m3, h=%.6g J/mol (%.6g J/kg), "
                   "EOS摩尔质量=%.6g, 化学摩尔质量=%.6g kg/mol\n",
                   name, state->density_kg_per_m3, state->h_j_per_mol, state->h_j_per_kg,
                   state->eos_molar_mass_kg_per_mol, state->chemical_molar_mass_kg_per_mol) >= 0;
}

int rp_text_thermo_state(FILE *stream, const RpNasa9Species *species,
                         double temperature_k, const RpThermoState *state)
{
    return fprintf(stream, "  物种 %s (NASA9, 参考压力 100000 Pa, T=%.6g K):\n"
                   "    摩尔质量 %.6g kg/kmol\n    cp %.6g J/(kg·K)\n"
                   "    h %.6g J/kg\n    s %.6g J/(kg·K)\n",
                   species->id, temperature_k, species->molar_mass_kg_per_kmol,
                   state->cp_j_per_kg_k, state->h_j_per_kg, state->s_j_per_kg_k) >= 0;
}

int rp_text_propellant_comparison(FILE *stream, const RpPropellantComparisonInput *input,
                                  const RpPropellantComparisonResult *result)
{
    const RpCombustionResult *mc = &result->methane.hp.chamber;
    const RpCombustionResult *kc = &result->kerosene.chamber;
    const RpFrozenNozzleFixedResult *mn = &result->methane.nozzle;
    const RpFrozenNozzleFixedResult *kn = &result->kerosene.nozzle;
    if (!rp_text_heading(stream, "甲烷 / RP-1 同条件对比") ||
        fprintf(stream, "  共同条件: Pc=%.6g MPa, At=%.6g m2, Ae/At=%.6g, 背压=%.6g kPa\n",
                input->methane.product_pressure_pa / 1e6, input->throat_area_m2,
                input->area_ratio, input->ambient_pressure_pa / 1e3) < 0 ||
        fprintf(stream, "  入口: CH4查表 %.6g K/%.6g MPa, O2 %.6g K/%.6g MPa, O/F=%.6g; "
                "RP-1 %.6g K, O2(L) %.6g K, O/F=%.6g\n",
                input->methane.fuel_temperature_k, input->methane.fuel_pressure_pa / 1e6,
                input->methane.oxidizer_temperature_k, input->methane.oxidizer_pressure_pa / 1e6,
                input->methane.oxidizer_fuel_mass_ratio,
                input->kerosene.reactants.fuel_temperature_k,
                input->kerosene.reactants.oxidizer_temperature_k,
                input->kerosene.reactants.oxidizer_fuel_mass_ratio) < 0 ||
        !write_padded(stream, "量") ||
        fprintf(stream, "%*s %*s %s\n", (int)RP_TEXT_NUMBER_COLUMNS, "CH4",
                (int)RP_TEXT_NUMBER_COLUMNS, "RP-1", "差值 CH4-RP1") < 0) { return 0; }
    if (!text_row3(stream, "燃烧室温度 Tc", mc->gas.temperature_k, kc->gas.temperature_k,
                   mc->gas.temperature_k - kc->gas.temperature_k) ||
        !text_row3(stream, "特征速度 c* [m/s]", mn->nozzle.cstar_m_per_s,
                   kn->nozzle.cstar_m_per_s, result->methane_minus_kerosene_cstar_m_per_s) ||
        !text_row3(stream, "质量流量 mdot [kg/s]", mn->mass_flow_kg_per_s,
                   kn->mass_flow_kg_per_s, result->methane_minus_kerosene_mass_flow_kg_per_s) ||
        !text_row3(stream, "推力 F [N]", mn->thrust_n, kn->thrust_n,
                   result->methane_minus_kerosene_thrust_n) ||
        !text_row3(stream, "比冲 Isp [s]", mn->specific_impulse_s, kn->specific_impulse_s,
                   result->methane_minus_kerosene_isp_s) ||
        !text_row3(stream, "出口马赫 Mach", mn->nozzle.exit.mach, kn->nozzle.exit.mach,
                   mn->nozzle.exit.mach - kn->nozzle.exit.mach) ||
        !text_row3(stream, "推力系数 CF", mn->nozzle.thrust_coefficient,
                   kn->nozzle.thrust_coefficient,
                   mn->nozzle.thrust_coefficient - kn->nozzle.thrust_coefficient) ||
        !text_row3(stream, "出口压力 pe [Pa]", mn->nozzle.exit.gas.pressure_pa,
                   kn->nozzle.exit.gas.pressure_pa,
                   mn->nozzle.exit.gas.pressure_pa - kn->nozzle.exit.gas.pressure_pa) ||
        !text_row3(stream, "出口面积 Ae [m2]", mn->exit_area_m2, kn->exit_area_m2,
                   mn->exit_area_m2 - kn->exit_area_m2)) { return 0; }
    return rp_text_note(stream, "各自具名入口与O/F的算例;不是真实型号性能排名或最优混合比。") &&
        rp_text_note(stream, "九种中性理想气相产物+燃烧室冻结喷管;无凝聚碳、泵、喷注或循环闭合。");
}

static const char *regime_label(RpNozzleRegime regime)
{
    switch (regime) {
        case RP_NOZZLE_REGIME_IDEAL_DOMAIN:
            return "理想附着域 (匹配/欠膨胀/真空,附着求解适用)";
        case RP_NOZZLE_REGIME_OVEREXPANDED_POSSIBLE:
            return "过膨胀域:理想出口压力低于背压,但未越过经验分离参考(附着性未知)";
        case RP_NOZZLE_REGIME_SEPARATION_HINT:
            return "过膨胀域:理想出口压力已低于经验分离参考压,提示喷管内可能分离(提示非预测)";
    }
    return "未知";
}

static int text_regime_common(FILE *stream, double ambient_pa, double exit_pa,
                              double separation_reference_pa,
                              int separation_available, double separation_ratio,
                              int matched_available, double matched_ratio)
{
    char reference_label[48];
    (void)snprintf(reference_label, sizeof(reference_label), "经验分离参考压 %g*pa",
                   RP_NOZZLE_SEPARATION_FRACTION);
    if (!rp_text_value(stream, "理想出口压力 pe", exit_pa, "Pa") ||
        !rp_text_value(stream, "背压/出口压比 pa/pe", ambient_pa / exit_pa, "-") ||
        !rp_text_value(stream, reference_label, separation_reference_pa, "Pa")) { return 0; }
    if (separation_available &&
        !rp_text_value(stream, "分离参考面积比(提示)", separation_ratio, "-")) { return 0; }
    if (matched_available &&
        !rp_text_value(stream, "该背压匹配面积比", matched_ratio, "-")) { return 0; }
    return 1;
}

int rp_text_ideal_regime(FILE *stream, const RpNozzleInput *input,
                         const RpNozzleRegimeResult *regime)
{
    if (!rp_text_heading(stream, "理想气体喷管 L0 域评估") ||
        fprintf(stream, "  工况分级: %s\n", regime_label(regime->regime)) < 0 ||
        !rp_text_value(stream, "总压 P0", input->stagnation_pressure_pa, "Pa") ||
        !rp_text_value(stream, "面积比 Ae/At", input->area_ratio, "-") ||
        !rp_text_value(stream, "环境背压 pa", input->ambient_pressure_pa, "Pa") ||
        !text_regime_common(stream, input->ambient_pressure_pa,
                            regime->ideal.exit_pressure_pa,
                            regime->separation_reference_pa,
                            regime->separation_area_ratio_available,
                            regime->separation_area_ratio,
                            regime->matched_area_ratio_available,
                            regime->matched_area_ratio) ||
        !rp_text_value(stream, "理想出口马赫", regime->ideal.exit_mach, "-") ||
        !rp_text_value(stream, "理想推力(含压力项)", regime->thrust_n, "N")) { return 0; }
    return rp_text_note(stream, "理想附着解的pe与pa无关;分离参考与面积比为经验提示,真实推力取决于分离位置,本模型不计算。");
}

int rp_text_frozen_regime(FILE *stream, const RpFrozenNozzleInput *input,
                          const RpFrozenNozzleRegimeResult *regime)
{
    if (!rp_text_heading(stream, "冻结喷管域评估") ||
        fprintf(stream, "  工况分级: %s\n", regime_label(regime->regime)) < 0 ||
        !rp_text_value(stream, "燃烧室压力 Pc", input->chamber_pressure_pa, "Pa") ||
        !rp_text_value(stream, "面积比 Ae/At", input->area_ratio, "-") ||
        !rp_text_value(stream, "环境背压 pa", input->ambient_pressure_pa, "Pa") ||
        !text_regime_common(stream, input->ambient_pressure_pa,
                            regime->ideal.exit.gas.pressure_pa,
                            regime->separation_reference_pa,
                            regime->separation_area_ratio_available,
                            regime->separation_area_ratio,
                            regime->matched_area_ratio_available,
                            regime->matched_area_ratio) ||
        !rp_text_value(stream, "理想出口马赫", regime->ideal.exit.mach, "-") ||
        !rp_text_value(stream, "理想质量流量", regime->mass_flow_kg_per_s, "kg/s") ||
        !rp_text_value(stream, "理想推力(含压力项)", regime->ideal_thrust_n, "N") ||
        !rp_text_value(stream, "理想比冲(含压力项)", regime->ideal_specific_impulse_s, "s")) { return 0; }
    return rp_text_note(stream, "理想附着解的pe与pa无关;分离参考与面积比为经验提示,真实推力取决于分离位置,本模型不计算。");
}
