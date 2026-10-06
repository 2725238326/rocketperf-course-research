#include "arguments.h"
#include "rocketperf/numeric.h"
#include <ctype.h>
#include <errno.h>
#include <stdlib.h>
#include <stddef.h>

int rp_cli_parse_decimal(const char *start, const char **next, double *output)
{
    const char *cursor;
    unsigned int digits = 0U;
    char *end;
    double value;
    if (start == NULL || next == NULL || output == NULL) { return 0; }
    cursor = start;
    if (*cursor == '+' || *cursor == '-') { ++cursor; }
    while (*cursor >= '0' && *cursor <= '9') { ++cursor; ++digits; }
    if (*cursor == '.') {
        ++cursor;
        while (*cursor >= '0' && *cursor <= '9') { ++cursor; ++digits; }
    }
    if (digits == 0U) { return 0; }
    if (*cursor == 'e' || *cursor == 'E') {
        unsigned int exponent_digits = 0U;
        ++cursor;
        if (*cursor == '+' || *cursor == '-') { ++cursor; }
        while (*cursor >= '0' && *cursor <= '9') { ++cursor; ++exponent_digits; }
        if (exponent_digits == 0U) { return 0; }
    }
    if (*cursor != '\0' && *cursor != ',' && !isspace((unsigned char)*cursor)) { return 0; }
    errno = 0;
    value = strtod(start, &end);
    if (errno == ERANGE || end != cursor || !rp_isfinite(value)) { return 0; }
    *next = cursor;
    *output = value;
    return 1;
}
