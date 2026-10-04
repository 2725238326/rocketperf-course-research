#include "rocketperf/cycle_study.h"
#include "rocketperf/numeric.h"

#include <math.h>
#include <string.h>

typedef struct { const char *name; size_t offset; } StudyField;
#define FIELD(name) {#name, offsetof(RpCycleInput, name)}
#define PUMP(name) {#name "_pump_efficiency", offsetof(RpCycleInput, name##_pump) + offsetof(RpLiquidPumpInput, efficiency)}
static const StudyField fields[] = {
    FIELD(main_area_ratio), FIELD(ambient_pressure_pa), FIELD(branch_axial_projection),
    FIELD(turbine_efficiency), FIELD(chamber_temperature_k), FIELD(overall_oxidizer_fuel_ratio),
    PUMP(fuel), PUMP(oxidizer)
};
#undef FIELD
#undef PUMP
_Static_assert(sizeof(fields) / sizeof(fields[0]) == RP_CYCLE_FIELD_COUNT, "Study field registry mismatch");

const char *rp_cycle_study_field_name(RpCycleStudyField field)
{
    return field >= 0 && field < RP_CYCLE_FIELD_COUNT ? fields[field].name : NULL;
}
double rp_cycle_study_input_value(const RpCycleInput *input, RpCycleStudyField field)
{
    double value;
    if (input == NULL || rp_cycle_study_field_name(field) == NULL) { return NAN; }
    memcpy(&value, (const unsigned char *)input + fields[field].offset, sizeof(value));
    return value;
}
static RpStatus compare(const RpCycleInput *base, const RpCycleResult *reference,
                         RpCycleStudyField field, RpCycleStudyPoint *point, RpError *error)
{
    const double base_value = rp_cycle_study_input_value(base, field);
    const double reference_area = reference->main_throat_area_m2 * base->main_area_ratio;
    RpCycleStudyMetrics *m = &point->metrics;
    m->thrust_change_n = point->result.total_thrust_n - reference->total_thrust_n;
    m->isp_change_s = point->result.engine_specific_impulse_s - reference->engine_specific_impulse_s;
    m->branch_flow_change_kg_per_s = point->result.branch_mass_flow_kg_per_s - reference->branch_mass_flow_kg_per_s;
    m->required_heat_change_w = (point->result.generator_heat_w - reference->generator_heat_w) +
                              (point->result.chamber_heat_w - reference->chamber_heat_w);
    m->main_exit_area_m2 = point->result.main_throat_area_m2 * point->input.main_area_ratio;
    m->main_exit_diameter_m = sqrt(4.0 * m->main_exit_area_m2 / 3.14159265358979323846);
    m->main_exit_area_change_m2 = m->main_exit_area_m2 - reference_area;
    m->thrust_relative_change = m->thrust_change_n / reference->total_thrust_n;
    m->isp_relative_change = m->isp_change_s / reference->engine_specific_impulse_s;
    if (base_value != 0.0 && point->value != base_value) {
        const double fraction = (point->value - base_value) / base_value;
        if (rp_isfinite(fraction) && fraction != 0.0) {
            m->elasticity_defined = 1;
            m->thrust_secant_elasticity = m->thrust_relative_change / fraction;
            m->isp_secant_elasticity = m->isp_relative_change / fraction;
        }
    }
    if (!rp_isfinite(m->thrust_change_n) || !rp_isfinite(m->isp_change_s) ||
        !rp_isfinite(m->branch_flow_change_kg_per_s) || !rp_isfinite(m->required_heat_change_w) ||
        !rp_isfinite(m->main_exit_area_m2) || !rp_isfinite(m->main_exit_diameter_m) ||
        !rp_isfinite(m->main_exit_area_change_m2) || !rp_isfinite(m->thrust_relative_change) ||
        !rp_isfinite(m->isp_relative_change) || !rp_isfinite(m->thrust_secant_elasticity) ||
        !rp_isfinite(m->isp_secant_elasticity)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "Cycle study metric overflow or invalid elasticity.");
    }
    return RP_OK;
}
RpStatus rp_cycle_scan_prescribed(const RpCycleInput *base, RpCycleStudyField field,
                                  const double *values, size_t count,
                                  RpCycleResult *baseline, RpCycleStudyPoint *points,
                                  size_t capacity, size_t *point_count, RpError *error)
{
    RpCycleResult reference;
    RpStatus status;
    if (point_count != NULL) { *point_count = 0U; }
    if (base == NULL || values == NULL || baseline == NULL || points == NULL || point_count == NULL ||
        count == 0U || count > capacity || rp_cycle_study_field_name(field) == NULL) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Study needs valid field, baseline and sized point storage.");
    }
    for (size_t i = 0U; i < count; ++i) {
        if (!rp_isfinite(values[i])) { return rp_error_set(error, RP_INVALID_ARGUMENT, "Study values must be finite."); }
    }
    status = rp_cycle_solve_prescribed(base, NULL, &reference, error);
    if (status != RP_OK) { return status; }
    for (size_t i = 0U; i < count; ++i) {
        RpError local_error = {0};
        RpCycleStudyPoint point = {0};
        point.value = values[i]; point.input = *base;
        memcpy((unsigned char *)&point.input + fields[field].offset, &point.value, sizeof(point.value));
        point.status = rp_cycle_solve_prescribed(&point.input, NULL, &point.result, &local_error);
        if (point.status == RP_OK) { point.status = compare(base, &reference, field, &point, &local_error); }
        if (point.status != RP_OK) { memcpy(point.message, local_error.message, sizeof(point.message)); }
        points[i] = point;
    }
    *baseline = reference; *point_count = count;
    rp_error_clear(error); return RP_OK;
}
