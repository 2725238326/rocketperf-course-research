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

typedef struct {
    bool staged_combustion; /* false: GG external exhaust; true: all-O ORSC. */
    double total_mass_flow_kg_per_s;
    double overall_oxidizer_fuel_ratio;
    RpCyclePropellant fuel;
    RpCyclePropellant oxidizer;
    double chamber_pressure_pa;
    double main_area_ratio;
    double preburner_pressure_pa;
    double preburner_oxidizer_fuel_ratio;
    double turbine_outlet_pressure_pa; /* GG only; must be zero for ORSC. */
    double turbine_efficiency;
    double shaft_efficiency;
    double auxiliary_power_w;
    double maximum_branch_fraction;
    double pump_to_chamber_drop_pa;
    double pump_to_preburner_drop_pa;
    double return_pressure_drop_pa; /* ORSC only; must be zero for GG. */
    double branch_area_ratio;       /* Must be 1 for inactive ORSC exhaust. */
    double branch_axial_projection; /* Must be 0 for ORSC. */
    double ambient_pressure_pa;
} RpEngineCycleInput;

typedef struct {
    RpCycleResult balance;
    RpCombustionResult preburner;
    RpCombustionResult chamber;
    double main_inlet_h_j_per_kg;
    double main_elements_kmol_per_kg[RP_CHO_ELEMENT_COUNT];
    double preburner_enthalpy_residual_w;
    double chamber_enthalpy_residual_w;
    double exit_element_relative_residual[RP_CHO_ELEMENT_COUNT];
    unsigned int turbine_pressure_iterations;
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
