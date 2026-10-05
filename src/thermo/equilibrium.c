#include "rocketperf/combustion.h"
#include "rocketperf/numeric.h"
#include "equilibrium_internal.h"

#include <float.h>
#include <math.h>
#include <stddef.h>

#define RP_EQUILIBRIUM_DIMENSION 4U

RpCombustionOptions rp_combustion_default_options(void)
{
    const RpCombustionOptions options = {1e-10, 0.01, 1000.0, 6000.0, 400U, 80U};
    return options;
}

static int valid_options(const RpCombustionOptions *options)
{
    return rp_isfinite(options->equilibrium_tolerance) && options->equilibrium_tolerance >= 1e-13 &&
        options->equilibrium_tolerance <= 1e-8 && rp_isfinite(options->enthalpy_tolerance_j_per_kg) &&
        options->enthalpy_tolerance_j_per_kg > 0.0 && options->enthalpy_tolerance_j_per_kg <= 1.0 &&
        rp_isfinite(options->hp_lower_temperature_k) && rp_isfinite(options->hp_upper_temperature_k) &&
        options->hp_lower_temperature_k >= 1000.0 && options->hp_upper_temperature_k <= 6000.0 &&
        options->hp_lower_temperature_k < options->hp_upper_temperature_k &&
        options->max_equilibrium_iterations > 0U && options->max_equilibrium_iterations <= 10000U &&
        options->max_hp_iterations > 0U && options->max_hp_iterations <= 1000U;
}

static RpStatus gibbs_at_temperature(double temperature, double gibbs[RP_CHO_SPECIES_COUNT], RpError *error)
{
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        const RpNasa9Species *species = rp_thermo_find_species(rp_cho_species_id(i));
        RpThermoState state;
        RpStatus status = rp_nasa9_evaluate(species, temperature, &state, error);
        if (status != RP_OK) { return status; }
        gibbs[i] = species->molar_mass_kg_per_kmol *
            (state.h_j_per_kg / temperature - state.s_j_per_kg_k) / RP_UNIVERSAL_GAS_CONSTANT_J_KMOL_K;
    }
    return RP_OK;
}

/* Residuals are log(element_sum / inventory) and log(species_sum / N).
 * Log-sum-exp keeps both residuals and analytical Jacobian finite. */
static int evaluate_system(const double variables[RP_EQUILIBRIUM_DIMENSION],
                           const double gibbs[RP_CHO_SPECIES_COUNT], double log_pressure,
                           const double inventory[RP_CHO_ELEMENT_COUNT],
                           double logs[RP_CHO_SPECIES_COUNT], double residual[RP_EQUILIBRIUM_DIMENSION],
                           double jacobian[RP_EQUILIBRIUM_DIMENSION][RP_EQUILIBRIUM_DIMENSION], double *norm)
{
    *norm = 0.0;
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        logs[i] = variables[3] - gibbs[i] - log_pressure;
        for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
            logs[i] += (double)rp_cho_element_count(i, e) * variables[e];
        }
        if (!rp_isfinite(logs[i])) { return 0; }
    }
    for (unsigned int row = 0U; row < RP_EQUILIBRIUM_DIMENSION; ++row) {
        double maximum = -DBL_MAX;
        double sum = 0.0;
        for (unsigned int col = 0U; col < RP_EQUILIBRIUM_DIMENSION; ++col) { jacobian[row][col] = 0.0; }
        for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
            const unsigned int weight = row == 3U ? 1U : rp_cho_element_count(i, row);
            if (weight != 0U) { maximum = fmax(maximum, logs[i] + log((double)weight)); }
        }
        for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
            const unsigned int weight = row == 3U ? 1U : rp_cho_element_count(i, row);
            if (weight != 0U) {
                const double contribution = exp(logs[i] + log((double)weight) - maximum);
                sum += contribution;
                for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
                    jacobian[row][e] += contribution * (double)rp_cho_element_count(i, e);
                }
            }
        }
        if (!rp_isfinite(sum) || sum <= 0.0) { return 0; }
        residual[row] = maximum + log(sum) - (row == 3U ? variables[3] : log(inventory[row]));
        for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) { jacobian[row][e] /= sum; }
        jacobian[row][3] = row == 3U ? 0.0 : 1.0;
        if (!rp_isfinite(residual[row])) { return 0; }
        *norm = fmax(*norm, fabs(residual[row]));
    }
    return 1;
}

