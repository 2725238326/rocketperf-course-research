/**
 * frozen.c: 冻结流喷管求解器（理想气体混合物、温变比热）
 *
 * 物理模型：
 *   1. 等熵膨胀：ds = 0，从燃烧室滞止状态到出口
 *   2. 燃烧室冻结：燃烧室到喉部及出口沿用相同摩尔分数（无化学反应）
 *   3. 理想气体物性：cp(T), h(T), s(T,P) 来自NASA9多项式（温度相关）
 *   4. 一维稳定流：忽略边界层、激波、径向速度
 *
 * 与ideal.c的区别：
 *   - ideal.c：γ = 常数（理想气体，单一比热比）
 *   - frozen.c：cp(T), γ(T) 变化（仍用理想气体状态方程）
 *
 * 守恒方程：
 *   - 能量：h0 = h + u²/2（总焓守恒，h0为燃烧室滞止焓）
 *   - 熵：s = s0（等熵膨胀，s0为燃烧室滞止熵）
 *   - 质量：ṁ = ρ·A·u（质量流量守恒）
 *
 * 数值方法：
 *   - 外层：二分查找出口温度 Te，使得面积比匹配
 *   - 内层：给定 Te，计算 Pe（等熵关系）、ue（能量守恒）、Ae（质量守恒）
 *   - 残差：log(Ae_calculated / Ae_target)
 *
 * 适用范围：
 *   ✓ 燃烧室高温燃气；膨胀温度下限取各物种NASA9拟合区下限（rp_cho_minimum_temperature）
 *   ✓ 燃烧室平衡态已知（9物种C-H-O混合物）
 *   ✓ 声明采用化学冻结近似；不由本程序预测停留时间或反应时间尺度
 *   ✗ 不适用：碳烟析出、H₂O高温再解离、液滴携带
 *   ✗ 不建模：边界层、激波、流动分离、非设计点损失
 *
 * 输入约束：
 *   - chamber: 燃烧室平衡态（温度、压力、摩尔分数）
 *   - throat_area_m2: 喉部面积 [m²]，需 > 0
 *   - exit_area_ratio: 面积比 Ae/At，范围 [1.0, 1e4]
 *   - ambient_pressure_pa: 背压 [Pa]，需 ≥ 0
 *
 * 验证（rp_nozzle_solve_frozen内拒绝超限结果）：
 *   - 能量残差：|h + u²/2 - h0| ≤ 1e-5 J/kg（喉部与出口）
 *   - 熵残差：|s - s0| ≤ 1e-7 J/(kg·K)；连续性与声速相对残差 ≤ 1e-8
 *   - 与NASA CEA冻结流模式对照（Frozen expansion）
 */

#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/numeric.h"
#include "rocketperf/version.h"

#include <math.h>
#include <stddef.h>

typedef struct {
    RpGasMixture chamber;
    double throat_flux;
    double area_ratio;
} FrozenContext;

static RpStatus flow_station(const FrozenContext *context, double temperature,
                              RpFrozenFlowStation *output, RpError *error)
{
    RpFrozenFlowStation station = {0};
    RpGasMixture at_chamber_pressure;
    RpStatus status = rp_cho_mixture_evaluate(context->chamber.mole_fractions, temperature,
                                              context->chamber.pressure_pa, &at_chamber_pressure, error);
    double pressure;
    double kinetic_energy;
    double gamma;
    double sound_squared;
    if (status != RP_OK) { return status; }
    pressure = context->chamber.pressure_pa * exp((at_chamber_pressure.s_j_per_kg_k -
               context->chamber.s_j_per_kg_k) / context->chamber.gas_constant_j_per_kg_k);
    if (!rp_isfinite(pressure) || pressure <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Frozen nozzle pressure underflow or overflow.");
    }
    /* Ideal-gas h/cp/composition do not depend on pressure. Reuse the NASA9
     * evaluation; only the entropy pressure term changes at this station. */
    station.gas = at_chamber_pressure;
    station.gas.pressure_pa = pressure;
    station.gas.s_j_per_kg_k -= station.gas.gas_constant_j_per_kg_k *
        (log(pressure) - log(context->chamber.pressure_pa));
    kinetic_energy = context->chamber.h_j_per_kg - station.gas.h_j_per_kg;
    if (kinetic_energy < 0.0 || !rp_isfinite(kinetic_energy)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Negative or non-finite frozen nozzle kinetic energy.");
    }
    gamma = station.gas.cp_frozen_j_per_kg_k /
        (station.gas.cp_frozen_j_per_kg_k - station.gas.gas_constant_j_per_kg_k);
    sound_squared = gamma * station.gas.gas_constant_j_per_kg_k * temperature;
    station.velocity_m_per_s = sqrt(2.0 * kinetic_energy);
    station.mach = station.velocity_m_per_s / sqrt(sound_squared);
    station.mass_flux_kg_per_m2_s = pressure / (station.gas.gas_constant_j_per_kg_k * temperature) * station.velocity_m_per_s;
    station.energy_residual_j_per_kg = station.gas.h_j_per_kg +
        0.5 * station.velocity_m_per_s * station.velocity_m_per_s - context->chamber.h_j_per_kg;
    station.entropy_residual_j_per_kg_k = station.gas.s_j_per_kg_k - context->chamber.s_j_per_kg_k;
    if (!rp_isfinite(sound_squared) || sound_squared <= 0.0 || !rp_isfinite(station.mach) ||
        !rp_isfinite(station.mass_flux_kg_per_m2_s) || !rp_isfinite(station.energy_residual_j_per_kg) ||
        !rp_isfinite(station.entropy_residual_j_per_kg_k)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite frozen flow station.");
    }
    *output = station;
    return RP_OK;
}

