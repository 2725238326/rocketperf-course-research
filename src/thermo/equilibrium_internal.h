#ifndef RP_EQUILIBRIUM_INTERNAL_H
#define RP_EQUILIBRIUM_INTERNAL_H

#include "rocketperf/combustion.h"

/* Internal adapter, not an unrestricted user-supplied thermodynamic model.
 * Feed builders supply positive CEA-basis elemental amounts per kg and total h.
 * Elemental mass must sum to one kg (absolute tolerance 1e-10 kg/kg);
 * common scaling of the inventory is not silently normalized away.
 * All public gas and fixed-anchor APIs retain their separate inlet guards. */
RpStatus rp_cho_equilibrium_hp_inventory(
    double pressure_pa,
    const double element_inventory_kmol_per_kg[RP_CHO_ELEMENT_COUNT],
    double feed_enthalpy_j_per_kg,
    const RpCombustionOptions *options,
    RpCombustionResult *output, RpError *error);

#endif
