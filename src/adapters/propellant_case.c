#include "propellant_case.h"
#include "case_file.h"
#include "case_text.h"

#include <stddef.h>
#include <string.h>

/* Field name -> offset into RpPropellantComparisonInput, so the strict
 * key=value parser stays table-driven like the other case readers.
 * Nested inlets compose their offsets with macros; values[...] indices
 * follow the struct member order, not the file order. */
typedef struct { const char *name; size_t offset; } NumericField;
#define METHANE(member) {"methane_" #member, offsetof(RpPropellantComparisonInput, methane) + offsetof(RpContinuousLiquidFeed, member)}
#define KEROSENE(member) {"kerosene_" #member, offsetof(RpPropellantComparisonInput, kerosene) + offsetof(RpKeroseneAnchorFeed, reactants) + offsetof(RpAssignedReactantFeed, member)}
#define COMMON(member) {#member, offsetof(RpPropellantComparisonInput, member)}
static const NumericField numbers[] = {
    METHANE(fuel_temperature_k), METHANE(fuel_pressure_pa),
    METHANE(oxidizer_temperature_k), METHANE(oxidizer_pressure_pa),
    METHANE(oxidizer_fuel_mass_ratio), KEROSENE(fuel_temperature_k),
    KEROSENE(oxidizer_temperature_k), KEROSENE(oxidizer_fuel_mass_ratio),
    {"pressure_pa", offsetof(RpPropellantComparisonInput, methane) + offsetof(RpContinuousLiquidFeed, product_pressure_pa)},
    COMMON(throat_area_m2), COMMON(area_ratio), COMMON(ambient_pressure_pa)
};
#undef METHANE
#undef KEROSENE
#undef COMMON
static const char *const metadata[] = {
    "schema_version", "case_id", "model", "source_ref", "methane_dataset_id",
    "methane_enthalpy_basis", "methane_phase", "kerosene_dataset_id", "kerosene_fuel_id",
    "kerosene_oxidizer_id", "kerosene_phase"
};
#define NUMBER_COUNT (sizeof(numbers) / sizeof(numbers[0]))
#define META_COUNT (sizeof(metadata) / sizeof(metadata[0]))

/* required[i] pins the identity of metadata[i]: file values must match the
 * model's pinned datasets/phases exactly, so a case cannot silently swap in
 * a different property table or reactant. case_id (1) and source_ref (3)
 * are free-form within their character rules and copied into the study. */
static RpStatus assign_metadata(RpPropellantCase *study, size_t index,
                                 const char *value, unsigned int line, RpError *error)
{
    const char *required[] = {"1", NULL, "propellant_fixed_geometry_v1", NULL,
        rp_liquid_feed_dataset_id(), rp_liquid_feed_enthalpy_basis_id(), "liquid",
        rp_kerosene_dataset_id(), "RP-1", "O2(L)", "liquid"};
    if (index == 1U) {
        if (!rp_text_identifier(value)) { return rp_text_parse_failure(error, line, "Invalid lowercase case_id."); }
        (void)snprintf(study->id, sizeof(study->id), "%s", value);
    } else if (index == 3U) {
        if (!rp_text_ascii(value, sizeof(study->source_ref))) { return rp_text_parse_failure(error, line, "Invalid printable ASCII source_ref."); }
        (void)snprintf(study->source_ref, sizeof(study->source_ref), "%s", value);
    } else if (strcmp(value, required[index]) != 0) {
        return rp_text_parse_failure(error, line, "Unsupported model, data identity or phase.");
    }
    return RP_OK;
}