static int solve_step(double matrix[RP_EQUILIBRIUM_DIMENSION][RP_EQUILIBRIUM_DIMENSION],
                      double right[RP_EQUILIBRIUM_DIMENSION], double step[RP_EQUILIBRIUM_DIMENSION])
{
    for (unsigned int col = 0U; col < RP_EQUILIBRIUM_DIMENSION; ++col) {
        unsigned int pivot = col;
        for (unsigned int row = col + 1U; row < RP_EQUILIBRIUM_DIMENSION; ++row) {
            if (fabs(matrix[row][col]) > fabs(matrix[pivot][col])) { pivot = row; }
        }
        if (!rp_isfinite(matrix[pivot][col]) || fabs(matrix[pivot][col]) < 1e-14) { return 0; }
        if (pivot != col) {
            const double value = right[col];
            right[col] = right[pivot]; right[pivot] = value;
            for (unsigned int j = 0U; j < RP_EQUILIBRIUM_DIMENSION; ++j) {
                const double entry = matrix[col][j];
                matrix[col][j] = matrix[pivot][j]; matrix[pivot][j] = entry;
            }
        }
        for (unsigned int row = col + 1U; row < RP_EQUILIBRIUM_DIMENSION; ++row) {
            const double factor = matrix[row][col] / matrix[col][col];
            for (unsigned int j = col + 1U; j < RP_EQUILIBRIUM_DIMENSION; ++j) { matrix[row][j] -= factor * matrix[col][j]; }
            right[row] -= factor * right[col];
        }
    }
    for (unsigned int reverse = RP_EQUILIBRIUM_DIMENSION; reverse > 0U; --reverse) {
        const unsigned int row = reverse - 1U;
        double value = right[row];
        for (unsigned int j = row + 1U; j < RP_EQUILIBRIUM_DIMENSION; ++j) { value -= matrix[row][j] * step[j]; }
        step[row] = value / matrix[row][row];
        if (!rp_isfinite(step[row])) { return 0; }
    }
    return 1;
}

static RpStatus solve_temperature(double temperature, double log_pressure,
                                  const double inventory[RP_CHO_ELEMENT_COUNT], const RpCombustionOptions *policy,
                                  double variables[RP_EQUILIBRIUM_DIMENSION], unsigned int *iterations,
                                  double logs[RP_CHO_SPECIES_COUNT], double *norm, RpError *error)
{
    double gibbs[RP_CHO_SPECIES_COUNT];
    RpStatus status = gibbs_at_temperature(temperature, gibbs, error);
    if (status != RP_OK) { return status; }
    for (;;) {
        double residual[RP_EQUILIBRIUM_DIMENSION];
        double jacobian[RP_EQUILIBRIUM_DIMENSION][RP_EQUILIBRIUM_DIMENSION];
        double right[RP_EQUILIBRIUM_DIMENSION];
        double step[RP_EQUILIBRIUM_DIMENSION] = {0};
        double maximum_step = 0.0;
        double damping = 1.0;
        int accepted = 0;
        if (!evaluate_system(variables, gibbs, log_pressure, inventory, logs, residual, jacobian, norm)) {
            return rp_error_set(error, RP_NUMERIC_ERROR, "Non-finite equilibrium residual.");
        }
        if (*norm <= policy->equilibrium_tolerance) { return RP_OK; }
        if (*iterations >= policy->max_equilibrium_iterations) {
            return rp_error_set(error, RP_NO_CONVERGENCE, "Equilibrium iteration budget exhausted.");
        }
        ++*iterations;
        for (unsigned int row = 0U; row < RP_EQUILIBRIUM_DIMENSION; ++row) { right[row] = -residual[row]; }
        if (!solve_step(jacobian, right, step)) {
            return rp_error_set(error, RP_NUMERIC_ERROR, "Singular or ill-conditioned equilibrium Jacobian.");
        }
        for (unsigned int j = 0U; j < RP_EQUILIBRIUM_DIMENSION; ++j) { maximum_step = fmax(maximum_step, fabs(step[j])); }
        if (maximum_step > 4.0) { damping = 4.0 / maximum_step; }
        for (unsigned int search = 0U; search < 40U; ++search) {
            double trial[RP_EQUILIBRIUM_DIMENSION];
            double trial_logs[RP_CHO_SPECIES_COUNT];
            double trial_residual[RP_EQUILIBRIUM_DIMENSION];
            double trial_jacobian[RP_EQUILIBRIUM_DIMENSION][RP_EQUILIBRIUM_DIMENSION];
            double trial_norm;
            for (unsigned int j = 0U; j < RP_EQUILIBRIUM_DIMENSION; ++j) { trial[j] = variables[j] + damping * step[j]; }
            if (evaluate_system(trial, gibbs, log_pressure, inventory, trial_logs, trial_residual, trial_jacobian, &trial_norm) &&
                trial_norm < *norm * (1.0 - 1e-4 * damping)) {
                for (unsigned int j = 0U; j < RP_EQUILIBRIUM_DIMENSION; ++j) { variables[j] = trial[j]; }
                accepted = 1;
                break;
            }
            damping *= 0.5;
        }
        if (!accepted) { return rp_error_set(error, RP_NO_CONVERGENCE, "Equilibrium line search stagnated."); }
    }
}

