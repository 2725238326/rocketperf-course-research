#ifndef ROCKETPERF_PROPELLANT_STUDY_H
#define ROCKETPERF_PROPELLANT_STUDY_H

#include "rocketperf/liquid_nozzle.h"

typedef struct {
    RpContinuousLiquidFeed methane;
    RpKeroseneAnchorFeed kerosene;
    double area_ratio;
    double ambient_pressure_pa;
    double throat_area_m2;
} RpPropellantComparisonInput;

typedef struct {
    RpAnchorInlet inlet;
    RpCombustionResult chamber;
    RpFrozenNozzleFixedResult nozzle;
} RpAssignedFixedResult;

typedef struct {
    RpContinuousLiquidFixedResult methane;
    RpAssignedFixedResult kerosene;
    double methane_minus_kerosene_thrust_n;
    double methane_minus_kerosene_isp_s;
    double methane_minus_kerosene_mass_flow_kg_per_s;
    double methane_minus_kerosene_cstar_m_per_s;
} RpPropellantComparisonResult;

/* Same product pressure, throat area, area ratio and ambient for both methods.
 * Inlet states and O/F remain explicit, not inferred engine parameters.
 * Calls the existing C HP/frozen solvers; failure leaves the entire result unchanged.
 * No partial pair, fuel ranking, batch identification, pump or cycle closure. */
RpStatus rp_propellant_compare_fixed(const RpPropellantComparisonInput *input,
                                     const RpCombustionOptions *combustion_options,
                                     const RpRootOptions *nozzle_options,
                                     RpPropellantComparisonResult *output, RpError *error);

#endif
