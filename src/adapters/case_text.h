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
/* Drop a UTF-8 BOM in place; call on the first line only. */
void rp_text_strip_bom(char *buffer);
/* JSON string with quote/backslash escaping; returns zero on output failure. */
int rp_text_write_json_string(FILE *stream, const char *value);
RpStatus rp_text_parse_failure(RpError *error, unsigned int line, const char *message);

#endif
