#include "combustion_commands.h"
#include "arguments.h"
#include "combustion_report.h"
#include "propellant_case.h"
#include "rocketperf/numeric.h"
#include <stdio.h>
#include <string.h>

int rp_cli_propellants(int count, char **args)
{
    /* Argument-mode counterpart of the --case path: CH4_OF RP1_OF AREA_RATIO
     * AMBIENT_PA. Inlet states are the study's declared defaults (CH4 120 K /
     * O2 100 K table states at 10 MPa; RP-1 298.15 K, O2(L) 90.170 K) and the
     * common geometry is fixed at Pc=10 MPa, At=0.01 m2. */
    double values[4] = {0};
    RpPropellantComparisonInput input = {0};
    RpPropellantComparisonResult result;
    RpError error = {0};
    RpStatus status;
    int written;
    if (count != 4) { goto usage; }
    for (int i = 0; i < count; ++i) {
        const char *next;
        if (!rp_cli_parse_decimal(args[i], &next, &values[i]) || *next != '\0') { goto usage; }
    }
    input.methane = (RpContinuousLiquidFeed){rp_liquid_feed_dataset_id(), rp_liquid_feed_enthalpy_basis_id(),
        RP_LIQUID_SINGLE_PHASE, RP_LIQUID_SINGLE_PHASE, 120.0, 1e7, 100.0, 1e7, 1e7, values[0]};
    input.kerosene = (RpKeroseneAnchorFeed){rp_kerosene_dataset_id(),
        {1e7, values[1], "RP-1", "O2(L)", 298.15, 90.170, RP_FEED_LIQUID}};
    input.area_ratio = values[2]; input.ambient_pressure_pa = values[3]; input.throat_area_m2 = 0.01;
    status = rp_propellant_compare_fixed(&input, NULL, NULL, &result, &error);
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return 4;
    }
    written = rp_report_write_propellant(stdout, &input, &result, NULL);
    if (!written || fflush(stdout) != 0) {
        (void)fputs("io_error: Cannot write propellant comparison.\n", stderr); return 3;
    }
    return 0;
usage:
    (void)fputs("Usage: rocketperf study propellants CH4_OF RP1_OF AREA_RATIO AMBIENT_PA\n", stderr);
    return 2;
}

static int propellant_case_main(const char *path)
{
    RpPropellantCase study = {0};
    RpPropellantComparisonResult result;
    RpError error = {0};
    RpStatus status = rp_propellant_case_load(path, &study, &error);
    int written;
    if (status == RP_OK) { status = rp_propellant_compare_fixed(&study.input, NULL, NULL, &result, &error); }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return status == RP_PARSE_ERROR || status == RP_IO_ERROR ? 3 : 4;
    }
    written = rp_report_write_propellant(stdout, &study.input, &result, &study);
    if (!written || fflush(stdout) != 0) { (void)fputs("io_error: Cannot write propellant case report.\n", stderr); return 3; }
    return 0;
}

