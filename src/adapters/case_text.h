#ifndef ROCKETPERF_CASE_TEXT_H
#define ROCKETPERF_CASE_TEXT_H

#include "rocketperf/status.h"

#include <stddef.h>
#include <stdio.h>

char *rp_text_trim(char *text);
int rp_text_ascii(const char *text, size_t capacity);
int rp_text_identifier(const char *text);
int rp_text_decimal(const char *text, double *output);
/* 1=line, 0=EOF, -1=NUL or length limit. Caller checks ferror(). */
int rp_text_read_line(FILE *file, char *buffer, size_t capacity);
RpStatus rp_text_parse_failure(RpError *error, unsigned int line, const char *message);

#endif