static void gas_inventory(double of_ratio, double inventory[RP_CHO_ELEMENT_COUNT])
{
    inventory[0] = 1.0;
    inventory[1] = 4.0;
    inventory[2] = 2.0 * of_ratio * rp_thermo_find_species("CH4")->molar_mass_kg_per_kmol /
                   rp_thermo_find_species("O2")->molar_mass_kg_per_kmol;
}

/* Inventory and inlet h are separate from product Gibbs data; no fabricated feed T. */
static RpStatus equilibrium_tp(double pressure_pa, const double supplied_inventory[RP_CHO_ELEMENT_COUNT], double feed_enthalpy,
                               double temperature_k, const RpCombustionOptions *policy,
                               RpCombustionResult *output, RpError *error)
{
    RpCombustionResult result = {0};
    double inventory[RP_CHO_ELEMENT_COUNT];
    double variables[RP_EQUILIBRIUM_DIMENSION];
    double logs[RP_CHO_SPECIES_COUNT];
    double initial_gibbs[RP_CHO_SPECIES_COUNT];
    double fractions[RP_CHO_SPECIES_COUNT];
    double log_pressure;
    double continuation = 6000.0;
    double total = 0.0;
    RpStatus status;
    if (temperature_k < 1000.0 || temperature_k > 6000.0 || pressure_pa < 100.0 || pressure_pa > 1e9) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Restricted gas equilibrium: T=1000..6000 K, p=100..1e9 Pa.");
    }
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        if (!rp_isfinite(supplied_inventory[e]) || supplied_inventory[e] <= 0.0) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid product elemental inventory.");
        }
        inventory[e] = supplied_inventory[e] / supplied_inventory[0];
    }
    log_pressure = log(pressure_pa) - log(rp_thermo_reference_pressure_pa());
    status = gibbs_at_temperature(continuation, initial_gibbs, error);
    if (status != RP_OK) { return status; }
    variables[1] = initial_gibbs[6] + log(0.1) + log_pressure;
    variables[2] = initial_gibbs[7] + log(0.1) + log_pressure;
    variables[0] = initial_gibbs[3] + log(0.2) + log_pressure - variables[2];
    variables[3] = log((inventory[0] + inventory[1] + inventory[2]) / 2.0);
    for (;;) {
        status = solve_temperature(continuation, log_pressure, inventory, policy, variables,
                                   &result.equilibrium_iterations, logs, &result.equilibrium_residual, error);
        if (status != RP_OK) { return status; }
        if (continuation == temperature_k) { break; }
        continuation = fmax(temperature_k, continuation - 500.0);
    }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
        fractions[i] = exp(logs[i] - variables[3]);
        if (!rp_isfinite(fractions[i]) || fractions[i] <= 0.0) {
            return rp_error_set(error, RP_NUMERIC_ERROR, "Equilibrium species underflow or non-positive abundance.");
        }
        total += fractions[i];
    }
    for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) { fractions[i] /= total; }
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        double amount = 0.0;
        for (unsigned int i = 0U; i < RP_CHO_SPECIES_COUNT; ++i) {
            amount += (double)rp_cho_element_count(i, e) * exp(logs[i]);
        }
        result.element_relative_residual[e] = (amount - inventory[e]) / inventory[e];
        if (fabs(result.element_relative_residual[e]) > 2.0 * policy->equilibrium_tolerance) {
            return rp_error_set(error, RP_NO_CONVERGENCE, "Element conservation residual exceeds tolerance.");
        }
    }
    status = rp_cho_mixture_evaluate(fractions, temperature_k, pressure_pa, &result.gas, error);
    if (status != RP_OK) { return status; }
    result.enthalpy_residual_j_per_kg = result.gas.h_j_per_kg - feed_enthalpy;
    *output = result;
    rp_error_clear(error);
    return RP_OK;
}

