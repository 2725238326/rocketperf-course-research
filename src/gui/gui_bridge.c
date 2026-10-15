#include "gui_bridge.h"
#include "gui_json.h"
#include "engine_case.h"
#include "case_file.h"
#include "rocketperf/combustion.h"
#include "rocketperf/engine_cycle.h"
#include "rocketperf/frozen_nozzle.h"
#include "rocketperf/liquid_combustion.h"
#include "rocketperf/liquid_feed.h"
#include "rocketperf/propellant_study.h"
#include "rocketperf/thermo.h"
#include "rocketperf/version.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define RP_GUI_SWEEP_MAX 81U
#define RP_GUI_PROFILE_POINTS 24U
#define RP_GUI_GRID_PRESSURES 8U

typedef struct {
    const RpGuiRequest *request;
    RpGuiBuffer *out;
    RpError error;
    RpStatus status;
    const char *stage;
} Call;

static int reject(Call *call, RpStatus status, const char *stage, const char *message)
{
    call->status = status;
    call->stage = stage;
    (void)snprintf(call->error.message, sizeof(call->error.message), "%s", message);
    return 0;
}

static int solver_failed(Call *call, RpStatus status, const char *stage)
{
    call->status = status;
    call->stage = stage;
    return 0;
}

/* Every key must be listed by the command; typos are rejected, not ignored. */
static int only_keys(Call *call, const char *const *allowed, size_t count)
{
    for (size_t i = 0U; i < call->request->count; ++i) {
        size_t k = 0U;
        while (k < count && strcmp(call->request->fields[i].key, allowed[k]) != 0) { ++k; }
        if (k == count) {
            char message[96];
            (void)snprintf(message, sizeof(message), "Unknown argument: %s", call->request->fields[i].key);
            return reject(call, RP_INVALID_ARGUMENT, "arguments", message);
        }
    }
    return 1;
}

/* Bounds here are IPC sanity limits; the solvers enforce physical domains. */
static int number_arg(Call *call, const char *key, double fallback, double lo, double hi, double *output)
{
    const RpGuiField *field = rp_gui_field(call->request, key);
    char message[96];
    if (field == NULL) { *output = fallback; return 1; }
    if (field->kind != RP_GUI_NUMBER || !(field->number >= lo && field->number <= hi)) {
        (void)snprintf(message, sizeof(message), "Argument %s must be a number in [%g, %g].", key, lo, hi);
        return reject(call, RP_INVALID_ARGUMENT, "arguments", message);
    }
    *output = field->number;
    return 1;
}

static int array_arg(Call *call, const char *key, size_t limit, double lo, double hi, double *output, size_t *count)
{
    const RpGuiField *field = rp_gui_field(call->request, key);
    char message[96];
    if (field == NULL || field->kind != RP_GUI_ARRAY || field->count == 0U || field->count > limit) {
        (void)snprintf(message, sizeof(message), "Argument %s must be a list of 1..%u numbers.", key, (unsigned int)limit);
        return reject(call, RP_INVALID_ARGUMENT, "arguments", message);
    }
    for (size_t i = 0U; i < field->count; ++i) {
        if (!(field->array[i] >= lo && field->array[i] <= hi)) {
            (void)snprintf(message, sizeof(message), "Argument %s values must lie in [%g, %g].", key, lo, hi);
            return reject(call, RP_INVALID_ARGUMENT, "arguments", message);
        }
        output[i] = field->array[i];
    }
    *count = field->count;
    return 1;
}

/* ---- chamber state shared by every command ------------------------------- */

typedef struct {
    int kerosene;
    double pc_pa, of, fuel_t_k, fuel_p_pa, ox_t_k, ox_p_pa;
} Point;

typedef struct {
    RpCombustionResult hp;
    double mixture_h_j_per_kg;
    double fuel_density, oxidizer_density;
} Chamber;

static const char *const point_keys[] = {"fuel", "pc", "of", "tf", "pf", "to", "po"};
#define POINT_KEY_COUNT (sizeof(point_keys) / sizeof(point_keys[0]))

/* Defaults are the declared study inlets: CH4 120 K / O2 100 K table states at
 * 10 MPa; RP-1 298.15 K with O2(L) 90.170 K assigned anchors. */
static int read_point(Call *call, Point *point)
{
    const RpGuiField *fuel = rp_gui_field(call->request, "fuel");
    if (fuel != NULL && (fuel->kind != RP_GUI_TEXT || (strcmp(fuel->text, "ch4") != 0 && strcmp(fuel->text, "rp1") != 0))) {
        return reject(call, RP_INVALID_ARGUMENT, "arguments", "Argument fuel must be \"ch4\" or \"rp1\".");
    }
    point->kerosene = fuel != NULL && strcmp(fuel->text, "rp1") == 0;
    return number_arg(call, "pc", 1e7, 100.0, 1e9, &point->pc_pa) &&
        number_arg(call, "of", 2.6, 0.01, 100.0, &point->of) &&
        number_arg(call, "tf", point->kerosene ? 298.15 : 120.0, 1.0, 1000.0, &point->fuel_t_k) &&
        number_arg(call, "pf", 1e7, 100.0, 1e9, &point->fuel_p_pa) &&
        number_arg(call, "to", point->kerosene ? 90.170 : 100.0, 1.0, 1000.0, &point->ox_t_k) &&
        number_arg(call, "po", 1e7, 100.0, 1e9, &point->ox_p_pa);
}

static RpStatus solve_chamber(const Point *point, Chamber *output, RpError *error)
{
    RpStatus status;
    memset(output, 0, sizeof(*output));
    output->fuel_density = output->oxidizer_density = NAN;
    if (!point->kerosene) {
        const RpContinuousLiquidFeed feed = {rp_liquid_feed_dataset_id(), rp_liquid_feed_enthalpy_basis_id(),
            RP_LIQUID_SINGLE_PHASE, RP_LIQUID_SINGLE_PHASE, point->fuel_t_k, point->fuel_p_pa,
            point->ox_t_k, point->ox_p_pa, point->pc_pa, point->of};
        RpContinuousLiquidHpResult hp;
        status = rp_ch4_o2_continuous_liquid_hp(&feed, NULL, &hp, error);
        if (status != RP_OK) { return status; }
        output->hp = hp.chamber;
        output->mixture_h_j_per_kg = hp.inlet.mixture_h_j_per_kg;
        output->fuel_density = hp.inlet.fuel.density_kg_per_m3;
        output->oxidizer_density = hp.inlet.oxidizer.density_kg_per_m3;
        return RP_OK;
    } else {
        const RpKeroseneAnchorFeed feed = {rp_kerosene_dataset_id(),
            {point->pc_pa, point->of, "RP-1", "O2(L)", point->fuel_t_k, point->ox_t_k, RP_FEED_LIQUID}};
        RpAnchorInlet inlet;
        status = rp_kerosene_anchor_inlet(&feed, &inlet, error);
        if (status == RP_OK) { status = rp_kerosene_equilibrium_hp_anchor(&feed, NULL, &output->hp, error); }
        if (status != RP_OK) { return status; }
        output->mixture_h_j_per_kg = inlet.mixture_h_j_per_kg;
        return RP_OK;
    }
}

