/* GENERATED from pinned NASA CEA v3.3.4 thermo.inp; do not hand-edit. */
#ifndef RP_REACTANTS_GENERATED_H
#define RP_REACTANTS_GENERATED_H
#define RP_ANCHOR_DATASET_ID "cea-v3.3.4-ch4l-o2l-assigned-v1"
typedef struct {
    const char *id;
    double molar_mass_kg_per_kmol;
    double temperature_k;
    double enthalpy_j_per_mol;
    double elements[3];
} RpAssignedReactant;
static const RpAssignedReactant rp_assigned_reactants[2] = {
    {"CH4(L)", 16.042459999999998, 111.643, -89233, {1, 4, 0}},
    {"O2(L)", 31.998799999999999, 90.170000000000002, -12979, {0, 0, 2}}
};
#endif