static int continuous_liquid_main(int count, char **args)
{
    /* hp-liquid-state / frozen-liquid-state positional layout:
     *   [0]=mode [1]=dataset [2]=basis [3]=phase [4..]=TF PF TO PO PC OF
     *   (frozen adds AREA_RATIO AMBIENT_PA THROAT_M2)
     * values[] therefore starts at the first numeric field, index 4. */
    const int fixed = count > 0 && strcmp(args[0], "frozen-liquid-state") == 0;
    double values[9] = {0};
    RpContinuousLiquidFeed feed = {0};
    RpContinuousLiquidHpResult hp = {0};
    RpContinuousLiquidFixedResult geometry = {0};
    RpError error = {0};
    RpStatus status;
    int written;
    if (count != (fixed ? 13 : 10)) { goto usage; }
    for (int i = 4; i < count; ++i) {
        const char *next;
        if (!rp_cli_parse_decimal(args[i], &next, &values[i - 4]) || *next != '\0') { goto usage; }
    }
    feed.dataset_id = args[1];
    feed.enthalpy_basis_id = args[2];
    feed.fuel_phase = strcmp(args[3], "liquid") == 0 ? RP_LIQUID_SINGLE_PHASE :
        strcmp(args[3], "two-phase") == 0 ? RP_LIQUID_TWO_PHASE : RP_LIQUID_GAS;
    feed.oxidizer_phase = feed.fuel_phase;
    feed.fuel_temperature_k = values[0]; feed.fuel_pressure_pa = values[1];
    feed.oxidizer_temperature_k = values[2]; feed.oxidizer_pressure_pa = values[3];
    feed.product_pressure_pa = values[4]; feed.oxidizer_fuel_mass_ratio = values[5];
    if (fixed) {
        status = rp_ch4_o2_continuous_liquid_hp_fixed_area(
            &feed, values[6], values[7], values[8], NULL, NULL, &geometry, &error);
        if (status == RP_OK) { hp = geometry.hp; }
    } else { status = rp_ch4_o2_continuous_liquid_hp(&feed, NULL, &hp, &error); }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return 4;
    }
    written = printf(
        "{\"schema_version\":1,\"model\":\"%s\",\"mode\":\"%s\",\"dataset_id\":\"%s\",\"liquid_dataset_id\":\"%s\","
        "\"inputs\":{\"feed_phase\":\"liquid\",\"enthalpy_basis\":\"%s\",\"fuel_temperature_k\":%.17g,"
        "\"fuel_pressure_pa\":%.17g,\"oxidizer_temperature_k\":%.17g,\"oxidizer_pressure_pa\":%.17g,"
        "\"pressure_pa\":%.17g,\"oxidizer_fuel_mass_ratio\":%.17g",
        fixed ? "ch4_o2_continuous_liquid_hp_frozen_fixed_area_v1" : "ch4_o2_continuous_liquid_hp_v1",
        args[0], rp_thermo_dataset_id(), rp_liquid_feed_dataset_id(), rp_liquid_feed_enthalpy_basis_id(),
        values[0], values[1], values[2], values[3], values[4], values[5]) >= 0;
    if (written && fixed) {
        written = printf(",\"area_ratio\":%.17g,\"ambient_pressure_pa\":%.17g,\"throat_area_m2\":%.17g",
                         values[6], values[7], values[8]) >= 0;
    }
    written = written && fputs("},\"boundary\":{\"fuel\":", stdout) >= 0 &&
        rp_report_write_liquid_state(stdout, &hp.inlet.fuel) && fputs(",\"oxidizer\":", stdout) >= 0 &&
        rp_report_write_liquid_state(stdout, &hp.inlet.oxidizer) &&
        printf(",\"fuel_mass_fraction\":%.17g,\"oxidizer_mass_fraction\":%.17g,\"inlet_mixture_h_j_per_kg\":%.17g,"
               "\"element_inventory_kmol_per_kg\":[%.17g,%.17g,%.17g],\"heat_transfer_j_per_kg\":0,"
               "\"inlet_kinetic_energy_j_per_kg\":0,\"shaft_work_j_per_kg\":0}",
               hp.inlet.fuel_mass_fraction, hp.inlet.oxidizer_mass_fraction, hp.inlet.mixture_h_j_per_kg,
               hp.inlet.element_inventory_kmol_per_kg[0], hp.inlet.element_inventory_kmol_per_kg[1],
               hp.inlet.element_inventory_kmol_per_kg[2]) >= 0 &&
        fputs(",\"chamber\":", stdout) >= 0 && rp_report_write_mixture(stdout, &hp.chamber.gas) &&
        rp_report_write_diagnostics(stdout, &hp.chamber);
    if (written && fixed) {
        written = rp_report_write_frozen_report(stdout, &geometry.nozzle.nozzle) && rp_report_write_fixed_geometry(stdout, &geometry.nozzle);
    }
    written = written && printf(
        ",\"provenance\":{\"reference_manifest_sha256\":\"%s\",\"input_role\":\"assumed_research\","
        "\"density_mass_basis\":\"CoolProp7.1.0 EOS molar mass\",\"chemical_mass_basis\":\"CEA v3.3.4 molar mass\"},"
        "\"limitations\":[\"Restricted nine-species ideal-gas products; no ions, condensed products or soot.\","
        "\"Assumed pure single-phase liquid table states; no flash, extrapolation or measured engine inlet claim.\","
        "\"HEOS enthalpy uses one CEA ideal-zero alignment; remaining ideal-cp differences are retained.\","
        "\"Inlet pressures select enthalpy, not a pump path or injector feasibility calculation.\","
        "\"Q=0 with no inlet kinetic energy or shaft work; no split-flow or full-cycle closure.\"",
        rp_liquid_feed_reference_sha256()) >= 0;
    if (written && fixed) {
        written = fputs(",\"Single fixed-area chamber-frozen inviscid nozzle; no shocks, separation or hardware losses.\"", stdout) >= 0;
    }
    written = written && fputs("]}\n", stdout) >= 0;
    if (!written || fflush(stdout) != 0) {
        (void)fputs("io_error: Cannot write continuous liquid combustion report.\n", stderr);
        return 3;
    }
    return 0;