static RpFrozenNozzleInput nozzle_input(const Chamber *chamber, double area_ratio, double ambient_pa)
{
    RpFrozenNozzleInput input;
    input.chamber_temperature_k = chamber->hp.gas.temperature_k;
    input.chamber_pressure_pa = chamber->hp.gas.pressure_pa;
    memcpy(input.mole_fractions, chamber->hp.gas.mole_fractions, sizeof(input.mole_fractions));
    input.area_ratio = area_ratio;
    input.ambient_pressure_pa = ambient_pa;
    return input;
}

static double gamma_of(const RpGasMixture *gas)
{
    return gas->cp_frozen_j_per_kg_k / (gas->cp_frozen_j_per_kg_k - gas->gas_constant_j_per_kg_k);
}

/* ---- serializers ---------------------------------------------------------- */

static void write_gas(RpGuiBuffer *out, const char *key, const RpGasMixture *gas)
{
    rp_gui_key(out, key);
    rp_gui_open(out, '{');
    rp_gui_num(out, "t", gas->temperature_k);
    rp_gui_num(out, "p", gas->pressure_pa);
    rp_gui_num(out, "mw", gas->molar_mass_kg_per_kmol);
    rp_gui_num(out, "r", gas->gas_constant_j_per_kg_k);
    rp_gui_num(out, "cp", gas->cp_frozen_j_per_kg_k);
    rp_gui_num(out, "gamma", gamma_of(gas));
    rp_gui_num(out, "h", gas->h_j_per_kg);
    rp_gui_num(out, "s", gas->s_j_per_kg_k);
    rp_gui_numbers(out, "x", gas->mole_fractions, RP_CHO_SPECIES_COUNT);
    rp_gui_close(out, '}');
}

static void write_station(RpGuiBuffer *out, const char *key, const RpFrozenFlowStation *station)
{
    rp_gui_key(out, key);
    rp_gui_open(out, '{');
    write_gas(out, "gas", &station->gas);
    rp_gui_num(out, "u", station->velocity_m_per_s);
    rp_gui_num(out, "mach", station->mach);
    rp_gui_num(out, "flux", station->mass_flux_kg_per_m2_s);
    rp_gui_close(out, '}');
}

static double max_abs(const double *values, size_t count)
{
    double worst = 0.0;
    for (size_t i = 0U; i < count; ++i) { if (fabs(values[i]) > worst) { worst = fabs(values[i]); } }
    return worst;
}

static void write_point(RpGuiBuffer *out, const Point *point)
{
    rp_gui_key(out, "input");
    rp_gui_open(out, '{');
    rp_gui_text(out, "fuel", point->kerosene ? "rp1" : "ch4");
    rp_gui_num(out, "pc", point->pc_pa);
    rp_gui_num(out, "of", point->of);
    rp_gui_num(out, "tf", point->fuel_t_k);
    rp_gui_num(out, "to", point->ox_t_k);
    if (!point->kerosene) { rp_gui_num(out, "pf", point->fuel_p_pa); rp_gui_num(out, "po", point->ox_p_pa); }
    rp_gui_text(out, "dataset", point->kerosene ? rp_kerosene_dataset_id() : rp_liquid_feed_dataset_id());
    rp_gui_close(out, '}');
}

static void write_chamber(RpGuiBuffer *out, const Chamber *chamber)
{
    const RpCombustionResult *hp = &chamber->hp;
    rp_gui_key(out, "chamber");
    rp_gui_open(out, '{');
    write_gas(out, "gas", &hp->gas);
    rp_gui_num(out, "graphite_activity", hp->graphite_activity);
    rp_gui_num(out, "mixture_h", chamber->mixture_h_j_per_kg);
    rp_gui_num(out, "fuel_density", chamber->fuel_density);
    rp_gui_num(out, "oxidizer_density", chamber->oxidizer_density);
    rp_gui_num(out, "hp_iterations", (double)hp->hp_iterations);
    rp_gui_num(out, "eq_iterations", (double)hp->equilibrium_iterations);
    rp_gui_num(out, "element_residual", max_abs(hp->element_relative_residual, RP_CHO_ELEMENT_COUNT));
    rp_gui_num(out, "equilibrium_residual", hp->equilibrium_residual);
    rp_gui_num(out, "enthalpy_residual", hp->enthalpy_residual_j_per_kg);
    rp_gui_close(out, '}');
}

static void write_failure(RpGuiBuffer *out, const char *key, RpStatus status, const RpError *error)
{
    rp_gui_key(out, key);
    rp_gui_open(out, '{');
    rp_gui_flag(out, "ok", 0);
    rp_gui_text(out, "status", rp_status_name(status));
    rp_gui_text(out, "message", error->message);
    rp_gui_close(out, '}');
}

/* ---- info / chamber -------------------------------------------------------- */

typedef struct { const char *file; const char *label; } BundledCase;
static const BundledCase bundled_cases[] = {
    {"cases/vehicles/zq3_y1_stage1.ini", "朱雀三号遥一 一级 · 燃气发生器开式"},
    {"cases/vehicles/zq3_y1_stage2.ini", "朱雀三号遥一 二级 · 燃气发生器开式"},
    {"cases/vehicles/cz10b_first_stage1.ini", "长征十号乙 一级 · RP-1 富氧补燃"},
    {"cases/vehicles/cz10b_first_stage2.ini", "长征十号乙 二级 · 开式（待判情景）"},
    {"cases/vehicles/cz10b_first_stage2_orsc.ini", "长征十号乙 二级 · 补燃（待判情景）"},
};
#define BUNDLED_CASE_COUNT (sizeof(bundled_cases) / sizeof(bundled_cases[0]))

static int command_info(Call *call)
{
    RpGuiBuffer *out = call->out;
    if (!only_keys(call, NULL, 0U)) { return 0; }
    rp_gui_open(out, '{');
    rp_gui_text(out, "version", RP_VERSION);
    rp_gui_text(out, "thermo_dataset", rp_thermo_dataset_id());
    rp_gui_text(out, "liquid_dataset", rp_liquid_feed_dataset_id());
    rp_gui_text(out, "liquid_basis", rp_liquid_feed_enthalpy_basis_id());
    rp_gui_text(out, "kerosene_dataset", rp_kerosene_dataset_id());
    rp_gui_text(out, "cycle_model", RP_ADIABATIC_CYCLE_MODEL);
    rp_gui_num(out, "separation_fraction", RP_NOZZLE_SEPARATION_FRACTION);
    rp_gui_key(out, "species");
    rp_gui_open(out, '[');
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) { rp_gui_string(out, rp_cho_species_id(i)); rp_gui_raw(out, ","); }
    rp_gui_close(out, ']');
    rp_gui_key(out, "cases");
    rp_gui_open(out, '[');
    for (size_t i = 0U; i < BUNDLED_CASE_COUNT; ++i) {
        char path[1024];
        RpEngineCycleCase study;
        RpError error = {0};
        RpStatus status = RP_IO_ERROR;
        rp_gui_open(out, '{');
        rp_gui_text(out, "file", bundled_cases[i].file);
        rp_gui_text(out, "label", bundled_cases[i].label);
        if (rp_find_bundled_case(bundled_cases[i].file, path, sizeof(path))) { status = rp_engine_case_load(path, &study, &error); }
        else { (void)rp_error_set(&error, RP_IO_ERROR, "Bundled case file not found next to the program or its parent folders."); }
        rp_gui_flag(out, "ok", status == RP_OK);
        if (status == RP_OK) {
            rp_gui_text(out, "id", study.id);
            rp_gui_text(out, "object_ref", study.object_ref);
            rp_gui_text(out, "evidence", study.cycle_evidence);
            rp_gui_text(out, "feed", study.feed_model);
            rp_gui_flag(out, "staged", study.input.staged_combustion);
        } else {
            rp_gui_text(out, "status", rp_status_name(status));
            rp_gui_text(out, "message", error.message);
        }
        rp_gui_close(out, '}');
    }
    rp_gui_close(out, ']');
    rp_gui_close(out, '}');
    return 1;
}

