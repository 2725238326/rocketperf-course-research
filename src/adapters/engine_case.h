#ifndef ROCKETPERF_ENGINE_CASE_H
#define ROCKETPERF_ENGINE_CASE_H

#include "rocketperf/engine_cycle.h"

#include <stdio.h>

typedef struct {
    char id[64];
    char object_ref[64];
    char source_ref[256];
    char cycle_evidence[32];
    char feed_model[32];
    double fuel_temperature_k;
    double oxidizer_temperature_k;
    double fuel_density_override_kg_per_m3;
    RpEngineCycleInput input;
} RpEngineCycleCase;

/* Strict all-required SI input, research_scenario only. Methane h/rho come
 * from pinned liquid table. RP-1 h/elements use assigned anchors, density is
 * explicitly assumed; O2 anchor h has no pressure correction in that model.
 * Load/build failure preserves output. Run solves before emitting any bytes. */
RpStatus rp_engine_case_load(const char *path, RpEngineCycleCase *output, RpError *error);
RpStatus rp_engine_case_run(const char *path, FILE *stream, int text_mode, RpError *error);

#endif
