#ifndef ROCKETPERF_TEXT_REPORT_H
#define ROCKETPERF_TEXT_REPORT_H

#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/liquid_feed.h"
#include "rocketperf/liquid_nozzle.h"
#include "rocketperf/nozzle.h"
#include "rocketperf/propellant_study.h"
#include "rocketperf/thermo.h"

#include <stdio.h>

/* Human-readable report fragments for interactive and --text output.
 * Labels are UTF-8 Chinese with SI units; every writer returns zero on
 * output failure, matching the JSON fragment contract in combustion_report.h. */
int rp_text_heading(FILE *stream, const char *title);
int rp_text_note(FILE *stream, const char *text);
int rp_text_value(FILE *stream, const char *label, double value, const char *unit);
int rp_text_mixture(FILE *stream, const char *title, const RpGasMixture *gas);
int rp_text_chamber_diagnostics(FILE *stream, const RpCombustionResult *result);
int rp_text_frozen_nozzle(FILE *stream, const RpFrozenNozzleResult *nozzle);
int rp_text_fixed_geometry(FILE *stream, const RpFrozenNozzleFixedResult *geometry);
int rp_text_ideal_result(FILE *stream, const RpNozzleInput *input,
                         const RpNozzleResult *result);
int rp_text_liquid_state(FILE *stream, const char *name,
                         const RpLiquidFeedState *state);
int rp_text_thermo_state(FILE *stream, const RpNasa9Species *species,
                         double temperature_k, const RpThermoState *state);
int rp_text_propellant_comparison(FILE *stream, const RpPropellantComparisonInput *input,
                                  const RpPropellantComparisonResult *result);

#endif