static double sonic_equation(double temperature, const void *opaque)
{
    const FrozenContext *context = opaque;
    RpFrozenFlowStation station = {0};
    if (flow_station(context, temperature, &station, NULL) != RP_OK) { return NAN; }
    return station.mach * station.mach - 1.0;
}

typedef struct {
    const FrozenContext *flow;
    double target_pa;
} PressureTarget;

static double pressure_equation(double temperature, const void *opaque)
{
    const PressureTarget *equation = opaque;
    RpFrozenFlowStation station = {0};
    if (flow_station(equation->flow, temperature, &station, NULL) != RP_OK) { return NAN; }
    return station.gas.pressure_pa - equation->target_pa;
}

/* Isentropic area ratio whose station static pressure equals target_pa.
 * Zero when the bracket leaves the throat..minimum-temperature span. */
static int area_ratio_for_pressure(const FrozenContext *context,
                                   double minimum_temperature,
                                   double throat_temperature,
                                   double target_pa,
                                   const RpRootOptions *policy,
                                   double *area_ratio)
{
    PressureTarget equation = {context, target_pa};
    RpRootResult root;
    RpFrozenFlowStation station = {0};
    double ratio;
    if (!rp_isfinite(target_pa) || target_pa <= 0.0 ||
        !rp_isfinite(throat_temperature) || throat_temperature <= minimum_temperature) {
        return 0;
    }
    if (rp_root_bisect(pressure_equation, &equation, minimum_temperature,
                       throat_temperature, policy, &root, NULL) != RP_OK) {
        return 0;
    }
    if (flow_station(context, root.x, &station, NULL) != RP_OK ||
        station.mass_flux_kg_per_m2_s <= 0.0) {
        return 0;
    }
    ratio = context->throat_flux / station.mass_flux_kg_per_m2_s;
    if (!rp_isfinite(ratio) || ratio < 1.0 || ratio > 1e4) { return 0; }
    *area_ratio = ratio;
    return 1;
}

static double area_equation(double temperature, const void *opaque)
{
    const FrozenContext *context = opaque;
    RpFrozenFlowStation station = {0};
    if (flow_station(context, temperature, &station, NULL) != RP_OK || station.mass_flux_kg_per_m2_s <= 0.0) { return NAN; }
    return station.mass_flux_kg_per_m2_s * context->area_ratio / context->throat_flux - 1.0;
}

