#include "case_file.h"
#include "rocketperf/version.h"
#include "rocketperf/numeric.h"

#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

static const char *const fields[] = {
    "schema_version", "case_id", "case_kind", "source_ref", "model",
    "gamma", "gas_constant_j_kg_k", "stagnation_temperature_k",
    "stagnation_pressure_pa", "area_ratio", "throat_area_m2", "ambient_pressure_pa"
};

static char *trim(char *text)
{
    char *end;
    while (*text != '\0' && isspace((unsigned char)*text)) { ++text; }
    end = text + strlen(text);
    while (end > text && isspace((unsigned char)end[-1])) { --end; }
    *end = '\0';
    return text;
}

static int ascii_text(const char *text, size_t capacity)
{
    const size_t length = strlen(text);
    if (length == 0U || length >= capacity) { return 0; }
    for (size_t i = 0U; i < length; ++i) {
        if ((unsigned char)text[i] < 32U || (unsigned char)text[i] > 126U) { return 0; }
    }
    return 1;
}

static int case_identifier(const char *text)
{
    if (!ascii_text(text, 64U)) { return 0; }
    for (const char *p = text; *p != '\0'; ++p) {
        if (!((*p >= 'a' && *p <= 'z') || (*p >= '0' && *p <= '9') || *p == '_' || *p == '-')) {
            return 0;
        }
    }
    return 1;
}

static int decimal_value(const char *text, double *output)
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

static RpStatus parse_failure(RpError *error, unsigned int line, const char *message)
{
    char detail[192];
    (void)snprintf(detail, sizeof(detail), "Case line %u: %s", line, message);
    return rp_error_set(error, RP_PARSE_ERROR, detail);
}

/* Read bytes explicitly: fgets/strlen alone can silently hide embedded NULs. */
static int read_line(FILE *file, char *buffer, size_t capacity)
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

static RpStatus assign_value(RpCase *study, unsigned int field, const char *value,
                              unsigned int line, RpError *error)
{
    double number = 0.0;
    if (field >= 5U && !decimal_value(value, &number)) {
        return parse_failure(error, line, "Expected a finite decimal number, without a unit suffix.");
    }
    switch (field) {
    case 0U:
        if (strcmp(value, "1") != 0) { return parse_failure(error, line, "Unsupported schema_version."); }
        break;
    case 1U:
        if (!case_identifier(value)) { return parse_failure(error, line, "case_id must use 1-63 lowercase ASCII letters, digits, '_' or '-'."); }
        (void)snprintf(study->id, sizeof(study->id), "%s", value);
        break;
    case 2U:
        if (strcmp(value, "synthetic_benchmark") != 0 && strcmp(value, "research_scenario") != 0) {
            return parse_failure(error, line, "Only synthetic_benchmark or research_scenario is supported.");
        }
        (void)snprintf(study->kind, sizeof(study->kind), "%s", value);
        break;
    case 3U:
        if (!ascii_text(value, sizeof(study->source_ref))) { return parse_failure(error, line, "source_ref must be 1-255 printable ASCII bytes."); }
        (void)snprintf(study->source_ref, sizeof(study->source_ref), "%s", value);
        break;
    case 4U:
        if (strcmp(value, RP_IDEAL_NOZZLE_MODEL) != 0) { return parse_failure(error, line, "Unsupported model identifier."); }
        break;
    case 5U: study->input.gamma = number; break;
    case 6U: study->input.gas_constant_j_kg_k = number; break;
    case 7U: study->input.stagnation_temperature_k = number; break;
    case 8U: study->input.stagnation_pressure_pa = number; break;
    case 9U: study->input.area_ratio = number; break;
    case 10U: study->input.throat_area_m2 = number; break;
    case 11U: study->input.ambient_pressure_pa = number; break;
    default: return parse_failure(error, line, "Internal field mapping error.");
    }
    return RP_OK;
}

RpStatus rp_case_load(const char *utf8_path, RpCase *output, RpError *error)
{
    RpCase study = {0};
    char buffer[512];
    FILE *file;
    unsigned int seen = 0U;
    unsigned int line = 0U;
    int line_status;
    RpStatus status = RP_OK;
    if (utf8_path == NULL || output == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Case path and output are required.");
    }
    file = rp_fopen_utf8_read(utf8_path);
    if (file == NULL) { return rp_error_set(error, RP_IO_ERROR, "Cannot open case file."); }
    while ((line_status = read_line(file, buffer, sizeof(buffer))) != 0) {
        char *text;
        char *separator;
        char *key;
        char *value;
        unsigned int field;
        size_t length;
        ++line;
        if (line > 128U || line_status < 0) {
            status = parse_failure(error, line, "Case exceeds line limits or contains an embedded NUL.");
            break;
        }
        length = strlen(buffer);
        if (line == 1U && length >= 3U && memcmp(buffer, "\xEF\xBB\xBF", 3U) == 0) {
            memmove(buffer, buffer + 3, length - 2U);
        }
        text = trim(buffer);
        if (*text == '\0' || *text == '#') { continue; }
        separator = strchr(text, '=');
        if (separator == NULL) { status = parse_failure(error, line, "Expected key=value."); break; }
        *separator = '\0';
        key = trim(text);
        value = trim(separator + 1);
        for (field = 0U; field < sizeof(fields) / sizeof(fields[0]); ++field) {
            if (strcmp(key, fields[field]) == 0) { break; }
        }
        if (field == sizeof(fields) / sizeof(fields[0])) { status = parse_failure(error, line, "Unknown field."); break; }
        if ((seen & (1U << field)) != 0U) { status = parse_failure(error, line, "Duplicate field."); break; }
        status = assign_value(&study, field, value, line, error);
        if (status != RP_OK) { break; }
        seen |= 1U << field;
    }
    if (status == RP_OK && ferror(file)) { status = rp_error_set(error, RP_IO_ERROR, "Cannot read case file."); }
    if (fclose(file) != 0 && status == RP_OK) { status = rp_error_set(error, RP_IO_ERROR, "Cannot close case file."); }
    if (status != RP_OK) { return status; }
    if (seen != (1U << 12U) - 1U) { return parse_failure(error, line, "Missing required field(s)."); }
    *output = study;
    rp_error_clear(error);
    return RP_OK;
}