RpStatus rp_ch4_o2_equilibrium_tp(const RpCh4O2Feed *feed, double temperature_k,
                                  const RpCombustionOptions *options,
                                  RpCombustionResult *output, RpError *error)
{
    const RpCombustionOptions policy = options != NULL ? *options : rp_combustion_default_options();
    double enthalpy;
    double inventory[RP_CHO_ELEMENT_COUNT];
    RpStatus status;
    if (output == NULL || !valid_options(&policy) || !rp_isfinite(temperature_k) || temperature_k <= 0.0) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid equilibrium temperature, options or output.");
    }
    status = rp_ch4_o2_feed_enthalpy(feed, &enthalpy, error);
    if (status != RP_OK) { return status; }
    if (feed->oxidizer_fuel_mass_ratio < 0.1 || feed->oxidizer_fuel_mass_ratio > 20.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Gas equilibrium O/F=0.1..20.");
    }
    gas_inventory(feed->oxidizer_fuel_mass_ratio, inventory);
    return equilibrium_tp(feed->pressure_pa, inventory, enthalpy, temperature_k,
                          &policy, output, error);
}

static RpStatus equilibrium_hp(double pressure_pa, const double inventory[RP_CHO_ELEMENT_COUNT], double enthalpy,
                               const RpCombustionOptions *policy,
                               RpCombustionResult *output, RpError *error)
{
    RpCombustionResult lower_state;
    RpCombustionResult upper_state;
    double lower = policy->hp_lower_temperature_k;
    double upper = policy->hp_upper_temperature_k;
    RpStatus status;
    status = equilibrium_tp(pressure_pa, inventory, enthalpy, lower, policy, &lower_state, error);
    if (status != RP_OK) { return status; }
    status = equilibrium_tp(pressure_pa, inventory, enthalpy, upper, policy, &upper_state, error);
    if (status != RP_OK) { return status; }
    if (fabs(lower_state.enthalpy_residual_j_per_kg) <= policy->enthalpy_tolerance_j_per_kg) {
        *output = lower_state; rp_error_clear(error); return RP_OK;
    }
    if (fabs(upper_state.enthalpy_residual_j_per_kg) <= policy->enthalpy_tolerance_j_per_kg) {
        *output = upper_state; rp_error_clear(error); return RP_OK;
    }
    if ((lower_state.enthalpy_residual_j_per_kg < 0.0) == (upper_state.enthalpy_residual_j_per_kg < 0.0)) {
        return rp_error_set(error, RP_NOT_BRACKETED, "HP enthalpy root is not bracketed in the allowed temperature interval.");
    }
    for (unsigned int iteration = 1U; iteration <= policy->max_hp_iterations; ++iteration) {
        const double middle = 0.5 * lower + 0.5 * upper;
        RpCombustionResult result;
        if (middle == lower || middle == upper) {
            return rp_error_set(error, RP_NO_CONVERGENCE, "HP temperature bracket stagnated before enthalpy tolerance.");
        }
        status = equilibrium_tp(pressure_pa, inventory, enthalpy, middle, policy, &result, error);
        if (status != RP_OK) { return status; }
        if (fabs(result.enthalpy_residual_j_per_kg) <= policy->enthalpy_tolerance_j_per_kg) {
            result.hp_iterations = iteration;
            *output = result;
            rp_error_clear(error);
            return RP_OK;
        }
        if ((result.enthalpy_residual_j_per_kg < 0.0) == (lower_state.enthalpy_residual_j_per_kg < 0.0)) {
            lower = middle; lower_state = result;
        } else { upper = middle; }
    }
    return rp_error_set(error, RP_NO_CONVERGENCE, "HP iteration budget exhausted.");
}

