#ifndef ROCKETPERF_LIQUID_FEED_H
#define ROCKETPERF_LIQUID_FEED_H

#include "rocketperf/status.h"

typedef enum {
    RP_LIQUID_GAS = 0,
    RP_LIQUID_SINGLE_PHASE = 1,
    RP_LIQUID_TWO_PHASE = 2
} RpLiquidFeedPhase;

typedef struct {
    const char *dataset_id;
    const char *fluid_id;
    RpLiquidFeedPhase phase;
    double temperature_k;
    double pressure_pa;
} RpLiquidFeedQuery;

typedef struct {
    double density_kg_per_m3;
    double h_j_per_mol;
    double h_j_per_kg;
    double eos_molar_mass_kg_per_mol;
    double chemical_molar_mass_kg_per_mol;
} RpLiquidFeedState;

/* Pinned offline reference only: Methane 100..140 K, Oxygen 80..110 K,
 * both 1..20 MPa, endpoints included. Bilinear interpolation; no extrapolation.
 * Accepts only the returned dataset ID and RP_LIQUID_SINGLE_PHASE.
 * Density retains the EOS mass convention. Enthalpy retains HEOS temperature/
 * pressure dependence and its residual term, with the CEA/NASA9 ideal zero at
 * 298.15 K. Mass enthalpy uses the pinned CEA molar mass, explicitly returned.
 * No phase flash, pump, combustion or cycle closure. Every failure preserves
 * output. Repeated calls require no I/O, allocation or mutable global state. */
const char *rp_liquid_feed_dataset_id(void);
const char *rp_liquid_feed_enthalpy_basis_id(void);
const char *rp_liquid_feed_reference_sha256(void);
RpStatus rp_liquid_feed_evaluate(const RpLiquidFeedQuery *query,
                                  RpLiquidFeedState *output, RpError *error);

#endif
