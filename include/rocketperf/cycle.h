#ifndef ROCKETPERF_CYCLE_H
#define ROCKETPERF_CYCLE_H

#include "rocketperf/frozen_nozzle.h"

#define RP_PRESCRIBED_CYCLE_MODEL "prescribed_thermal_cycle_v1"

typedef struct {
    double mass_flow_kg_per_s;
    double density_kg_per_m3;
    double inlet_pressure_pa;
    double outlet_pressure_pa;
    double efficiency;
    double inlet_h_j_per_kg;
} RpLiquidPumpInput;

typedef struct {
    double specific_work_j_per_kg;
    double shaft_power_w;
    double outlet_h_j_per_kg;
    double energy_residual_w;
} RpLiquidPumpResult;

typedef struct {
    double temperature_k;
    double inlet_pressure_pa;
    double outlet_pressure_pa;
    double efficiency;
    double mole_fractions[RP_CHO_SPECIES_COUNT];
} RpFrozenTurbineInput;

typedef struct {
    RpGasMixture inlet;
    RpGasMixture isentropic_outlet;
    RpGasMixture outlet;
    double specific_work_j_per_kg;
    double efficiency_residual_j_per_kg;
    double entropy_generation_j_per_kg_k;
} RpFrozenTurbineResult;

/* Prescribed thermal states, constant-density feed properties and a single shaft.
 * Only externally exhausted generator gas is supported (return fields == 0).
 * The main and generator TP states use their separate CH4/O2 inventories.
 * Pump inlet enthalpies MUST use the same formation-enthalpy reference as NASA9;
 * density and enthalpy are prescribed, NOT evaluated liquid properties.
 * Heat terms are the exchange REQUIRED to maintain the prescribed temperatures,
 * not a prediction of combustion efficiency or an adiabatic cycle closure. */
typedef struct {
    double total_mass_flow_kg_per_s;
    double overall_oxidizer_fuel_ratio;
    RpLiquidPumpInput fuel_pump;
    RpLiquidPumpInput oxidizer_pump;
    double chamber_pressure_pa;
    double chamber_temperature_k;
    double main_area_ratio;
    double generator_oxidizer_fuel_ratio;
    double generator_temperature_k;
    double turbine_inlet_pressure_pa;
    double turbine_outlet_pressure_pa;
    double turbine_efficiency;
    double shaft_efficiency;
    double auxiliary_power_w;
    double maximum_branch_fraction;
    double return_fraction;             /* Reserved: nonzero is unsupported. */
    double return_pressure_drop_pa;     /* Reserved: must be zero in v1. */
    double branch_area_ratio;
    double branch_axial_projection;
    double ambient_pressure_pa;
} RpCycleInput;

typedef struct {
    RpLiquidPumpResult fuel_pump;
    RpLiquidPumpResult oxidizer_pump;
    RpFrozenTurbineResult turbine;
    RpFrozenNozzleResult main_nozzle;
    RpFrozenNozzleResult branch_nozzle;
    int branch_nozzle_active;
    double fuel_mass_flow_kg_per_s;
    double oxidizer_mass_flow_kg_per_s;
    double branch_mass_flow_kg_per_s;
    double branch_fuel_mass_flow_kg_per_s;
    double branch_oxidizer_mass_flow_kg_per_s;
    double returned_mass_flow_kg_per_s;
    double external_mass_flow_kg_per_s;
    double main_mass_flow_kg_per_s;
    double main_fuel_mass_flow_kg_per_s;
    double main_oxidizer_mass_flow_kg_per_s;
    double main_oxidizer_fuel_ratio;
    double turbine_power_w;
    double pump_power_w;
    double mechanical_loss_w;
    double generator_heat_w;
    double chamber_heat_w;
    double inlet_enthalpy_rate_w;
    double exit_total_enthalpy_rate_w;
    double main_throat_area_m2;
    double branch_throat_area_m2;
    double main_thrust_n;
    double branch_thrust_n;
    double total_thrust_n;
    double main_effective_velocity_m_per_s;
    double engine_effective_velocity_m_per_s;
    double engine_specific_impulse_s;
    double mass_residual_kg_per_s;
    double shaft_residual_w;
    double energy_residual_w;
    double mass_relative_residual;
    double shaft_relative_residual;
    double energy_relative_residual;
} RpCycleResult;

/* Adiabatic constant-density pump: all shaft input enters the fluid enthalpy.
 * Flow may be zero; positive density and eta in (0,1] are still required. */
RpStatus rp_liquid_pump_solve(const RpLiquidPumpInput *input,
                              RpLiquidPumpResult *output, RpError *error);
/* Total-to-total, ideal-gas frozen composition, eta=(h_in-h_out)/(h_in-h_out_s).
 * NULL root options uses defaults; p_out == p_in is a zero-work limit. */
RpStatus rp_frozen_turbine_solve(const RpFrozenTurbineInput *input,
                                 const RpRootOptions *options,
                                 RpFrozenTurbineResult *output, RpError *error);
/* Solves external branch mass from shaft closure; refuses starvation, nonzero
 * return, insufficient pump pressure, excessive diversion and bad residuals.
 * Pump mass_flow fields must be zero: the cycle derives them from total/OF.
 * Every failure leaves output unchanged. No I/O, allocation or external solver. */
RpStatus rp_cycle_solve_prescribed(const RpCycleInput *input,
                                   const RpRootOptions *options,
                                   RpCycleResult *output, RpError *error);

#endif
