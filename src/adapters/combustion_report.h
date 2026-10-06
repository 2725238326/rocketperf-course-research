#ifndef ROCKETPERF_COMBUSTION_REPORT_H
#define ROCKETPERF_COMBUSTION_REPORT_H

#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/liquid_feed.h"
#include "propellant_case.h"
#include <stdio.h>

/* JSON fragments for already solved states. Returns zero on output failure. */
int rp_report_write_mixture(FILE *stream, const RpGasMixture *gas);
int rp_report_write_diagnostics(FILE *stream, const RpCombustionResult *result);
int rp_report_write_station(FILE *stream, const RpFrozenFlowStation *station);
int rp_report_write_frozen_report(FILE *stream, const RpFrozenNozzleResult *nozzle);
int rp_report_write_fixed_geometry(FILE *stream, const RpFrozenNozzleFixedResult *geometry);
int rp_report_write_liquid_state(FILE *stream, const RpLiquidFeedState *state);
int rp_report_write_propellant(FILE *stream, const RpPropellantComparisonInput *input,
                               const RpPropellantComparisonResult *result,
                               const RpPropellantCase *study);

#endif
