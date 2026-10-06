/* Research driver for pinned assigned reactants, not a public fuel adapter. */
#include "rocketperf/combustion.h"
#include "rocketperf/frozen_nozzle.h"
#include "../src/thermo/equilibrium_internal.h"

#include <stdio.h>
#include <string.h>

int main(void)
{
    const double ratios[] = {0.5, 1.0, 2.2, 2.6, 3.2, 4.0};
    const double fuel_mass = 13.976183;
    const double oxidizer_mass = 31.9988;
    (void)printf("{\"scope\":\"fixed-rp1-nine-gas-research\",\"points\":[");
    for (unsigned int j = 0U; j < sizeof(ratios) / sizeof(ratios[0]); ++j) {
        const double ratio = ratios[j];
        const double f = 1.0 / (1.0 + ratio);
        const double inventory[3] = {f / fuel_mass, 1.95 * f / fuel_mass,
                                     2.0 * (1.0 - f) / oxidizer_mass};
        const double h = f * (-24717.7 * 1000.0 / fuel_mass) +
                         (1.0 - f) * (-12979.0 * 1000.0 / oxidizer_mass);
        RpCombustionResult result = {0};
        RpError error = {0};
        const RpStatus status = rp_cho_equilibrium_hp_inventory(1e7, inventory, h, NULL, &result, &error);
        (void)printf("%s{\"ratio\":%.17g,\"status\":\"%s\",\"h_feed_j_per_kg\":%.17g",
                     j == 0U ? "" : ",", ratio, rp_status_name(status), h);
        if (status == RP_OK) {
            (void)printf(",\"temperature_k\":%.17g,\"h_residual_j_per_kg\":%.17g,\"fractions\":[",
                         result.gas.temperature_k, result.enthalpy_residual_j_per_kg);
            for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
                (void)printf("%s%.17g", i == 0U ? "" : ",", result.gas.mole_fractions[i]);
            }
            (void)printf("]");
            if (ratio == 2.6) {
                RpFrozenNozzleInput input = {0};
                input.chamber_temperature_k = result.gas.temperature_k;
                input.chamber_pressure_pa = 1e7;
                (void)memcpy(input.mole_fractions, result.gas.mole_fractions, sizeof(input.mole_fractions));
                (void)printf(",\"nozzles\":[");
                for (unsigned int k = 0U; k < 2U; ++k) {
                    RpFrozenNozzleFixedResult nozzle = {0};
                    input.area_ratio = k == 0U ? 10.0 : 40.0;
                    const RpStatus ns = rp_nozzle_solve_frozen_fixed_area(&input, 0.01, NULL, &nozzle, &error);
                    (void)printf("%s{\"area_ratio\":%.17g,\"status\":\"%s\"",
                                 k == 0U ? "" : ",", input.area_ratio, rp_status_name(ns));
                    if (ns == RP_OK) {
                        (void)printf(",\"cstar_m_per_s\":%.17g,\"vacuum_velocity_m_per_s\":%.17g,"
                                     "\"mass_flow_kg_per_s\":%.17g,\"thrust_n\":%.17g,\"isp_s\":%.17g",
                                     nozzle.nozzle.cstar_m_per_s, nozzle.nozzle.vacuum_effective_velocity_m_per_s,
                                     nozzle.mass_flow_kg_per_s, nozzle.thrust_n, nozzle.specific_impulse_s);
                    }
                    (void)printf("}");
                }
                (void)printf("]");
            }
        }
        (void)printf("}");
    }
    (void)printf("]}\n");
    return ferror(stdout) ? 1 : 0;
}