usage:
    (void)fputs("Usage: rocketperf combustion hp-liquid-state DATASET BASIS liquid TF_K PF_PA TO_K PO_PA PC_PA OF\n"
               "       rocketperf combustion frozen-liquid-state DATASET BASIS liquid TF_K PF_PA TO_K PO_PA PC_PA OF AREA_RATIO AMBIENT_PA THROAT_M2\n", stderr);
    return 2;
}

int rp_cli_combustion(int count, char **arguments)
{
    /* One entry point, several positional layouts selected by mode:
     *   gas feed          [0]=mode [1..]=T/P, OF, TF, TO (frozen adds AREA, PA)
     *   explicit enthalpy [0]=mode [1]=basis [2]=phase [3..]=P OF HF HO
     *   anchored liquid   [0]=mode [1]=dataset [2]=phase [3]=fuel [4]=ox
     *                     [5..]=P OF TF TO (fixed adds AREA PA THROAT)
     * values[] numbering below follows each layout's first numeric argument. */
    double values[8] = {0};
    const char *mode = count > 0 ? arguments[0] : "";
    const int tp = strcmp(mode, "tp") == 0;
    const int hp = strcmp(mode, "hp") == 0;
    const int frozen = strcmp(mode, "frozen") == 0;
    const int fixed_tp = strcmp(mode, "frozen-tp") == 0;
    const int hp_h = strcmp(mode, "hp-h") == 0;
    const int fixed_h = strcmp(mode, "frozen-h") == 0;
    const int hp_anchor = strcmp(mode, "hp-liquid") == 0;
    const int fixed_anchor = strcmp(mode, "frozen-liquid") == 0;
    const int hp_rp1 = strcmp(mode, "hp-rp1") == 0;
    const int fixed_rp1 = strcmp(mode, "frozen-rp1") == 0;
    /* Flag lattice: rp1 and ch4 anchor share the assigned-liquid layout;
     * "anchor" adds fixed-geometry output, "fixed" adds a throat area. */
    const int rp1 = hp_rp1 || fixed_rp1;
    const int anchor = hp_anchor || fixed_anchor || rp1;
    const int explicit_h = hp_h || fixed_h;
    const int fixed = fixed_tp || fixed_h || fixed_anchor || fixed_rp1;
    const int assigned_tp = tp || fixed_tp;
    RpCh4O2Feed feed = {0};
    RpCh4O2EnthalpyFeed inlet = {0};
    RpCh4O2AnchorFeed liquid = {0};
    RpKeroseneAnchorFeed kerosene = {0};
    RpAnchorInlet anchor_inlet = {0};
    double inlet_enthalpy = 0.0;
    RpCombustionResult result;
    RpFrozenNozzleResult nozzle;
    RpFrozenNozzleFixedResult geometry;
    RpError error;
    RpStatus status;
    int written;
    if (strcmp(mode, "hp-liquid-state") == 0 || strcmp(mode, "frozen-liquid-state") == 0) {
        return continuous_liquid_main(count, arguments);
    }
    if ((!tp && !hp && !frozen && !fixed && !hp_h && !hp_anchor && !hp_rp1) ||
        count != (tp ? 6 : hp ? 5 : fixed_tp ? 9 : hp_h ? 7 : fixed_h ? 10 : (hp_anchor || hp_rp1) ? 9 : (fixed_anchor || fixed_rp1) ? 12 : 7)) { goto usage; }
    /* Each layout parses its own numeric slice into values[0..]. */
    for (int i = anchor ? 5 : explicit_h ? 3 : 1; i < count; ++i) {
        const char *next;
        if (!rp_cli_parse_decimal(arguments[i], &next, &values[i - (anchor ? 5 : explicit_h ? 3 : 1)]) || *next != '\0') { goto usage; }
    }
    if (anchor) {
        if (strcmp(arguments[1], rp1 ? rp_kerosene_dataset_id() : rp_anchor_dataset_id()) != 0 || strcmp(arguments[2], "liquid") != 0) {
            status = rp_error_set(&error, RP_OUT_OF_DOMAIN, "Fixed anchor requires pinned reactant dataset and liquid phase.");
        } else {
            liquid.pressure_pa = values[0]; liquid.oxidizer_fuel_mass_ratio = values[1];
            liquid.fuel_anchor_id = arguments[3]; liquid.oxidizer_anchor_id = arguments[4];
            liquid.fuel_temperature_k = values[2]; liquid.oxidizer_temperature_k = values[3];
            liquid.phase = RP_FEED_LIQUID;
            if (rp1) {
                kerosene.dataset_id = arguments[1]; kerosene.reactants = liquid;
                status = rp_kerosene_anchor_inlet(&kerosene, &anchor_inlet, &error);
                if (status == RP_OK) { status = rp_kerosene_equilibrium_hp_anchor(&kerosene, NULL, &result, &error); }
            } else {
                status = rp_ch4_o2_anchor_inlet(&liquid, &anchor_inlet, &error);
                if (status == RP_OK) { status = rp_ch4_o2_equilibrium_hp_anchor(&liquid, NULL, &result, &error); }
            }
        }
    } else if (explicit_h) {
        inlet.pressure_pa = values[0]; inlet.oxidizer_fuel_mass_ratio = values[1];
        inlet.fuel_h_j_per_kg = values[2]; inlet.oxidizer_h_j_per_kg = values[3];
        /* Unknown phase/basis are rejected by the public C inlet contract. */
        inlet.phase = strcmp(arguments[2], "gas") == 0 ? RP_FEED_GAS : RP_FEED_LIQUID;
        inlet.basis = strcmp(arguments[1], "nasa9-cea-v3.3.4") == 0 ?
            RP_ENTHALPY_NASA9_CEA_V334 : RP_ENTHALPY_UNSPECIFIED;
        status = rp_ch4_o2_inlet_enthalpy(&inlet, &inlet_enthalpy, &error);
        if (status == RP_OK) { status = rp_ch4_o2_equilibrium_hp_enthalpy(&inlet, NULL, &result, &error); }
    } else {
        /* Gas layouts: tp/frozen-tp lead with T then P; hp/frozen lead with P. */
        feed.pressure_pa = values[assigned_tp ? 1 : 0];
        feed.oxidizer_fuel_mass_ratio = values[assigned_tp ? 2 : 1];
        feed.fuel_temperature_k = values[assigned_tp ? 3 : 2];
        feed.oxidizer_temperature_k = values[assigned_tp ? 4 : 3];
        feed.phase = RP_FEED_GAS;
        status = assigned_tp ? rp_ch4_o2_equilibrium_tp(&feed, values[0], NULL, &result, &error) :
                      rp_ch4_o2_equilibrium_hp(&feed, NULL, &result, &error);
    }
    if (status == RP_OK && (frozen || fixed)) {
        RpFrozenNozzleInput input = {0};
        input.chamber_temperature_k = result.gas.temperature_k;
        input.chamber_pressure_pa = result.gas.pressure_pa;
        memcpy(input.mole_fractions, result.gas.mole_fractions, sizeof(input.mole_fractions));
        input.area_ratio = values[fixed_tp ? 5 : 4]; input.ambient_pressure_pa = values[fixed_tp ? 6 : 5];
        if (fixed) {
            status = rp_nozzle_solve_frozen_fixed_area(&input, values[fixed_tp ? 7 : 6], NULL, &geometry, &error);
            if (status == RP_OK) { nozzle = geometry.nozzle; }
        } else { status = rp_nozzle_solve_frozen(&input, NULL, &nozzle, &error); }
    }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return 4;
    }
    if (anchor) {
        written = printf("{\"schema_version\":1,\"model\":\"%s\",\"mode\":\"%s\",\"dataset_id\":\"%s\","
                         "\"reactant_dataset_id\":\"%s\",\"inputs\":{\"feed_phase\":\"liquid\","
                         "\"anchor_dataset_id\":\"%s\",\"fuel_anchor_id\":\"%s\",\"oxidizer_anchor_id\":\"O2(L)\","
                         "\"pressure_pa\":%.17g,\"oxidizer_fuel_mass_ratio\":%.17g,"
                         "\"fuel_temperature_k\":%.17g,\"oxidizer_temperature_k\":%.17g",
                         rp1 ? (fixed_rp1 ? "rp1_o2l_hp_frozen_fixed_area_v1" : "rp1_o2l_hp_assigned_v1") :
                             (fixed_anchor ? "ch4l_o2l_hp_frozen_fixed_area_v1" : "ch4l_o2l_hp_assigned_v1"),
                         mode, rp_thermo_dataset_id(), rp1 ? rp_kerosene_dataset_id() : rp_anchor_dataset_id(),
                         rp1 ? rp_kerosene_dataset_id() : rp_anchor_dataset_id(), rp1 ? "RP-1" : "CH4(L)",
                         liquid.pressure_pa, liquid.oxidizer_fuel_mass_ratio,
                         liquid.fuel_temperature_k, liquid.oxidizer_temperature_k) >= 0;
    } else if (explicit_h) {
        written = printf("{\"schema_version\":1,\"model\":\"%s\",\"mode\":\"%s\",\"dataset_id\":\"%s\","
                         "\"inputs\":{\"feed_phase\":\"gas\",\"enthalpy_basis\":\"nasa9-cea-v3.3.4\","
                         "\"pressure_pa\":%.17g,\"oxidizer_fuel_mass_ratio\":%.17g,"
                         "\"fuel_h_j_per_kg\":%.17g,\"oxidizer_h_j_per_kg\":%.17g",
                         fixed_h ? "ch4_o2_hp_enthalpy_frozen_fixed_area_v1" : "ch4_o2_hp_enthalpy_v1",
                         mode, rp_thermo_dataset_id(), inlet.pressure_pa, inlet.oxidizer_fuel_mass_ratio,
                         inlet.fuel_h_j_per_kg, inlet.oxidizer_h_j_per_kg) >= 0;
    } else {
        written = printf("{\"schema_version\":1,\"model\":\"%s\",\"mode\":\"%s\",\"dataset_id\":\"%s\","
                     "\"inputs\":{\"feed_phase\":\"gas\",\"pressure_pa\":%.17g,\"oxidizer_fuel_mass_ratio\":%.17g,"
                     "\"fuel_temperature_k\":%.17g,\"oxidizer_temperature_k\":%.17g",
                     fixed ? "ch4_o2_tp_frozen_fixed_area_v1" : frozen ? "ch4_o2_chamber_frozen_v1" : "ch4_o2_gas_equilibrium_v1", mode, rp_thermo_dataset_id(),
                         feed.pressure_pa, feed.oxidizer_fuel_mass_ratio, feed.fuel_temperature_k, feed.oxidizer_temperature_k) >= 0;
    }
    if (written && assigned_tp) { written = printf(",\"temperature_k\":%.17g", values[0]) >= 0; }
    if (written && frozen) { written = printf(",\"area_ratio\":%.17g,\"ambient_pressure_pa\":%.17g", values[4], values[5]) >= 0; }
    if (written && fixed) { written = printf(",\"area_ratio\":%.17g,\"ambient_pressure_pa\":%.17g,\"throat_area_m2\":%.17g",
                                            values[fixed_tp ? 5 : 4], values[fixed_tp ? 6 : 5], values[fixed_tp ? 7 : 6]) >= 0; }
    written = written && fputs("}", stdout) >= 0;
    if (written && explicit_h) {
        written = printf(",\"boundary\":{\"inlet_mixture_h_j_per_kg\":%.17g,\"heat_transfer_j_per_kg\":0}",
                         inlet_enthalpy) >= 0;
    }
    if (written && anchor) {
        written = printf(",\"boundary\":{\"fuel_h_j_per_kg\":%.17g,\"oxidizer_h_j_per_kg\":%.17g,"
                         "\"inlet_mixture_h_j_per_kg\":%.17g,\"heat_transfer_j_per_kg\":0,"
                         "\"pressure_correction_applied\":false,\"element_inventory_kmol_per_kg\":[%.17g,%.17g,%.17g]}",
                         anchor_inlet.fuel_h_j_per_kg, anchor_inlet.oxidizer_h_j_per_kg,
                         anchor_inlet.mixture_h_j_per_kg, anchor_inlet.element_inventory_kmol_per_kg[0],
                         anchor_inlet.element_inventory_kmol_per_kg[1], anchor_inlet.element_inventory_kmol_per_kg[2]) >= 0;
    }
    written = written && fputs(",\"chamber\":", stdout) >= 0 && rp_report_write_mixture(stdout, &result.gas) && rp_report_write_diagnostics(stdout, &result);
    if (written && (frozen || fixed)) {
        written = rp_report_write_frozen_report(stdout, &nozzle);
    }
    if (written && fixed) {
        written = rp_report_write_fixed_geometry(stdout, &geometry);
    }
    written = written && fputs(",\"limitations\":[\"Restricted nine-species ideal-gas products; no ions, condensed products or soot.\",", stdout) >= 0;
    if (written) {
        written = fputs(anchor ?
            "\"Fixed liquid reactant enthalpies only; no liquid EOS, density, pressure correction or phase-stability solve.\"," :
            "\"Gas-feed method calculation, not flight engine performance.\",", stdout) >= 0;
    }
    written = written && fputs(
                               "\"Frozen nozzle is chamber-frozen, inviscid and without shocks or separation.\"", stdout) >= 0;
    if (written && fixed) {
        written = fputs(",\"Fixed-area performance is single-nozzle only, not feed-system or full-cycle closure.\"", stdout) >= 0;
    }
    if (written && explicit_h) {
        written = fputs(",\"Inlet basis is caller-declared; no liquid properties, inlet kinetic energy or shaft work.\"", stdout) >= 0;
    }
    if (written && anchor) {
        written = fputs(",\"Pressure denotes ideal-gas product chamber pressure; no pump, shaft work or real-engine validation.\"", stdout) >= 0;
    }
    if (written && rp1) {
        written = fputs(",\"Fixed CEA RP-1 pseudo-reactant; not an identified Chinese kerosene batch.\","
                        "\"Product p=10 MPa and O/F=2.2..4.0; rich-mixture condensation is outside this method.\"", stdout) >= 0;
    }
    written = written && fputs("]}\n", stdout) >= 0;
    if (!written || fflush(stdout) != 0) {
        (void)fputs("io_error: Cannot write combustion JSON report.\n", stderr); return 3;
    }
    return 0;
