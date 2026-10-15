#ifndef ROCKETPERF_ENGINE_CYCLE_H
#define ROCKETPERF_ENGINE_CYCLE_H

#include "rocketperf/cycle.h"

#include <stdbool.h>

#define RP_ADIABATIC_CYCLE_MODEL "adiabatic_single_shaft_cycle_v1"

/* Explicit propellant inventories, including zero amounts for absent elements.
 * The pump properties describe its inlet, not an inferred post-pump EOS state. */
typedef struct {
    RpLiquidPumpInput pump;
    double elements_kmol_per_kg[RP_CHO_ELEMENT_COUNT];
    RpEnthalpyBasis basis;
} RpCyclePropellant;

/**
 * 发动机循环输入参数
 *
 * 描述液体火箭发动机的热力循环（燃气发生器或补燃循环）。
 * 所有推进剂流量、压力、效率均为设计点参数。
 */
typedef struct {
    bool staged_combustion;              /* [-] false=燃气发生器循环(GG), true=富氧补燃循环(ORSC) */
    double total_mass_flow_kg_per_s;     /* [kg/s] 总推进剂流量，有限且>0 */
    double overall_oxidizer_fuel_ratio;  /* [-] 总体氧燃比(O/F)，有限且>0；另受HP/分流约束 */
    RpCyclePropellant fuel;              /* 燃料属性（元素组成+泵入口状态） */
    RpCyclePropellant oxidizer;          /* 氧化剂属性（元素组成+泵入口状态） */
    double chamber_pressure_pa;          /* [Pa] 数值接收100..1e9；物理适用性另行核验 */
    double main_area_ratio;              /* [-] 主喷管面积比 Ae/At，范围 1-1e4 */
    double preburner_pressure_pa;        /* [Pa] 数值接收100..1e9，另受供给/回流约束 */
    double preburner_oxidizer_fuel_ratio;/* [-] 预燃室氧燃比，GG典型0.5-2，ORSC需>overall_O/F */
    double turbine_outlet_pressure_pa;   /* [Pa] 涡轮出口压力（GG必须>0，ORSC必须=0自动求解） */
    double turbine_efficiency;           /* [-] 涡轮等熵效率，有限且0<eta<=1 */
    double shaft_efficiency;             /* [-] 轴传动效率，有限且0<eta<=1 */
    double auxiliary_power_w;            /* [W] 辅助功率消耗（发电机等），≥0 */
    double maximum_branch_fraction;      /* [-] 最大分流比，有限且0<f<1 */
    double pump_to_chamber_drop_pa;      /* [Pa] 泵出口到主燃烧室管路损失，≥0 */
    double pump_to_preburner_drop_pa;    /* [Pa] 泵出口到预燃室管路损失，≥0 */
    double return_pressure_drop_pa;      /* [Pa] 回流压降：ORSC有限且>=0，GG必须=0 */
    double branch_area_ratio;            /* [-] 分支喷管面积比（GG燃气排气，ORSC必须=1） */
    double branch_axial_projection;      /* [-] 分支喷管轴向投影比（ORSC必须=0） */
    double ambient_pressure_pa;          /* [Pa] 有限且>=0；各喷管另检查背压适用域 */
} RpEngineCycleInput;

/**
 * 发动机循环计算结果
 *
 * 包含推力性能、燃烧状态和收敛诊断信息。
 */
typedef struct {
    RpCycleResult balance;                /* 循环平衡结果（推力、比冲、流量分配） */
    RpCombustionResult preburner;         /* 预燃室燃烧平衡态 */
    RpCombustionResult chamber;           /* 主燃烧室燃烧平衡态 */
    double main_inlet_h_j_per_kg;         /* [J/kg] 主燃烧室入口混合物比焓 */
    double main_elements_kmol_per_kg[RP_CHO_ELEMENT_COUNT]; /* [kmol/kg] 主燃烧室元素库存(C,H,O) */
    double preburner_enthalpy_residual_w; /* [W] 预燃室焓守恒残差（功率单位） */
    double chamber_enthalpy_residual_w;   /* [W] 主燃烧室焓守恒残差（功率单位） */
    double exit_element_relative_residual[RP_CHO_ELEMENT_COUNT]; /* [-] 出口元素守恒相对残差 */
    unsigned int turbine_pressure_iterations; /* [-] 涡轮压力迭代次数（ORSC循环） */
} RpEngineCycleResult;

/* Single implementation file: src/cycle/adiabatic.c. Pure C17, no I/O/heap.
 * GG: HP preburner -> frozen turbine at declared p_out -> shaft-derived branch.
 * ORSC: all oxidizer -> HP preburner; fuel is diverted at declared preburner OF.
 *       Turbine p_out is solved from shaft load above chamber p + return drop.
 *       Frozen returned-gas elements/h plus fresh fuel -> main HP, no extra LHV.
 * Two constant-density pumps share a shaft; pump work enters the fluid once.
 * Q_preburner=Q_chamber=0; mechanical loss leaves as heat, aux is exported work.
 * Mass flow sets nozzle sizing, not a fixed-hardware operating point. Products
 * remain restricted nine-gas CHO, with both HP temperatures in 1000..6000 K.
 * Core input is a declared research model, not a calibrated engine card.
 * Pump mass_flow overrides must be zero. Every failure preserves output. */
RpStatus rp_engine_cycle_solve(const RpEngineCycleInput *input,
                                const RpCombustionOptions *combustion_options,
                                const RpRootOptions *root_options,
                                RpEngineCycleResult *output, RpError *error);

#endif
