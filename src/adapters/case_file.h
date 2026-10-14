#ifndef ROCKETPERF_CASE_FILE_H
#define ROCKETPERF_CASE_FILE_H

#include "rocketperf/nozzle.h"

#include <stddef.h>
#include <stdio.h>

typedef struct {
    char id[64];
    char kind[32];
    char source_ref[256];
    RpNozzleInput input;
} RpCase;

/* Strict schema; unknown/duplicate/missing fields fail. Output transactional. */
RpStatus rp_case_load(const char *utf8_path, RpCase *output, RpError *error);
/* Validate all metadata/numbers before emitting JSON. Invalid data writes no
 * bytes. An I/O failure can leave a partial report; caller owns flushing. */
RpStatus rp_case_write_json(FILE *stream, const RpCase *study,
                            const RpNozzleResult *result, RpError *error);
RpStatus rp_case_write_study_json(FILE *stream, const RpCase *study,
                                  const RpNozzleStudyGrid *grid,
                                  const RpNozzleStudyPoint *points,
                                  size_t point_count, RpError *error);
/* Regime assessment report: same validation-before-write contract. */
RpStatus rp_case_write_regime_json(FILE *stream, const RpCase *study,
                                   const RpNozzleRegimeResult *regime, RpError *error);
FILE *rp_fopen_utf8_read(const char *utf8_path);
/* Locate a bundled relative case: the current directory first, then the
 * executable's folder and up to four parents (release package, build/release or
 * build/artifacts/<config>/<id> layouts).
 * Writes a UTF-8 path into output; returns zero when no candidate opens. */
int rp_find_bundled_case(const char *relative, char *output, size_t capacity);

#endif