/* c* is a throat property; a short vacuum expansion (Ae/At = 2) supplies it. */
static RpStatus chamber_cstar(const Chamber *chamber, double *cstar, RpError *error)
{
    const RpFrozenNozzleInput input = nozzle_input(chamber, 2.0, 0.0);
    RpFrozenNozzleResult nozzle;
    const RpStatus status = rp_nozzle_solve_frozen(&input, NULL, &nozzle, error);
    if (status == RP_OK) { *cstar = nozzle.cstar_m_per_s; }
    return status;
}

static int command_chamber(Call *call)
{
    RpGuiBuffer *out = call->out;
    Point point;
    Chamber chamber;
    double cstar = NAN;
    RpStatus status;
    if (!only_keys(call, point_keys, POINT_KEY_COUNT) || !read_point(call, &point)) { return 0; }
    status = solve_chamber(&point, &chamber, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "chamber"); }
    status = chamber_cstar(&chamber, &cstar, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "cstar"); }
    rp_gui_open(out, '{');
    write_point(out, &point);
    write_chamber(out, &chamber);
    rp_gui_num(out, "cstar", cstar);
    rp_gui_close(out, '}');
    return 1;
}

/* Column arrays over O/F; rejected points stay in place with their C status. */
static int command_chamber_sweep(Call *call)
{
    static const char *const keys[] = {"fuel", "pc", "tf", "pf", "to", "po", "of_min", "of_max", "n"};
    RpGuiBuffer *out = call->out;
    Point point;
    double lo, hi, count_value;
    size_t count;
    RpGuiBuffer status_column = {0}, message_column = {0};
    double *columns;
    enum { OF, T, CSTAR, MW, GAMMA, AC, H, FIXED };
    if (!only_keys(call, keys, sizeof(keys) / sizeof(keys[0])) || !read_point(call, &point) ||
        !number_arg(call, "of_min", 0.5, 0.01, 100.0, &lo) || !number_arg(call, "of_max", 4.0, 0.01, 100.0, &hi) ||
        !number_arg(call, "n", 36.0, 2.0, (double)RP_GUI_SWEEP_MAX, &count_value)) { return 0; }
    if (!(hi > lo)) { return reject(call, RP_INVALID_ARGUMENT, "arguments", "of_max must exceed of_min."); }
    count = (size_t)count_value;
    columns = calloc(count * (FIXED + RP_CHO_SPECIES_COUNT), sizeof(double));
    if (columns == NULL) { return reject(call, RP_IO_ERROR, "memory", "Cannot allocate sweep columns."); }
    rp_gui_open(&status_column, '[');
    rp_gui_open(&message_column, '[');
    for (size_t i = 0U; i < count; ++i) {
        Point swept = point;
        Chamber chamber;
        RpError error = {0};
        double cstar = NAN;
        RpStatus status;
        swept.of = lo + (hi - lo) * (double)i / (double)(count - 1U);
        status = solve_chamber(&swept, &chamber, &error);
        if (status == RP_OK) { status = chamber_cstar(&chamber, &cstar, &error); }
        columns[OF * count + i] = swept.of;
        for (size_t c = T; c < FIXED + RP_CHO_SPECIES_COUNT; ++c) { columns[c * count + i] = NAN; }
        if (status == RP_OK) {
            columns[T * count + i] = chamber.hp.gas.temperature_k;
            columns[CSTAR * count + i] = cstar;
            columns[MW * count + i] = chamber.hp.gas.molar_mass_kg_per_kmol;
            columns[GAMMA * count + i] = gamma_of(&chamber.hp.gas);
            columns[AC * count + i] = chamber.hp.graphite_activity;
            columns[H * count + i] = chamber.mixture_h_j_per_kg;
            for (size_t s = 0U; s < RP_CHO_SPECIES_COUNT; ++s) {
                columns[(FIXED + s) * count + i] = chamber.hp.gas.mole_fractions[s];
            }
        }
        rp_gui_string(&status_column, rp_status_name(status));
        rp_gui_raw(&status_column, ",");
        rp_gui_string(&message_column, status == RP_OK ? "" : error.message);
        rp_gui_raw(&message_column, ",");
    }
    rp_gui_close(&status_column, ']');
    rp_gui_close(&message_column, ']');
    rp_gui_open(out, '{');
    write_point(out, &point);
    rp_gui_numbers(out, "of", columns + OF * count, count);
    rp_gui_numbers(out, "t", columns + T * count, count);
    rp_gui_numbers(out, "cstar", columns + CSTAR * count, count);
    rp_gui_numbers(out, "mw", columns + MW * count, count);
    rp_gui_numbers(out, "gamma", columns + GAMMA * count, count);
    rp_gui_numbers(out, "graphite_activity", columns + AC * count, count);
    rp_gui_numbers(out, "mixture_h", columns + H * count, count);
    rp_gui_key(out, "x");
    rp_gui_open(out, '[');
    for (size_t s = 0U; s < RP_CHO_SPECIES_COUNT; ++s) {
        rp_gui_open(out, '[');
        for (size_t i = 0U; i < count; ++i) { rp_gui_number(out, columns[(FIXED + s) * count + i]); }
        rp_gui_close(out, ']');
    }
    rp_gui_close(out, ']');
    rp_gui_key(out, "status");
    rp_gui_raw(out, status_column.data != NULL ? status_column.data : "[],");
    rp_gui_key(out, "message");
    rp_gui_raw(out, message_column.data != NULL ? message_column.data : "[],");
    rp_gui_close(out, '}');
    if (status_column.failed || message_column.failed) { out->failed = 1; }
    rp_gui_buffer_free(&status_column);
    rp_gui_buffer_free(&message_column);
    free(columns);
    return 1;
}
/* ---- nozzle ---------------------------------------------------------------- */

static const char *const nozzle_keys[] = {"fuel", "pc", "of", "tf", "pf", "to", "po", "ar", "pa", "at"};
#define NOZZLE_KEY_COUNT (sizeof(nozzle_keys) / sizeof(nozzle_keys[0]))

static void write_fixed(RpGuiBuffer *out, const char *key, RpStatus status, const RpError *error,
                        const RpFrozenNozzleFixedResult *fixed)
{
    if (status != RP_OK) { write_failure(out, key, status, error); return; }
    rp_gui_key(out, key);
    rp_gui_open(out, '{');
    rp_gui_flag(out, "ok", 1);
    rp_gui_num(out, "thrust", fixed->thrust_n);
    rp_gui_num(out, "isp", fixed->specific_impulse_s);
    rp_gui_num(out, "mdot", fixed->mass_flow_kg_per_s);
    rp_gui_num(out, "cf", fixed->nozzle.thrust_coefficient);
    rp_gui_num(out, "c_eff", fixed->nozzle.effective_velocity_m_per_s);
    rp_gui_num(out, "exit_area", fixed->exit_area_m2);
    rp_gui_num(out, "continuity_residual", fixed->nozzle.continuity_relative_residual);
    rp_gui_num(out, "sonic_residual", fixed->nozzle.sonic_relative_residual);
    rp_gui_close(out, '}');
}

