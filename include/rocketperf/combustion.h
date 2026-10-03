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
typedef struct {
    double equilibrium_tolerance;
    double enthalpy_tolerance_j_per_kg;
    double hp_lower_temperature_k;
    double hp_upper_temperature_k;
    unsigned int max_equilibrium_iterations;
    unsigned int max_hp_iterations;
} RpCombustionOptions;
typedef struct {
    double temperature_k;
    double pressure_pa;
    double mole_fractions[RP_CHO_SPECIES_COUNT];
    double molar_mass_kg_per_kmol;
    double gas_constant_j_per_kg_k;
    double cp_frozen_j_per_kg_k;
    double h_j_per_kg;
    double s_j_per_kg_k;
} RpGasMixture;
typedef struct {
    RpGasMixture gas;
    double element_relative_residual[RP_CHO_ELEMENT_COUNT];
    double equilibrium_residual;
    double enthalpy_residual_j_per_kg;
    unsigned int equilibrium_iterations;
    unsigned int hp_iterations;
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

#endif