RpStatus rp_nozzle_solve_frozen(const RpFrozenNozzleInput *input,
                                const RpRootOptions *options,
                                RpFrozenNozzleResult *output, RpError *error)
{
    const RpRootOptions defaults = {1e-8, 1e-12, 1e-11, 200U};
    const RpRootOptions policy = options != NULL ? *options : defaults;
    RpFrozenNozzleResult result = {0};
    FrozenContext context = {0};
    RpRootResult root;
    RpStatus status;
    double minimum_temperature = 0.0;
    if (input == NULL || output == NULL || !rp_isfinite(input->area_ratio) || input->area_ratio < 1.0 ||
        input->area_ratio > 1e4 || !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid frozen nozzle input, area ratio or ambient pressure.");
    }
    status = rp_cho_mixture_evaluate(input->mole_fractions, input->chamber_temperature_k,
                                     input->chamber_pressure_pa, &context.chamber, error);
    if (status != RP_OK) { return status; }
    minimum_temperature = rp_cho_minimum_temperature(input->mole_fractions);
    if (input->chamber_temperature_k <= minimum_temperature) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "No frozen expansion interval inside the NASA9 temperature domain.");
    }
    status = rp_root_bisect(sonic_equation, &context, minimum_temperature, input->chamber_temperature_k, &policy, &root, error);
    if (status != RP_OK) { return status; }
    status = flow_station(&context, root.x, &result.throat, error);
    if (status != RP_OK) { return status; }
    context.throat_flux = result.throat.mass_flux_kg_per_m2_s;
    context.area_ratio = input->area_ratio;
    if (input->area_ratio == 1.0) { result.exit = result.throat; }
    else {
        status = rp_root_bisect(area_equation, &context, minimum_temperature, root.x, &policy, &root, error);
        if (status != RP_OK) { return status; }
        status = flow_station(&context, root.x, &result.exit, error);
        if (status != RP_OK) { return status; }
    }
    if (input->ambient_pressure_pa > result.exit.gas.pressure_pa) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Overexpanded frozen nozzle is outside the supported no-shock domain.");
    }
    result.chamber = context.chamber;
    result.cstar_m_per_s = input->chamber_pressure_pa / context.throat_flux;
    result.vacuum_effective_velocity_m_per_s = result.exit.velocity_m_per_s +
        result.exit.gas.pressure_pa * input->area_ratio / context.throat_flux;
    result.effective_velocity_m_per_s = result.exit.velocity_m_per_s +
        (result.exit.gas.pressure_pa - input->ambient_pressure_pa) * input->area_ratio / context.throat_flux;
    result.thrust_coefficient = result.effective_velocity_m_per_s / result.cstar_m_per_s;
    result.continuity_relative_residual = area_equation(result.exit.gas.temperature_k, &context);
    result.sonic_relative_residual = result.throat.mach * result.throat.mach - 1.0;
    if (!rp_isfinite(result.cstar_m_per_s) || result.cstar_m_per_s <= 0.0 ||
        !rp_isfinite(result.effective_velocity_m_per_s) || result.effective_velocity_m_per_s <= 0.0 ||
        !rp_isfinite(result.vacuum_effective_velocity_m_per_s) || !rp_isfinite(result.thrust_coefficient) ||
        !rp_isfinite(result.continuity_relative_residual) || !rp_isfinite(result.sonic_relative_residual)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite frozen nozzle output.");
    }
    if (fabs(result.continuity_relative_residual) > 1e-8 || fabs(result.sonic_relative_residual) > 1e-8 ||
        fabs(result.exit.energy_residual_j_per_kg) > 1e-5 || fabs(result.throat.energy_residual_j_per_kg) > 1e-5 ||
        fabs(result.exit.entropy_residual_j_per_kg_k) > 1e-7 || fabs(result.throat.entropy_residual_j_per_kg_k) > 1e-7 ||
        result.exit.mach < 1.0 - 1e-8) {
        return rp_error_set(error, RP_NO_CONVERGENCE, "Frozen nozzle physical residual exceeds tolerance.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_nozzle_solve_frozen_fixed_area(const RpFrozenNozzleInput *input,
                                           double throat_area_m2,
                                           const RpRootOptions *options,
                                           RpFrozenNozzleFixedResult *output,
                                           RpError *error)
{
    RpFrozenNozzleFixedResult result = {0};
    RpStatus status;
    if (output == NULL || !rp_isfinite(throat_area_m2) || throat_area_m2 <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Fixed throat area must be finite and positive.");
    }
    status = rp_nozzle_solve_frozen(input, options, &result.nozzle, error);
    if (status != RP_OK) { return status; }
    result.throat_area_m2 = throat_area_m2;
    result.exit_area_m2 = throat_area_m2 * input->area_ratio;
    result.mass_flow_kg_per_s = throat_area_m2 * result.nozzle.throat.mass_flux_kg_per_m2_s;
    result.thrust_n = result.mass_flow_kg_per_s * result.nozzle.effective_velocity_m_per_s;
    result.specific_impulse_s = result.nozzle.effective_velocity_m_per_s / RP_STANDARD_GRAVITY_M_S2;
    if (!rp_isfinite(result.exit_area_m2) || result.exit_area_m2 <= 0.0 ||
        !rp_isfinite(result.mass_flow_kg_per_s) || result.mass_flow_kg_per_s <= 0.0 ||
        !rp_isfinite(result.thrust_n) || result.thrust_n <= 0.0 ||
        !rp_isfinite(result.specific_impulse_s) || result.specific_impulse_s <= 0.0) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Fixed-geometry nozzle dimensions or performance overflow/underflow.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_nozzle_assess_frozen(const RpFrozenNozzleInput *input,
                                 double throat_area_m2,
                                 const RpRootOptions *options,
                                 RpFrozenNozzleRegimeResult *output,
                                 RpError *error)
{
    const RpRootOptions defaults = {1e-8, 1e-12, 1e-11, 200U};
    const RpRootOptions policy = options != NULL ? *options : defaults;
    RpFrozenNozzleRegimeResult result = {0};
    RpFrozenNozzleInput attached;
    FrozenContext context = {0};
    RpStatus status;
    double minimum_temperature;
    double throat_temperature;
    double effective_velocity;
    if (input == NULL || output == NULL ||
        !rp_isfinite(throat_area_m2) || throat_area_m2 <= 0.0 ||
        !rp_isfinite(input->ambient_pressure_pa) || input->ambient_pressure_pa < 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT,
                            "Frozen regime requires positive throat area and finite non-negative ambient pressure.");
    }
    attached = *input;
    attached.ambient_pressure_pa = 0.0;
    status = rp_nozzle_solve_frozen(&attached, &policy, &result.ideal, error);
    if (status != RP_OK) { return status; }
    context.chamber = result.ideal.chamber;
    context.throat_flux = result.ideal.throat.mass_flux_kg_per_m2_s;
    context.area_ratio = input->area_ratio;
    minimum_temperature = rp_cho_minimum_temperature(input->mole_fractions);
    throat_temperature = result.ideal.throat.gas.temperature_k;
    result.throat_area_m2 = throat_area_m2;
    result.mass_flow_kg_per_s = throat_area_m2 * context.throat_flux;
    effective_velocity = result.ideal.exit.velocity_m_per_s +
        (result.ideal.exit.gas.pressure_pa - input->ambient_pressure_pa) *
        input->area_ratio / context.throat_flux;
    result.ideal_thrust_n = result.mass_flow_kg_per_s * effective_velocity;
    result.ideal_specific_impulse_s = effective_velocity / RP_STANDARD_GRAVITY_M_S2;
    result.ambient_over_exit_pressure =
        input->ambient_pressure_pa / result.ideal.exit.gas.pressure_pa;
    result.separation_reference_pa = RP_NOZZLE_SEPARATION_FRACTION * input->ambient_pressure_pa;
    result.matched_area_ratio_available = area_ratio_for_pressure(
        &context, minimum_temperature, throat_temperature,
        input->ambient_pressure_pa, &policy, &result.matched_area_ratio);
    result.separation_area_ratio_available = area_ratio_for_pressure(
        &context, minimum_temperature, throat_temperature,
        result.separation_reference_pa, &policy, &result.separation_area_ratio);
    if (input->ambient_pressure_pa <= result.ideal.exit.gas.pressure_pa) {
        result.regime = RP_NOZZLE_REGIME_IDEAL_DOMAIN;
    } else if (result.ideal.exit.gas.pressure_pa >= result.separation_reference_pa) {
        result.regime = RP_NOZZLE_REGIME_OVEREXPANDED_POSSIBLE;
    } else {
        result.regime = RP_NOZZLE_REGIME_SEPARATION_HINT;
    }
    if (!rp_isfinite(result.mass_flow_kg_per_s) || result.mass_flow_kg_per_s <= 0.0 ||
        !rp_isfinite(result.ideal_thrust_n) || !rp_isfinite(result.ideal_specific_impulse_s) ||
        !rp_isfinite(result.ambient_over_exit_pressure) || result.ambient_over_exit_pressure < 0.0 ||
        (result.matched_area_ratio_available && !rp_isfinite(result.matched_area_ratio)) ||
        (result.separation_area_ratio_available && !rp_isfinite(result.separation_area_ratio))) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite frozen nozzle regime output.");
    }
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