/* Single operating point: chamber -> regime assessment (ideal reference with the
 * actual back pressure) -> attached fixed-area solve (the supported contract,
 * rejects overexpansion) -> vacuum solve -> station profile along Ae/At. */
static int command_nozzle(Call *call)
{
    RpGuiBuffer *out = call->out;
    Point point;
    Chamber chamber;
    double area_ratio, ambient, throat;
    RpFrozenNozzleInput input;
    RpFrozenNozzleRegimeResult regime;
    RpFrozenNozzleFixedResult attached, vacuum;
    RpError attached_error = {0}, vacuum_error = {0};
    RpStatus status, attached_status, vacuum_status;
    double ar[RP_GUI_PROFILE_POINTS], p[RP_GUI_PROFILE_POINTS], t[RP_GUI_PROFILE_POINTS];
    double mach[RP_GUI_PROFILE_POINTS], u[RP_GUI_PROFILE_POINTS];
    size_t used = 0U;
    if (!only_keys(call, nozzle_keys, NOZZLE_KEY_COUNT) || !read_point(call, &point) ||
        !number_arg(call, "ar", 10.0, 1.0, 1e4, &area_ratio) || !number_arg(call, "pa", 0.0, 0.0, 1e8, &ambient) ||
        !number_arg(call, "at", 0.01, 1e-8, 100.0, &throat)) { return 0; }
    status = solve_chamber(&point, &chamber, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "chamber"); }
    input = nozzle_input(&chamber, area_ratio, ambient);
    status = rp_nozzle_assess_frozen(&input, throat, NULL, &regime, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "nozzle"); }
    attached_status = rp_nozzle_solve_frozen_fixed_area(&input, throat, NULL, &attached, &attached_error);
    input.ambient_pressure_pa = 0.0;
    vacuum_status = rp_nozzle_solve_frozen_fixed_area(&input, throat, NULL, &vacuum, &vacuum_error);
    ar[0] = 1.0; p[0] = regime.ideal.throat.gas.pressure_pa; t[0] = regime.ideal.throat.gas.temperature_k;
    mach[0] = regime.ideal.throat.mach; u[0] = regime.ideal.throat.velocity_m_per_s;
    used = 1U;
    for (size_t i = 1U; i < RP_GUI_PROFILE_POINTS; ++i) {
        RpFrozenNozzleResult station;
        RpError ignored = {0};
        input.area_ratio = pow(area_ratio, (double)i / (double)(RP_GUI_PROFILE_POINTS - 1U));
        if (input.area_ratio <= 1.0 + 1e-9) { continue; }
        if (rp_nozzle_solve_frozen(&input, NULL, &station, &ignored) != RP_OK) { continue; }
        ar[used] = input.area_ratio; p[used] = station.exit.gas.pressure_pa; t[used] = station.exit.gas.temperature_k;
        mach[used] = station.exit.mach; u[used] = station.exit.velocity_m_per_s;
        ++used;
    }
    rp_gui_open(out, '{');
    write_point(out, &point);
    rp_gui_num(out, "ar", area_ratio);
    rp_gui_num(out, "pa", ambient);
    rp_gui_num(out, "at", throat);
    write_chamber(out, &chamber);
    rp_gui_key(out, "ideal");
    rp_gui_open(out, '{');
    rp_gui_num(out, "cstar", regime.ideal.cstar_m_per_s);
    rp_gui_num(out, "c_vac", regime.ideal.vacuum_effective_velocity_m_per_s);
    write_station(out, "throat", &regime.ideal.throat);
    write_station(out, "exit", &regime.ideal.exit);
    rp_gui_num(out, "mdot", regime.mass_flow_kg_per_s);
    rp_gui_num(out, "thrust", regime.ideal_thrust_n);
    rp_gui_num(out, "isp", regime.ideal_specific_impulse_s);
    rp_gui_close(out, '}');
    rp_gui_key(out, "regime");
    rp_gui_open(out, '{');
    rp_gui_text(out, "name", rp_nozzle_regime_name(regime.regime));
    rp_gui_num(out, "pa_over_pe", regime.ambient_over_exit_pressure);
    rp_gui_num(out, "separation_reference", regime.separation_reference_pa);
    rp_gui_num(out, "separation_ar", regime.separation_area_ratio_available ? regime.separation_area_ratio : NAN);
    rp_gui_num(out, "matched_ar", regime.matched_area_ratio_available ? regime.matched_area_ratio : NAN);
    rp_gui_close(out, '}');
    write_fixed(out, "attached", attached_status, &attached_error, &attached);
    write_fixed(out, "vacuum", vacuum_status, &vacuum_error, &vacuum);
    rp_gui_key(out, "profile");
    rp_gui_open(out, '{');
    rp_gui_numbers(out, "ar", ar, used);
    rp_gui_numbers(out, "p", p, used);
    rp_gui_numbers(out, "t", t, used);
    rp_gui_numbers(out, "mach", mach, used);
    rp_gui_numbers(out, "u", u, used);
    rp_gui_close(out, '}');
    rp_gui_close(out, '}');
    return 1;
}

/* Area-ratio x ambient grid on one chamber state. Isp/F are the regime
 * interface's ideal values; regime code 0 is the attached (pe >= pa) domain. */