RpStatus rp_propellant_case_load(const char *utf8_path, RpPropellantCase *output, RpError *error)
{
    RpPropellantCase result = {0};
    /* seen[] covers both tables, so unknown keys, duplicates and missing
     * fields are one uniform rejection path shared with the file limits. */
    unsigned char seen[META_COUNT + NUMBER_COUNT] = {0};
    char buffer[512];
    unsigned int line = 0U;
    int line_status;
    RpStatus status = RP_OK;
    FILE *file;
    if (utf8_path == NULL || output == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Propellant case path and output are required.");
    }
    file = rp_fopen_utf8_read(utf8_path);
    if (file == NULL) { return rp_error_set(error, RP_IO_ERROR, "Cannot open propellant case file."); }
    while ((line_status = rp_text_read_line(file, buffer, sizeof(buffer))) != 0) {
        char *text;
        char *separator;
        char *key;
        char *value;
        size_t index;
        ++line;
        if (line > 128U || line_status < 0) {
            status = rp_text_parse_failure(error, line, "Line limit exceeded or embedded NUL."); break;
        }
        if (line == 1U && strlen(buffer) >= 3U && memcmp(buffer, "\xEF\xBB\xBF", 3U) == 0) {
            memmove(buffer, buffer + 3, strlen(buffer) - 2U);
        }
        text = rp_text_trim(buffer);
        if (*text == '\0' || *text == '#') { continue; }
        separator = strchr(text, '=');
        if (separator == NULL) { status = rp_text_parse_failure(error, line, "Expected key=value."); break; }
        *separator = '\0';
        key = rp_text_trim(text); value = rp_text_trim(separator + 1);
        for (index = 0U; index < META_COUNT; ++index) {
            if (strcmp(key, metadata[index]) == 0) { break; }
        }
        if (index == META_COUNT) {
            size_t number;
            for (number = 0U; number < NUMBER_COUNT; ++number) {
                if (strcmp(key, numbers[number].name) == 0) { break; }
            }
            index = META_COUNT + number;
        }
        if (index == META_COUNT + NUMBER_COUNT) { status = rp_text_parse_failure(error, line, "Unknown field."); break; }
        if (seen[index] != 0U) { status = rp_text_parse_failure(error, line, "Duplicate field."); break; }
        if (index < META_COUNT) {
            status = assign_metadata(&result, index, value, line, error);
        } else {
            double number;
            if (!rp_text_decimal(value, &number)) {
                status = rp_text_parse_failure(error, line, "Expected a finite decimal number.");
            } else {
                memcpy((char *)&result.input + numbers[index - META_COUNT].offset, &number, sizeof(number));
            }
        }
        if (status != RP_OK) { break; }
        seen[index] = 1U;
    }
    if (status == RP_OK && ferror(file)) { status = rp_error_set(error, RP_IO_ERROR, "Cannot read propellant case file."); }
    if (fclose(file) != 0 && status == RP_OK) { status = rp_error_set(error, RP_IO_ERROR, "Cannot close propellant case file."); }
    if (status != RP_OK) { return status; }
    for (size_t index = 0U; index < sizeof(seen); ++index) {
        if (seen[index] == 0U) { return rp_text_parse_failure(error, line, "Missing required field."); }
    }
    /* Identity fields are re-pinned from the compiled model, not trusted from
     * the file (they were only string-compared above); the kerosene chamber
     * pressure follows the common product pressure so both sides solve the
     * same chamber condition. */
    result.input.methane.dataset_id = rp_liquid_feed_dataset_id();
    result.input.methane.enthalpy_basis_id = rp_liquid_feed_enthalpy_basis_id();
    result.input.methane.fuel_phase = RP_LIQUID_SINGLE_PHASE;
    result.input.methane.oxidizer_phase = RP_LIQUID_SINGLE_PHASE;
    result.input.kerosene.dataset_id = rp_kerosene_dataset_id();
    result.input.kerosene.reactants.fuel_anchor_id = "RP-1";
    result.input.kerosene.reactants.oxidizer_anchor_id = "O2(L)";
    result.input.kerosene.reactants.phase = RP_FEED_LIQUID;
    result.input.kerosene.reactants.pressure_pa = result.input.methane.product_pressure_pa;
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}
