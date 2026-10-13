#ifndef ROCKETPERF_NOZZLE_H
#define ROCKETPERF_NOZZLE_H

#include "rocketperf/root.h"

#include <stddef.h>

/**
 * 喷管求解输入参数
 *
 * 所有单位为SI基本单位。理想气体假设，比热比γ为常数。
 */
typedef struct {
    double gamma;                      /* [-] 比热比 cp/cv，范围 (1.0, 2.0]，燃气典型 1.15-1.40 */
    double gas_constant_j_kg_k;        /* [J/(kg·K)] 比气体常数 R = R_universal / M */
    double stagnation_temperature_k;   /* [K] 滞止温度（喉部上游总温），NASA9 范围 300-6000 K */
    double stagnation_pressure_pa;     /* [Pa] 滞止压力（喉部上游总压），需 > 0 */
    double area_ratio;                 /* [-] 面积比 Ae/At，范围 [1.0, 1e4]，典型 2-100 */
    double throat_area_m2;             /* [m²] 喉部面积 At，需 > 0 */
    double ambient_pressure_pa;        /* [Pa] 背压/环境压力，≥ 0；超膨胀时（pa > pe）求解拒绝 */
} RpNozzleInput;

/**
 * 喷管求解输出结果
 *
 * 出口参数基于理想冻结膨胀。推力包含压力项（pe-pa）·Ae。
 */
typedef struct {
    double exit_mach;                  /* [-] 出口马赫数 Me，超音速膨胀通常 Me > 1 */
    double exit_temperature_k;         /* [K] 出口静温 Te = T0 / (1 + (γ-1)/2 · Me²) */
    double exit_pressure_pa;           /* [Pa] 出口静压 pe，等熵膨胀计算 */
    double exit_velocity_m_s;          /* [m/s] 出口速度 ue = Me · √(γ R Te) */
    double exit_area_m2;               /* [m²] 出口面积 Ae = At · (Ae/At) */
    double characteristic_velocity_m_s;/* [m/s] 特征速度 c* = Pc·At/ṁ，反映燃烧室效率 */
    double mass_flow_kg_s;             /* [kg/s] 质量流量 ṁ = Pc·At/c*，喉部阻塞流 */
    double thrust_n;                   /* [N] 推力 F = ṁ·ue + (pe-pa)·Ae */
    double thrust_coefficient;         /* [-] 推力系数 CF = F / (Pc·At) */
    double specific_impulse_s;         /* [s] 比冲 Isp = F / (ṁ·g0)，g0 = 9.80665 m/s² */
    double relative_area_residual;     /* [-] 面积方程残差（相对值），收敛检查用 */
    unsigned int root_iterations;      /* [-] 求根迭代次数 */
} RpNozzleResult;

typedef struct {
    double area_ratio;
    double ambient_pressure_pa;
    RpStatus status;
    RpNozzleResult result;
    char message[192];
} RpNozzleStudyPoint;

typedef struct {
    const double *area_ratios;
    size_t area_ratio_count;
    const double *ambient_pressures_pa;
    size_t ambient_pressure_count;
} RpNozzleStudyGrid;

/* Flow-regime classification for back pressures the attached solver rejects.
 * OVEREXPANDED_POSSIBLE is a mild-overexpansion band below the empirical
 * separation reference; SEPARATION_HINT means the Summerfield-type reference
 * (exit pressure below ~0.4*ambient) is crossed. Both are diagnostics about
 * model applicability, never a separation/flow prediction. */
typedef enum {
    RP_NOZZLE_REGIME_IDEAL_DOMAIN = 0,
    RP_NOZZLE_REGIME_OVEREXPANDED_POSSIBLE,
    RP_NOZZLE_REGIME_SEPARATION_HINT
} RpNozzleRegime;

/* Summerfield-type empirical boundary: attached isentropic flow is not
 * expected once the ideal exit pressure falls below this fraction of the
 * ambient pressure. Diagnostic hint only; real separation is not modeled. */
#define RP_NOZZLE_SEPARATION_FRACTION 0.4

typedef struct {
    RpNozzleRegime regime;
    RpNozzleResult ideal;                    /* Attached isentropic solve (ambient ignored). */
    double thrust_n;                         /* Ideal formula with actual ambient, incl. negative pressure term. */
    double ambient_over_exit_pressure;       /* pa/pe. */
    double separation_reference_pa;          /* 0.4*pa empirical reference wall pressure, hint only. */
    int separation_area_ratio_available;
    double separation_area_ratio;            /* Isentropic station area ratio where p = 0.4*pa. */
    int matched_area_ratio_available;
    double matched_area_ratio;               /* Ae/At that would give pe == pa. */
} RpNozzleRegimeResult;

const char *rp_nozzle_regime_name(RpNozzleRegime regime);

/* Answers "what does the ideal model say beyond its attached domain": still
 * solves the isentropic expansion (pe is ambient-independent), then reports
 * pressure ratios, the empirical separation reference and the area ratios
 * that would match pa or reach the separation reference. Reference area ratios
 * are available only within the forward solver's range [1, 1e4]; otherwise
 * their availability flag is zero and their stored value is zero. Input validation
 * matches rp_nozzle_solve_ideal except ambient pressure may exceed pe.
 * Output unchanged on failure; no allocation, I/O or global mutable state. */
RpStatus rp_nozzle_assess_ideal(const RpNozzleInput *input,
                                const RpRootOptions *options,
                                RpNozzleRegimeResult *output, RpError *error);

/* Reservoir-to-exit, calorically perfect gas, sonic throat, supersonic branch.
 * Initial validated domain: 1 < gamma <= 2; 1 <= Ae/At <= 1e4;
 * ambient pressure <= ideal exit pressure (matched/underexpanded).
 * No chemistry, losses, shocks, separation, cooling, cycle or reuse model.
 * Output is unchanged on failure. No allocation, I/O or global mutable state. */
RpStatus rp_nozzle_solve_ideal(const RpNozzleInput *input,
                             const RpRootOptions *options,
                             RpNozzleResult *output, RpError *error);

/* Evaluate a Cartesian area-ratio/back-pressure grid using the same L0 model.
 * Grid points outside the model domain are retained as diagnostics rather than
 * aborting the complete study. Invalid grid storage or non-finite grid values
 * still fail the call without writing points. If point_count is non-NULL, it
 * is reset to zero on entry. RP_OK means the grid was evaluated, not that every
 * point succeeded; callers must inspect statuses (numeric failures are not
 * expected domain exclusions). Output points are written in row-major order:
 * area ratio outer loop, ambient pressure inner loop. */
RpStatus rp_nozzle_scan_area_ratio_ambient(const RpNozzleInput *base,
                                           const RpNozzleStudyGrid *grid,
                                           RpNozzleStudyPoint *points,
                                           size_t point_capacity,
                                           size_t *point_count,
                                           RpError *error);

#endif