static int command_nozzle_sweep(Call *call)
{
    static const char *const keys[] = {"fuel", "pc", "of", "tf", "pf", "to", "po", "at", "ars", "pas"};
    RpGuiBuffer *out = call->out;
    Point point;
    Chamber chamber;
    double throat, ratios[RP_GUI_ARRAY_MAX], pressures[RP_GUI_GRID_PRESSURES];
    size_t ratio_count, pressure_count;
    double matched[RP_GUI_GRID_PRESSURES], exit_p[RP_GUI_ARRAY_MAX], cf_vac[RP_GUI_ARRAY_MAX];
    double *isp, *thrust, *code;
    RpStatus status;
    if (!only_keys(call, keys, sizeof(keys) / sizeof(keys[0])) || !read_point(call, &point) ||
        !number_arg(call, "at", 0.01, 1e-8, 100.0, &throat) ||
        !array_arg(call, "ars", 64U, 1.0, 1e4, ratios, &ratio_count) ||
        !array_arg(call, "pas", RP_GUI_GRID_PRESSURES, 0.0, 1e8, pressures, &pressure_count)) { return 0; }
    status = solve_chamber(&point, &chamber, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "chamber"); }
    isp = calloc(3U * ratio_count * pressure_count, sizeof(double));
    if (isp == NULL) { return reject(call, RP_IO_ERROR, "memory", "Cannot allocate nozzle grid."); }
    thrust = isp + ratio_count * pressure_count;
    code = thrust + ratio_count * pressure_count;
    for (size_t j = 0U; j < pressure_count; ++j) { matched[j] = NAN; }
    for (size_t i = 0U; i < ratio_count; ++i) {
        exit_p[i] = cf_vac[i] = NAN;
        for (size_t j = 0U; j < pressure_count; ++j) {
            const RpFrozenNozzleInput input = nozzle_input(&chamber, ratios[i], pressures[j]);
            RpFrozenNozzleRegimeResult regime;
            RpError error = {0};
            const size_t k = j * ratio_count + i;
            if (rp_nozzle_assess_frozen(&input, throat, NULL, &regime, &error) != RP_OK) {
                isp[k] = thrust[k] = code[k] = NAN;
                continue;
            }
            isp[k] = regime.ideal_specific_impulse_s;
            thrust[k] = regime.ideal_thrust_n;
            code[k] = (double)regime.regime;
            exit_p[i] = regime.ideal.exit.gas.pressure_pa;
            cf_vac[i] = regime.ideal.thrust_coefficient;
            if (regime.matched_area_ratio_available) { matched[j] = regime.matched_area_ratio; }
        }
    }
    rp_gui_open(out, '{');
    write_point(out, &point);
    rp_gui_numbers(out, "ars", ratios, ratio_count);
    rp_gui_numbers(out, "pas", pressures, pressure_count);
    rp_gui_numbers(out, "matched_ar", matched, pressure_count);
    rp_gui_numbers(out, "exit_p", exit_p, ratio_count);
    rp_gui_numbers(out, "cf_vac", cf_vac, ratio_count);
    rp_gui_key(out, "isp"); rp_gui_open(out, '[');
    for (size_t j = 0U; j < pressure_count; ++j) { rp_gui_numbers(out, NULL, isp + j * ratio_count, ratio_count); }
    rp_gui_close(out, ']');
    rp_gui_key(out, "thrust"); rp_gui_open(out, '[');
    for (size_t j = 0U; j < pressure_count; ++j) { rp_gui_numbers(out, NULL, thrust + j * ratio_count, ratio_count); }
    rp_gui_close(out, ']');
    rp_gui_key(out, "regime"); rp_gui_open(out, '[');
    for (size_t j = 0U; j < pressure_count; ++j) { rp_gui_numbers(out, NULL, code + j * ratio_count, ratio_count); }
    rp_gui_close(out, ']');
    rp_gui_close(out, '}');
    free(isp);
    return 1;
}
/* ---- propellant comparison --------------------------------------------------- */

static RpPropellantComparisonInput comparison_input(double ch4_of, double rp1_of, double area_ratio,
                                                    double ambient, double throat)
{
    RpPropellantComparisonInput input;
    memset(&input, 0, sizeof(input));
    input.methane = (RpContinuousLiquidFeed){rp_liquid_feed_dataset_id(), rp_liquid_feed_enthalpy_basis_id(),
        RP_LIQUID_SINGLE_PHASE, RP_LIQUID_SINGLE_PHASE, 120.0, 1e7, 100.0, 1e7, 1e7, ch4_of};
    input.kerosene = (RpKeroseneAnchorFeed){rp_kerosene_dataset_id(),
        {1e7, rp1_of, "RP-1", "O2(L)", 298.15, 90.170, RP_FEED_LIQUID}};
    input.area_ratio = area_ratio;
    input.ambient_pressure_pa = ambient;
    input.throat_area_m2 = throat;
    return input;
}

static void write_side(RpGuiBuffer *out, const char *key, const RpCombustionResult *hp,
                       const RpFrozenNozzleFixedResult *nozzle)
{
    rp_gui_key(out, key);
    rp_gui_open(out, '{');
    rp_gui_num(out, "tc", hp->gas.temperature_k);
    rp_gui_num(out, "mw", hp->gas.molar_mass_kg_per_kmol);
    rp_gui_num(out, "gamma", gamma_of(&hp->gas));
    rp_gui_num(out, "graphite_activity", hp->graphite_activity);
    rp_gui_num(out, "cstar", nozzle->nozzle.cstar_m_per_s);
    rp_gui_num(out, "cf", nozzle->nozzle.thrust_coefficient);
    rp_gui_num(out, "isp", nozzle->specific_impulse_s);
    rp_gui_num(out, "thrust", nozzle->thrust_n);
    rp_gui_num(out, "mdot", nozzle->mass_flow_kg_per_s);
    rp_gui_num(out, "pe", nozzle->nozzle.exit.gas.pressure_pa);
    rp_gui_num(out, "exit_t", nozzle->nozzle.exit.gas.temperature_k);
    rp_gui_close(out, '}');
}

/* Same Pc = 10 MPa (RP-1 method domain), throat, Ae/At and ambient for both
 * fuels; paired failure semantics come from rp_propellant_compare_fixed. */
static int command_compare(Call *call)
{
    static const char *const keys[] = {"ch4_of", "rp1_of", "ar", "pa", "at", "of_min", "of_max", "n"};
    RpGuiBuffer *out = call->out;
    double ch4_of, rp1_of, area_ratio, ambient, throat, lo, hi, count_value;
    RpPropellantComparisonInput input;
    RpPropellantComparisonResult result;
    RpStatus status;
    size_t count;
    double of[RP_GUI_SWEEP_MAX], columns[8][RP_GUI_SWEEP_MAX];
    if (!only_keys(call, keys, sizeof(keys) / sizeof(keys[0])) ||
        !number_arg(call, "ch4_of", 2.6, 0.01, 100.0, &ch4_of) || !number_arg(call, "rp1_of", 2.6, 0.01, 100.0, &rp1_of) ||
        !number_arg(call, "ar", 10.0, 1.0, 1e4, &area_ratio) || !number_arg(call, "pa", 0.0, 0.0, 1e8, &ambient) ||
        !number_arg(call, "at", 0.01, 1e-8, 100.0, &throat) ||
        !number_arg(call, "of_min", 2.2, 0.01, 100.0, &lo) || !number_arg(call, "of_max", 4.0, 0.01, 100.0, &hi) ||
        !number_arg(call, "n", 19.0, 2.0, (double)RP_GUI_SWEEP_MAX, &count_value)) { return 0; }
    if (!(hi > lo)) { return reject(call, RP_INVALID_ARGUMENT, "arguments", "of_max must exceed of_min."); }
    input = comparison_input(ch4_of, rp1_of, area_ratio, ambient, throat);
    status = rp_propellant_compare_fixed(&input, NULL, NULL, &result, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "comparison"); }
    count = (size_t)count_value;
    for (size_t i = 0U; i < count; ++i) {
        RpPropellantComparisonResult swept;
        RpError ignored = {0};
        RpPropellantComparisonInput point;
        of[i] = lo + (hi - lo) * (double)i / (double)(count - 1U);
        point = comparison_input(of[i], of[i], area_ratio, ambient, throat);
        for (size_t c = 0U; c < 8U; ++c) { columns[c][i] = NAN; }
        if (rp_propellant_compare_fixed(&point, NULL, NULL, &swept, &ignored) != RP_OK) { continue; }
        columns[0][i] = swept.methane.nozzle.specific_impulse_s;
        columns[1][i] = swept.kerosene.nozzle.specific_impulse_s;
        columns[2][i] = swept.methane.nozzle.thrust_n;
        columns[3][i] = swept.kerosene.nozzle.thrust_n;
        columns[4][i] = swept.methane.nozzle.mass_flow_kg_per_s;
        columns[5][i] = swept.kerosene.nozzle.mass_flow_kg_per_s;
        columns[6][i] = swept.methane.nozzle.nozzle.cstar_m_per_s;
        columns[7][i] = swept.kerosene.nozzle.nozzle.cstar_m_per_s;
    }
    rp_gui_open(out, '{');
    rp_gui_num(out, "pc", 1e7);
    rp_gui_num(out, "ar", area_ratio);
    rp_gui_num(out, "pa", ambient);
    rp_gui_num(out, "at", throat);
    rp_gui_num(out, "ch4_of", ch4_of);
    rp_gui_num(out, "rp1_of", rp1_of);
    write_side(out, "ch4", &result.methane.hp.chamber, &result.methane.nozzle);
    write_side(out, "rp1", &result.kerosene.chamber, &result.kerosene.nozzle);
    rp_gui_key(out, "delta");
    rp_gui_open(out, '{');
    rp_gui_num(out, "thrust", result.methane_minus_kerosene_thrust_n);
    rp_gui_num(out, "isp", result.methane_minus_kerosene_isp_s);
    rp_gui_num(out, "mdot", result.methane_minus_kerosene_mass_flow_kg_per_s);
    rp_gui_num(out, "cstar", result.methane_minus_kerosene_cstar_m_per_s);
    rp_gui_close(out, '}');
    rp_gui_key(out, "sweep");
    rp_gui_open(out, '{');
    rp_gui_numbers(out, "of", of, count);
    rp_gui_numbers(out, "ch4_isp", columns[0], count);
    rp_gui_numbers(out, "rp1_isp", columns[1], count);
    rp_gui_numbers(out, "ch4_thrust", columns[2], count);
    rp_gui_numbers(out, "rp1_thrust", columns[3], count);
    rp_gui_numbers(out, "ch4_mdot", columns[4], count);
    rp_gui_numbers(out, "rp1_mdot", columns[5], count);
    rp_gui_numbers(out, "ch4_cstar", columns[6], count);
    rp_gui_numbers(out, "rp1_cstar", columns[7], count);
    rp_gui_close(out, '}');
    rp_gui_close(out, '}');
    return 1;
}
/* ---- engine cycle -------------------------------------------------------------- */