usage:
    (void)fputs("Usage (gas feed, SI): rocketperf combustion tp T_K P_PA OF TF_K TO_K\n"
                "                     rocketperf combustion hp P_PA OF TF_K TO_K\n"
                "                     rocketperf combustion frozen P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA\n"
                "                     rocketperf combustion frozen-tp T_K P_PA OF TF_K TO_K AREA_RATIO AMBIENT_PA THROAT_M2\n"
                "                     rocketperf combustion hp-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG\n"
                "                     rocketperf combustion frozen-h nasa9-cea-v3.3.4 gas P_PA OF HF_JKG HO_JKG AREA_RATIO AMBIENT_PA THROAT_M2\n"
                "                     rocketperf combustion hp-liquid cea-v3.3.4-ch4l-o2l-assigned-v1 liquid CH4(L) O2(L) P_PA OF 111.643 90.170\n"
                "                     rocketperf combustion frozen-liquid cea-v3.3.4-ch4l-o2l-assigned-v1 liquid CH4(L) O2(L) P_PA OF 111.643 90.170 AREA_RATIO AMBIENT_PA THROAT_M2\n"
                "                     rocketperf combustion hp-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 O2(L) 10000000 OF 298.15 90.170\n"
                "                     rocketperf combustion frozen-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 O2(L) 10000000 OF 298.15 90.170 AREA_RATIO AMBIENT_PA THROAT_M2\n", stderr);
    return 2;
}


int rp_cli_propellant_case(const char *path)
{
    return propellant_case_main(path);
}
