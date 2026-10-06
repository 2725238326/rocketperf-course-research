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

#endif