/* Editable members only. Pump inlet pressures and feed temperatures fix the
 * loaded densities/enthalpies, so they stay read-only from the INI file. */
typedef struct { const char *name; size_t offset; double lo, hi; } CycleField;
#define FIELD(member, lo, hi) {#member, offsetof(RpEngineCycleInput, member), lo, hi}
static const CycleField cycle_fields[] = {
    FIELD(total_mass_flow_kg_per_s, 1e-6, 1e6), FIELD(overall_oxidizer_fuel_ratio, 0.01, 100.0),
    FIELD(chamber_pressure_pa, 100.0, 1e9), FIELD(main_area_ratio, 1.0, 1e4),
    FIELD(preburner_pressure_pa, 100.0, 1e9), FIELD(preburner_oxidizer_fuel_ratio, 0.01, 1000.0),
    FIELD(turbine_outlet_pressure_pa, 0.0, 1e9), FIELD(turbine_efficiency, 0.0, 1.0),
    FIELD(shaft_efficiency, 0.0, 1.0), FIELD(auxiliary_power_w, 0.0, 1e12),
    FIELD(maximum_branch_fraction, 0.0, 1.0), FIELD(pump_to_chamber_drop_pa, 0.0, 1e9),
    FIELD(pump_to_preburner_drop_pa, 0.0, 1e9), FIELD(return_pressure_drop_pa, 0.0, 1e9),
    FIELD(branch_area_ratio, 1.0, 1e4), FIELD(ambient_pressure_pa, 0.0, 1e8),
};
#undef FIELD
#define CYCLE_FIELD_COUNT (sizeof(cycle_fields) / sizeof(cycle_fields[0]))
#define PUMP_FIELD_COUNT 4U
static const char *const pump_names[PUMP_FIELD_COUNT] = {
    "fuel_pump_outlet_pressure_pa", "fuel_pump_efficiency", "oxidizer_pump_outlet_pressure_pa", "oxidizer_pump_efficiency"};

static double *pump_member(RpEngineCycleInput *input, size_t index)
{
    switch (index) {
    case 0U: return &input->fuel.pump.outlet_pressure_pa;
    case 1U: return &input->fuel.pump.efficiency;
    case 2U: return &input->oxidizer.pump.outlet_pressure_pa;
    default: return &input->oxidizer.pump.efficiency;
    }
}

static double *cycle_member(RpEngineCycleInput *input, const char *name, double *lo, double *hi)
{
    for (size_t i = 0U; i < CYCLE_FIELD_COUNT; ++i) {
        if (strcmp(name, cycle_fields[i].name) == 0) {
            *lo = cycle_fields[i].lo; *hi = cycle_fields[i].hi;
            return (double *)(void *)((unsigned char *)input + cycle_fields[i].offset);
        }
    }
    for (size_t i = 0U; i < PUMP_FIELD_COUNT; ++i) {
        if (strcmp(name, pump_names[i]) == 0) {
            const int efficiency = (i % 2U) == 1U;
            *lo = efficiency ? 0.0 : 100.0; *hi = efficiency ? 1.0 : 1e9;
            return pump_member(input, i);
        }
    }
    return NULL;
}

/* Loads a whitelisted bundled case and applies numeric overrides; `skip` names
 * a key consumed by the caller (cycle_sweep's field/values). */
static int load_cycle(Call *call, RpEngineCycleCase *study, const char *const *extra, size_t extra_count)
{
    const RpGuiField *file = rp_gui_field(call->request, "case");
    char path[1024];
    RpStatus status;
    size_t which = 0U;
    if (file == NULL || file->kind != RP_GUI_TEXT) {
        return reject(call, RP_INVALID_ARGUMENT, "arguments", "Argument case must name a bundled vehicle case file.");
    }
    while (which < BUNDLED_CASE_COUNT && strcmp(file->text, bundled_cases[which].file) != 0) { ++which; }
    if (which == BUNDLED_CASE_COUNT) { return reject(call, RP_INVALID_ARGUMENT, "arguments", "Unknown bundled case file."); }
    if (!rp_find_bundled_case(bundled_cases[which].file, path, sizeof(path))) {
        return reject(call, RP_IO_ERROR, "case", "Bundled case file not found next to the program or its parent folders.");
    }
    status = rp_engine_case_load(path, study, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "case"); }
    for (size_t i = 0U; i < call->request->count; ++i) {
        const RpGuiField *field = &call->request->fields[i];
        double lo, hi, *member;
        size_t k = 0U;
        char message[112];
        if (strcmp(field->key, "case") == 0) { continue; }
        while (k < extra_count && strcmp(field->key, extra[k]) != 0) { ++k; }
        if (k < extra_count) { continue; }
        member = cycle_member(&study->input, field->key, &lo, &hi);
        if (member == NULL) {
            (void)snprintf(message, sizeof(message), "Argument %s is not an editable cycle input.", field->key);
            return reject(call, RP_INVALID_ARGUMENT, "arguments", message);
        }
        if (field->kind != RP_GUI_NUMBER || !(field->number >= lo && field->number <= hi)) {
            (void)snprintf(message, sizeof(message), "Argument %s must be a number in [%g, %g].", field->key, lo, hi);
            return reject(call, RP_INVALID_ARGUMENT, "arguments", message);
        }
        *member = field->number;
    }
    return 1;
}

