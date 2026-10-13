#ifndef ROCKETPERF_COMBUSTION_H
#define ROCKETPERF_COMBUSTION_H

#include "rocketperf/thermo.h"

#define RP_CHO_SPECIES_COUNT 9U
#define RP_CHO_ELEMENT_COUNT 3U

typedef enum { RP_FEED_GAS = 0, RP_FEED_LIQUID = 1 } RpFeedPhase;
typedef struct {
    double pressure_pa;
    double oxidizer_fuel_mass_ratio;
    double fuel_temperature_k;
    double oxidizer_temperature_k;
    RpFeedPhase phase;
} RpCh4O2Feed;
typedef enum {
    RP_ENTHALPY_UNSPECIFIED = 0,
    RP_ENTHALPY_NASA9_CEA_V334 = 1
} RpEnthalpyBasis;
typedef struct {
    double pressure_pa;
    double oxidizer_fuel_mass_ratio;
    double fuel_h_j_per_kg;
    double oxidizer_h_j_per_kg;
    RpFeedPhase phase;
    RpEnthalpyBasis basis;
} RpCh4O2EnthalpyFeed;
typedef struct {
    double pressure_pa;
    double oxidizer_fuel_mass_ratio;
    const char *fuel_anchor_id;
    const char *oxidizer_anchor_id;
    double fuel_temperature_k;
    double oxidizer_temperature_k;
    RpFeedPhase phase;
} RpAssignedReactantFeed;
typedef RpAssignedReactantFeed RpCh4O2AnchorFeed;
typedef struct {
    const char *dataset_id;
    RpAssignedReactantFeed reactants;
} RpKeroseneAnchorFeed;
typedef struct {
    double fuel_h_j_per_kg;
    double oxidizer_h_j_per_kg;
    double mixture_h_j_per_kg;
    double element_inventory_kmol_per_kg[RP_CHO_ELEMENT_COUNT];
} RpAnchorInlet;
/**
 * 化学平衡求解器配置参数
 */
typedef struct {
    double equilibrium_tolerance;          /* [-] 平衡残差收敛阈值，范围 [1e-13, 1e-8]，典型 1e-10 */
    double enthalpy_tolerance_j_per_kg;    /* [J/kg] HP模式焓收敛阈值，范围 (0, 1]，典型 0.01 */
    double hp_lower_temperature_k;         /* [K] HP二分下界，≥1000 K（NASA9下限） */
    double hp_upper_temperature_k;         /* [K] HP二分上界，≤6000 K（NASA9上限） */
    unsigned int max_equilibrium_iterations; /* [-] TP迭代上限，范围 [1, 10000]，典型 400 */
    unsigned int max_hp_iterations;        /* [-] HP外层迭代上限，范围 [1, 1000]，典型 80 */
} RpCombustionOptions;
/**
 * 气体混合物热力学状态
 *
 * 基于化学平衡计算（9个C-H-O物种），理想气体假设。
 */
typedef struct {
    double temperature_k;                  /* [K] 温度，范围 1000-6000 K */
    double pressure_pa;                    /* [Pa] 压力，范围 100 Pa - 1e9 Pa */
    double mole_fractions[RP_CHO_SPECIES_COUNT]; /* [-] 摩尔分数 xi，Σxi = 1，顺序见注释 */
    double molar_mass_kg_per_kmol;         /* [kg/kmol] 混合物平均摩尔质量 M = Σ(xi·Mi) */
    double gas_constant_j_per_kg_k;        /* [J/(kg·K)] 比气体常数 R = R_universal / M */
    double cp_frozen_j_per_kg_k;           /* [J/(kg·K)] 冻结比热 cp，成分不变时的热容 */
    double h_j_per_kg;                     /* [J/kg] 比焓，相对于NASA9参考态（元素298.15K） */
    double s_j_per_kg_k;                   /* [J/(kg·K)] 比熵，包含化学贡献和热贡献 */
} RpGasMixture;

/**
 * 化学平衡计算结果
 *
 * 包含平衡态热力学性质和收敛诊断信息。
 */
typedef struct {
    RpGasMixture gas;                      /* 平衡态混合物性质 */
    double element_relative_residual[RP_CHO_ELEMENT_COUNT]; /* [-] 元素守恒相对残差（C, H, O） */
    double equilibrium_residual;           /* [-] 平衡方程残差（最大分量）*/
    double enthalpy_residual_j_per_kg;     /* [J/kg] 焓残差（HP模式），TP模式时非零 */
    unsigned int equilibrium_iterations;   /* [-] TP迭代次数（最终温度的迭代，不含HP试探） */
    unsigned int hp_iterations;            /* [-] HP外层迭代次数（温度二分次数） */
} RpCombustionResult;

/* Fixed order: H2 O2 H2O CO CO2 CH4 H O OH; elements: C H O.
 * Ideal gas only. Numerical bounds: T=1000..6000 K, p=100..1e9 Pa, O/F=0.1..20.
 * These are guards, not a certified ideal-gas or gas-phase stability envelope.
 * enthalpy_residual is generally nonzero for TP; HP enforces its tolerance.
 * equilibrium_iterations counts the final TP continuation, not all HP calls.
 * NULL options uses defaults. Every failure leaves output unchanged. */