RpStatus rp_cho_equilibrium_hp_inventory(
    double pressure_pa,
    const double element_inventory_kmol_per_kg[RP_CHO_ELEMENT_COUNT],
    double feed_enthalpy_j_per_kg,
    const RpCombustionOptions *options,
    RpCombustionResult *output, RpError *error)
{
    const RpCombustionOptions policy = options != NULL ? *options : rp_combustion_default_options();
    double inventory_mass;
    if (output == NULL || element_inventory_kmol_per_kg == NULL || !valid_options(&policy) ||
        !rp_isfinite(pressure_pa) || pressure_pa <= 0.0 ||
        !rp_isfinite(feed_enthalpy_j_per_kg)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid CHO HP inventory, pressure, enthalpy, options or output.");
    }
    if (pressure_pa < 100.0 || pressure_pa > 1e9) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "CHO HP product p=100..1e9 Pa.");
    }
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        if (!rp_isfinite(element_inventory_kmol_per_kg[e]) ||
            element_inventory_kmol_per_kg[e] <= 0.0) {
            return rp_error_set(error, RP_INVALID_ARGUMENT, "CHO HP inventory must be finite and positive.");
        }
    }
    for (unsigned int e = 0U; e < RP_CHO_ELEMENT_COUNT; ++e) {
        const double ratio = element_inventory_kmol_per_kg[e] /
                             element_inventory_kmol_per_kg[0];
        if (!rp_isfinite(ratio) || ratio <= 0.0) {
            return rp_error_set(error, RP_NUMERIC_ERROR, "CHO HP inventory normalization overflow or underflow.");
        }
    }
    /* Normalizing C/H/O ratios must not discard the declared per-kg basis.
     * Atomic masses come from the same pinned database as product species. */
    inventory_mass =
        element_inventory_kmol_per_kg[0] *
            (rp_thermo_find_species("CO")->molar_mass_kg_per_kmol -
             rp_thermo_find_species("O")->molar_mass_kg_per_kmol) +
        element_inventory_kmol_per_kg[1] *
            rp_thermo_find_species("H")->molar_mass_kg_per_kmol +
        element_inventory_kmol_per_kg[2] *
            rp_thermo_find_species("O")->molar_mass_kg_per_kmol;
    if (!rp_isfinite(inventory_mass)) {
        return rp_error_set(error, RP_NUMERIC_ERROR, "CHO HP elemental mass overflow.");
    }
    if (fabs(inventory_mass - 1.0) > 1e-10) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "CHO HP inventory must describe one kg on the pinned chemical mass basis.");
    }
    return equilibrium_hp(pressure_pa, element_inventory_kmol_per_kg,
                          feed_enthalpy_j_per_kg, &policy, output, error);
}

RpStatus rp_ch4_o2_equilibrium_hp(const RpCh4O2Feed *feed,
                                  const RpCombustionOptions *options,
                                  RpCombustionResult *output, RpError *error)
{
    const RpCombustionOptions policy = options != NULL ? *options : rp_combustion_default_options();
    double enthalpy;
    double inventory[RP_CHO_ELEMENT_COUNT];
    RpStatus status;
    if (output == NULL || !valid_options(&policy)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid HP options or output.");
    }
    status = rp_ch4_o2_feed_enthalpy(feed, &enthalpy, error);
    if (status != RP_OK) { return status; }
    if (feed->oxidizer_fuel_mass_ratio < 0.1 || feed->oxidizer_fuel_mass_ratio > 20.0) {
        return rp_error_set(error, RP_OUT_OF_DOMAIN, "Gas equilibrium O/F=0.1..20.");
    }
    gas_inventory(feed->oxidizer_fuel_mass_ratio, inventory);
    return equilibrium_hp(feed->pressure_pa, inventory, enthalpy, &policy, output, error);
}

RpStatus rp_ch4_o2_equilibrium_hp_enthalpy(const RpCh4O2EnthalpyFeed *feed,
                                          const RpCombustionOptions *options,
                                          RpCombustionResult *output, RpError *error)
{
    const RpCombustionOptions policy = options != NULL ? *options : rp_combustion_default_options();
    double enthalpy;
    double inventory[RP_CHO_ELEMENT_COUNT];
    RpStatus status;
    if (output == NULL || !valid_options(&policy)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid explicit-enthalpy HP options or output.");
    }
    status = rp_ch4_o2_inlet_enthalpy(feed, &enthalpy, error);
    if (status != RP_OK) { return status; }
    gas_inventory(feed->oxidizer_fuel_mass_ratio, inventory);
    return equilibrium_hp(feed->pressure_pa, inventory, enthalpy, &policy, output, error);
}

RpStatus rp_ch4_o2_equilibrium_hp_anchor(const RpCh4O2AnchorFeed *feed,
                                         const RpCombustionOptions *options,
                                         RpCombustionResult *output, RpError *error)
{
    const RpCombustionOptions policy = options != NULL ? *options : rp_combustion_default_options();
    RpAnchorInlet inlet;
    RpStatus status;
    if (output == NULL || !valid_options(&policy)) {
        return rp_error_set(error, RP_INVALID_ARGUMENT, "Invalid fixed-anchor HP options or output.");
    }
    status = rp_ch4_o2_anchor_inlet(feed, &inlet, error);
    if (status != RP_OK) { return status; }
    return equilibrium_hp(feed->pressure_pa, inlet.element_inventory_kmol_per_kg,
                          inlet.mixture_h_j_per_kg, &policy, output, error);
}