static void write_cycle_inputs(RpGuiBuffer *out, RpEngineCycleCase *study)
{
    rp_gui_key(out, "inputs");
    rp_gui_open(out, '{');
    for (size_t i = 0U; i < CYCLE_FIELD_COUNT; ++i) {
        double lo, hi;
        rp_gui_num(out, cycle_fields[i].name, *cycle_member(&study->input, cycle_fields[i].name, &lo, &hi));
    }
    for (size_t i = 0U; i < PUMP_FIELD_COUNT; ++i) { rp_gui_num(out, pump_names[i], *pump_member(&study->input, i)); }
    rp_gui_close(out, '}');
    rp_gui_key(out, "fixed");
    rp_gui_open(out, '{');
    rp_gui_num(out, "fuel_temperature_k", study->fuel_temperature_k);
    rp_gui_num(out, "oxidizer_temperature_k", study->oxidizer_temperature_k);
    rp_gui_num(out, "fuel_pump_inlet_pressure_pa", study->input.fuel.pump.inlet_pressure_pa);
    rp_gui_num(out, "oxidizer_pump_inlet_pressure_pa", study->input.oxidizer.pump.inlet_pressure_pa);
    rp_gui_num(out, "fuel_density", study->input.fuel.pump.density_kg_per_m3);
    rp_gui_num(out, "oxidizer_density", study->input.oxidizer.pump.density_kg_per_m3);
    rp_gui_num(out, "branch_axial_projection", study->input.branch_axial_projection);
    rp_gui_close(out, '}');
}

static void write_cycle_case(RpGuiBuffer *out, const RpEngineCycleCase *study)
{
    rp_gui_key(out, "case");
    rp_gui_open(out, '{');
    rp_gui_text(out, "id", study->id);
    rp_gui_text(out, "object_ref", study->object_ref);
    rp_gui_text(out, "evidence", study->cycle_evidence);
    rp_gui_text(out, "feed", study->feed_model);
    rp_gui_text(out, "source", study->source_ref);
    rp_gui_flag(out, "staged", study->input.staged_combustion);
    rp_gui_close(out, '}');
}

static void write_nozzle_summary(RpGuiBuffer *out, const char *key, const RpFrozenNozzleResult *nozzle)
{
    rp_gui_key(out, key);
    rp_gui_open(out, '{');
    rp_gui_num(out, "cstar", nozzle->cstar_m_per_s);
    rp_gui_num(out, "cf", nozzle->thrust_coefficient);
    rp_gui_num(out, "pe", nozzle->exit.gas.pressure_pa);
    rp_gui_num(out, "te", nozzle->exit.gas.temperature_k);
    rp_gui_num(out, "me", nozzle->exit.mach);
    rp_gui_num(out, "ue", nozzle->exit.velocity_m_per_s);
    rp_gui_close(out, '}');
}

static void write_cycle_result(RpGuiBuffer *out, const RpEngineCycleResult *result)
{
    const RpCycleResult *b = &result->balance;
    rp_gui_key(out, "preburner");
    rp_gui_open(out, '{');
    write_gas(out, "gas", &result->preburner.gas);
    rp_gui_num(out, "graphite_activity", result->preburner.graphite_activity);
    rp_gui_close(out, '}');
    rp_gui_key(out, "chamber");
    rp_gui_open(out, '{');
    write_gas(out, "gas", &result->chamber.gas);
    rp_gui_num(out, "graphite_activity", result->chamber.graphite_activity);
    rp_gui_close(out, '}');
    rp_gui_key(out, "turbine");
    rp_gui_open(out, '{');
    rp_gui_num(out, "in_t", b->turbine.inlet.temperature_k);
    rp_gui_num(out, "in_p", b->turbine.inlet.pressure_pa);
    rp_gui_num(out, "out_t", b->turbine.outlet.temperature_k);
    rp_gui_num(out, "out_p", b->turbine.outlet.pressure_pa);
    rp_gui_num(out, "work", b->turbine.specific_work_j_per_kg);
    rp_gui_num(out, "entropy_generation", b->turbine.entropy_generation_j_per_kg_k);
    rp_gui_close(out, '}');
    rp_gui_key(out, "pumps");
    rp_gui_open(out, '{');
    rp_gui_num(out, "fuel_w", b->fuel_pump.shaft_power_w);
    rp_gui_num(out, "oxidizer_w", b->oxidizer_pump.shaft_power_w);
    rp_gui_num(out, "fuel_work", b->fuel_pump.specific_work_j_per_kg);
    rp_gui_num(out, "oxidizer_work", b->oxidizer_pump.specific_work_j_per_kg);
    rp_gui_close(out, '}');
    write_nozzle_summary(out, "main_nozzle", &b->main_nozzle);
    if (b->branch_nozzle_active) { write_nozzle_summary(out, "branch_nozzle", &b->branch_nozzle); }
    else { rp_gui_key(out, "branch_nozzle"); rp_gui_raw(out, "null,"); }
    rp_gui_key(out, "balance");
    rp_gui_open(out, '{');
    rp_gui_num(out, "fuel_flow", b->fuel_mass_flow_kg_per_s);
    rp_gui_num(out, "oxidizer_flow", b->oxidizer_mass_flow_kg_per_s);
    rp_gui_num(out, "branch_flow", b->branch_mass_flow_kg_per_s);
    rp_gui_num(out, "branch_fuel_flow", b->branch_fuel_mass_flow_kg_per_s);
    rp_gui_num(out, "branch_oxidizer_flow", b->branch_oxidizer_mass_flow_kg_per_s);
    rp_gui_num(out, "returned_flow", b->returned_mass_flow_kg_per_s);
    rp_gui_num(out, "external_flow", b->external_mass_flow_kg_per_s);
    rp_gui_num(out, "main_flow", b->main_mass_flow_kg_per_s);
    rp_gui_num(out, "main_of", b->main_oxidizer_fuel_ratio);
    rp_gui_num(out, "turbine_power", b->turbine_power_w);
    rp_gui_num(out, "pump_power", b->pump_power_w);
    rp_gui_num(out, "mechanical_loss", b->mechanical_loss_w);
    rp_gui_num(out, "main_throat_area", b->main_throat_area_m2);
    rp_gui_num(out, "branch_throat_area", b->branch_throat_area_m2);
    rp_gui_num(out, "main_thrust", b->main_thrust_n);
    rp_gui_num(out, "branch_thrust", b->branch_thrust_n);
    rp_gui_num(out, "total_thrust", b->total_thrust_n);
    rp_gui_num(out, "main_c_eff", b->main_effective_velocity_m_per_s);
    rp_gui_num(out, "engine_c_eff", b->engine_effective_velocity_m_per_s);
    rp_gui_num(out, "isp", b->engine_specific_impulse_s);
    rp_gui_num(out, "mass_residual", b->mass_residual_kg_per_s);
    rp_gui_num(out, "shaft_residual", b->shaft_residual_w);
    rp_gui_num(out, "energy_residual", b->energy_residual_w);
    rp_gui_num(out, "mass_relative", b->mass_relative_residual);
    rp_gui_num(out, "shaft_relative", b->shaft_relative_residual);
    rp_gui_num(out, "energy_relative", b->energy_relative_residual);
    rp_gui_close(out, '}');
    rp_gui_key(out, "diagnostics");
    rp_gui_open(out, '{');
    rp_gui_num(out, "preburner_enthalpy_residual", result->preburner_enthalpy_residual_w);
    rp_gui_num(out, "chamber_enthalpy_residual", result->chamber_enthalpy_residual_w);
    rp_gui_num(out, "exit_element_residual", max_abs(result->exit_element_relative_residual, RP_CHO_ELEMENT_COUNT));
    rp_gui_num(out, "turbine_pressure_iterations", (double)result->turbine_pressure_iterations);
    rp_gui_close(out, '}');
}