const char *rp_cho_species_id(unsigned int index);
unsigned int rp_cho_element_count(unsigned int species, unsigned int element);
RpCombustionOptions rp_combustion_default_options(void);
RpStatus rp_cho_mixture_evaluate(const double mole_fractions[RP_CHO_SPECIES_COUNT],
                                 double temperature_k, double pressure_pa,
                                 RpGasMixture *output, RpError *error);
RpStatus rp_ch4_o2_feed_enthalpy(const RpCh4O2Feed *feed, double *output, RpError *error);
RpStatus rp_ch4_o2_equilibrium_tp(const RpCh4O2Feed *feed, double temperature_k,
                                  const RpCombustionOptions *options,
                                  RpCombustionResult *output, RpError *error);
RpStatus rp_ch4_o2_equilibrium_hp(const RpCh4O2Feed *feed,
                                  const RpCombustionOptions *options,
                                  RpCombustionResult *output, RpError *error);

/* Independent explicit-enthalpy gas inlet, not a liquid-property adapter.
 * Both pure-species enthalpies include formation enthalpy on the pinned NASA9
 * CEA v3.3.4 basis, and must lie within each gas fit's 200..6000 K h interval.
 * basis is a caller assertion, not proof of provenance or phase stability.
 * Pressure/O/F guards match equilibrium above. No inlet T is invented.
 * HP solves h_products(T,p) = (h_CH4 + O/F*h_O2)/(1+O/F); Q=0, no inlet KE.
 * NULL options uses defaults. Every failure leaves output unchanged. */
RpStatus rp_ch4_o2_inlet_enthalpy(const RpCh4O2EnthalpyFeed *feed,
                                  double *output, RpError *error);
RpStatus rp_ch4_o2_equilibrium_hp_enthalpy(const RpCh4O2EnthalpyFeed *feed,
                                          const RpCombustionOptions *options,
                                          RpCombustionResult *output, RpError *error);

/* Pinned CEA CH4(L) at exactly 111.643 K and O2(L) at exactly 90.170 K.
 * Assigned chemical enthalpies include formation contributions. No caller h
 * override, NASA9 extrapolation, liquid EOS/density or pressure correction.
 * pressure_pa is product chamber pressure, not a measured liquid inlet pressure.
 * Only those IDs and RP_FEED_LIQUID are accepted. Same p/O-F and HP guards.
 * Products remain restricted ideal gases. No pump, phase-stability or cycle solve.
 * NULL options uses defaults. Every failure leaves output unchanged. */
const char *rp_anchor_dataset_id(void);
RpStatus rp_ch4_o2_anchor_inlet(const RpCh4O2AnchorFeed *feed,
                                RpAnchorInlet *output, RpError *error);
RpStatus rp_ch4_o2_equilibrium_hp_anchor(const RpCh4O2AnchorFeed *feed,
                                         const RpCombustionOptions *options,
                                         RpCombustionResult *output, RpError *error);

/* Fixed RP-1 C1H1.95 at 298.15 K with O2(L)90.170 K, Q=0.
 * Method domain: product pressure exactly 10 MPa, O/F=2.2..4.0.
 * This is an assigned-reactant model, not a Chinese kerosene batch or EOS.
 * Nine neutral ideal-gas products; no condensed carbon or pressure correction.
 * Requires pinned dataset/IDs and liquid phase. No arbitrary h override.
 * Failure leaves output unchanged; NULL options uses the existing HP defaults. */
const char *rp_kerosene_dataset_id(void);
RpStatus rp_kerosene_anchor_inlet(const RpKeroseneAnchorFeed *feed,
                                  RpAnchorInlet *output, RpError *error);
RpStatus rp_kerosene_equilibrium_hp_anchor(const RpKeroseneAnchorFeed *feed,
                                          const RpCombustionOptions *options,
                                          RpCombustionResult *output, RpError *error);

/* Mixed fresh/returned streams on the pinned chemical mass and enthalpy basis.
 * Inventory must describe one kg of C/H/O material; positive C, H and O are
 * required. The basis is an explicit caller assertion, not phase/provenance
 * validation. Products: nine neutral ideal gases, T=1000..6000 K, p=100..1e9 Pa.
 * This distinct interface does not broaden the fixed RP-1 anchor method domain.
 * No liquid flash, condensed carbon or unrestricted fuel-property evaluation.
 * Every failure leaves output unchanged; NULL options uses HP defaults. */
typedef struct {
    double pressure_pa;
    double h_j_per_kg;
    double elements_kmol_per_kg[RP_CHO_ELEMENT_COUNT];
    RpEnthalpyBasis basis;
} RpChoMixedFeed;
RpStatus rp_cho_equilibrium_hp_mixed(const RpChoMixedFeed *feed,
                                     const RpCombustionOptions *options,
                                     RpCombustionResult *output, RpError *error);

#endif
