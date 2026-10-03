#include "rocketperf/thermo.h"
#include "database_generated.h"

#include <stddef.h>
#include <string.h>

const RpNasa9Species *rp_thermo_find_species(const char *id)
{
    if (id == NULL) { return NULL; }
    for (size_t index = 0U; index < sizeof(rp_database_species) / sizeof(rp_database_species[0]); ++index) {
        if (strcmp(id, rp_database_species[index].id) == 0) { return &rp_database_species[index]; }
    }
    return NULL;
}

const char *rp_thermo_dataset_id(void)
{
    return RP_THERMO_DATASET_ID;
}

double rp_thermo_reference_pressure_pa(void)
{
    return 100000.0;
}