static int command_cycle(Call *call)
{
    RpGuiBuffer *out = call->out;
    RpEngineCycleCase study;
    RpEngineCycleResult result;
    RpStatus status;
    if (!load_cycle(call, &study, NULL, 0U)) { return 0; }
    status = rp_engine_cycle_solve(&study.input, NULL, NULL, &result, &call->error);
    if (status != RP_OK) { return solver_failed(call, status, "cycle"); }
    rp_gui_open(out, '{');
    write_cycle_case(out, &study);
    write_cycle_inputs(out, &study);
    write_cycle_result(out, &result);
    rp_gui_close(out, '}');
    return 1;
}

/* One editable field stepped over `values`; each point is an independent solve. */
static int command_cycle_sweep(Call *call)
{
    static const char *const extra[] = {"field", "values"};
    RpGuiBuffer *out = call->out;
    RpEngineCycleCase study;
    const RpGuiField *name = rp_gui_field(call->request, "field");
    double values[RP_GUI_ARRAY_MAX], lo, hi, *member;
    double columns[7][RP_GUI_ARRAY_MAX];
    size_t count;
    RpGuiBuffer messages = {0};
    if (!load_cycle(call, &study, extra, 2U)) { return 0; }
    if (name == NULL || name->kind != RP_GUI_TEXT || (member = cycle_member(&study.input, name->text, &lo, &hi)) == NULL) {
        return reject(call, RP_INVALID_ARGUMENT, "arguments", "Argument field must name an editable cycle input.");
    }
    if (!array_arg(call, "values", 48U, lo, hi, values, &count)) { return 0; }
    rp_gui_open(&messages, '[');
    for (size_t i = 0U; i < count; ++i) {
        RpEngineCycleResult result;
        RpError error = {0};
        RpStatus status;
        *member = values[i];
        status = rp_engine_cycle_solve(&study.input, NULL, NULL, &result, &error);
        for (size_t c = 0U; c < 7U; ++c) { columns[c][i] = NAN; }
        if (status == RP_OK) {
            columns[0][i] = result.balance.engine_specific_impulse_s;
            columns[1][i] = result.balance.total_thrust_n;
            columns[2][i] = result.balance.branch_mass_flow_kg_per_s;
            columns[3][i] = result.preburner.gas.temperature_k;
            columns[4][i] = result.balance.turbine.outlet.pressure_pa;
            columns[5][i] = result.balance.pump_power_w;
            columns[6][i] = result.chamber.gas.temperature_k;
        }
        rp_gui_string(&messages, status == RP_OK ? "" : error.message);
        rp_gui_raw(&messages, ",");
    }
    rp_gui_close(&messages, ']');
    rp_gui_open(out, '{');
    write_cycle_case(out, &study);
    rp_gui_text(out, "field", name->text);
    rp_gui_numbers(out, "values", values, count);
    rp_gui_numbers(out, "isp", columns[0], count);
    rp_gui_numbers(out, "thrust", columns[1], count);
    rp_gui_numbers(out, "branch_flow", columns[2], count);
    rp_gui_numbers(out, "preburner_t", columns[3], count);
    rp_gui_numbers(out, "turbine_out_p", columns[4], count);
    rp_gui_numbers(out, "pump_power", columns[5], count);
    rp_gui_numbers(out, "chamber_t", columns[6], count);
    rp_gui_key(out, "message");
    rp_gui_raw(out, messages.data != NULL ? messages.data : "[],");
    rp_gui_close(out, '}');
    if (messages.failed) { out->failed = 1; }
    rp_gui_buffer_free(&messages);
    return 1;
}

/* ---- dispatch ------------------------------------------------------------------ */

typedef struct { const char *name; int (*run)(Call *call); } Command;
static const Command commands[] = {
    {"info", command_info}, {"chamber", command_chamber}, {"chamber_sweep", command_chamber_sweep},
    {"nozzle", command_nozzle}, {"nozzle_sweep", command_nozzle_sweep}, {"compare", command_compare},
    {"cycle", command_cycle}, {"cycle_sweep", command_cycle_sweep},
};

static double now_ms(void)
{
    struct timespec stamp;
    if (timespec_get(&stamp, TIME_UTC) != TIME_UTC) { return 0.0; }
    return (double)stamp.tv_sec * 1e3 + (double)stamp.tv_nsec / 1e6;
}

char *rp_gui_handle(const char *request_text)
{
    RpGuiRequest *request = malloc(sizeof(*request));
    RpGuiBuffer result = {0}, envelope = {0};
    Call call;
    char reason[96];
    const Command *command = NULL;
    double started, elapsed;
    int ok = 0;
    memset(&call, 0, sizeof(call));
    call.out = &result;
    call.stage = "request";
    if (request == NULL) { return NULL; }
    if (!rp_gui_parse(request_text, request, reason, sizeof(reason))) {
        (void)reject(&call, RP_PARSE_ERROR, "request", reason);
        request->cmd[0] = '\0';
    } else {
        for (size_t i = 0U; i < sizeof(commands) / sizeof(commands[0]); ++i) {
            if (strcmp(request->cmd, commands[i].name) == 0) { command = &commands[i]; }
        }
        if (command == NULL) { (void)reject(&call, RP_INVALID_ARGUMENT, "request", "Unknown command."); }
    }
    call.request = request;
    started = now_ms();
    if (command != NULL) { ok = command->run(&call); }
    elapsed = now_ms() - started;
    if (ok && result.failed) { ok = reject(&call, RP_IO_ERROR, "memory", "Cannot allocate response."); }
    rp_gui_open(&envelope, '{');
    rp_gui_flag(&envelope, "ok", ok);
    rp_gui_text(&envelope, "cmd", request->cmd);
    rp_gui_num(&envelope, "elapsed_ms", elapsed);
    if (ok) {
        rp_gui_key(&envelope, "result");
        rp_gui_raw(&envelope, result.data);
    } else {
        rp_gui_text(&envelope, "status", rp_status_name(call.status));
        rp_gui_text(&envelope, "stage", call.stage != NULL ? call.stage : "");
        rp_gui_text(&envelope, "message", call.error.message);
    }
    rp_gui_close(&envelope, '}');
    rp_gui_buffer_free(&result);
    free(request);
    if (envelope.failed || envelope.data == NULL) { rp_gui_buffer_free(&envelope); return NULL; }
    /* Drop the closing comma the buffer convention leaves after the outer object. */
    if (envelope.length > 0U && envelope.data[envelope.length - 1U] == ',') { envelope.data[--envelope.length] = '\0'; }
    return envelope.data;
}

void rp_gui_release(char *response)
{
    free(response);
}
