#include "case_text.h"
#include "rocketperf/numeric.h"

#include <ctype.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>

char *rp_text_trim(char *text)
{
    char *end;
    while (*text != '\0' && isspace((unsigned char)*text)) { ++text; }
    end = text + strlen(text);
    while (end > text && isspace((unsigned char)end[-1])) { --end; }
    *end = '\0';
    return text;
}
int rp_text_ascii(const char *text, size_t capacity)
{
    const size_t length = strlen(text);
    if (length == 0U || length >= capacity) { return 0; }
    for (size_t i = 0U; i < length; ++i) {
        if ((unsigned char)text[i] < 32U || (unsigned char)text[i] > 126U) { return 0; }
    }
    return 1;
}
int rp_text_identifier(const char *text)
{
    if (!rp_text_ascii(text, 64U)) { return 0; }
    for (const char *p = text; *p != '\0'; ++p) {
        if (!((*p >= 'a' && *p <= 'z') || (*p >= '0' && *p <= '9') || *p == '_' || *p == '-')) { return 0; }
    }
    return 1;
}
int rp_text_decimal(const char *text, double *output)
{
    const char *p = text;
    unsigned int digits = 0U;
    char *end;
    double result;
    if (*p == '+' || *p == '-') { ++p; }
    while (*p >= '0' && *p <= '9') { ++p; ++digits; }
    if (*p == '.') {
        ++p;
        while (*p >= '0' && *p <= '9') { ++p; ++digits; }
    }
    if (digits == 0U) { return 0; }
    if (*p == 'e' || *p == 'E') {
        ++p;
        if (*p == '+' || *p == '-') { ++p; }
        digits = 0U;
        while (*p >= '0' && *p <= '9') { ++p; ++digits; }
        if (digits == 0U) { return 0; }
    }
    if (*p != '\0') { return 0; }
    errno = 0;
    result = strtod(text, &end);
    if (errno == ERANGE || *end != '\0' || !rp_isfinite(result)) { return 0; }
    *output = result;
    return 1;
}
RpStatus rp_text_parse_failure(RpError *error, unsigned int line, const char *message)
{
    char detail[192];
    (void)snprintf(detail, sizeof(detail), "Case line %u: %s", line, message);
    return rp_error_set(error, RP_PARSE_ERROR, detail);
}
int rp_text_read_line(FILE *file, char *buffer, size_t capacity)
{
    size_t length = 0U;
    int character;
    while ((character = fgetc(file)) != EOF) {
        if (character == 0 || length + 1U >= capacity) { return -1; }
        buffer[length++] = (char)character;
        if (character == '\n') { break; }
    }
    buffer[length] = '\0';
    return length == 0U ? 0 : 1;
}
