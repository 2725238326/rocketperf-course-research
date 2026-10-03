#include "case_file.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static unsigned int checks;
static unsigned int failures;
#define CHECK(condition) do { ++checks; if (!(condition)) { ++failures; (void)fprintf(stderr, "line %d: %s\n", __LINE__, #condition); } } while (0)

int main(void)
{
    RpCase study = {"adapter_test", "research_scenario", "source\n\t\001\\\"",
        {1.4, 287.0, 300.0, 1e6, 1.6875, 0.001, 0.0}};
    RpNozzleResult result;
    RpError error = {0};
    double ratios[] = {1.6875};
    double pressures[] = {0.0, 200000.0};
    RpNozzleStudyGrid grid = {ratios, 1U, pressures, 2U};
    RpNozzleStudyPoint points[2];
    size_t count = 0U;
    FILE *stream;
    char text[8192];
    size_t length;
    CHECK(rp_nozzle_solve_ideal(&study.input, NULL, &result, &error) == RP_OK);
    CHECK(rp_nozzle_scan_area_ratio_ambient(&study.input, &grid, points, 2U, &count, &error) == RP_OK);
    stream = tmpfile();
    CHECK(stream != NULL);
    if (stream == NULL) { return 1; }
    result.thrust_n = NAN;
    CHECK(rp_case_write_json(stream, &study, &result, &error) == RP_INVALID_ARGUMENT);
    CHECK(ftell(stream) == 0L);
    CHECK(rp_nozzle_solve_ideal(&study.input, NULL, &result, &error) == RP_OK);
    memset(study.id, 'x', sizeof(study.id));
    CHECK(rp_case_write_json(stream, &study, &result, &error) == RP_INVALID_ARGUMENT);
    CHECK(ftell(stream) == 0L);
    (void)strcpy(study.id, "adapter_test");
    points[0].result.thrust_n = INFINITY;
    CHECK(rp_case_write_study_json(stream, &study, &grid, points, count, &error) == RP_INVALID_ARGUMENT);
    CHECK(ftell(stream) == 0L);
    points[0].result = result;
    points[0].area_ratio = 2.0;
    CHECK(rp_case_write_study_json(stream, &study, &grid, points, count, &error) == RP_INVALID_ARGUMENT);
    points[0].area_ratio = ratios[0];
    memset(points[1].message, 'x', sizeof(points[1].message));
    CHECK(rp_case_write_study_json(stream, &study, &grid, points, count, &error) == RP_INVALID_ARGUMENT);
    (void)strcpy(points[1].message, "excluded\npoint");
    pressures[0] = NAN;
    CHECK(rp_case_write_study_json(stream, &study, &grid, points, count, &error) == RP_INVALID_ARGUMENT);
    pressures[0] = 0.0;
    CHECK(rp_case_write_study_json(stream, &study, &grid, points, count - 1U, &error) == RP_INVALID_ARGUMENT);
    CHECK(ftell(stream) == 0L);
    CHECK(rp_case_write_study_json(stream, &study, &grid, points, count, &error) == RP_OK);
    CHECK(fflush(stream) == 0);
    CHECK(fseek(stream, 0L, SEEK_SET) == 0);
    length = fread(text, 1U, sizeof(text) - 1U, stream);
    text[length] = '\0';
    CHECK(strstr(text, "source\\u000a\\u0009\\u0001") != NULL);
    CHECK(strstr(text, "excluded\\u000apoint") != NULL);
    CHECK(fclose(stream) == 0);
    (void)printf("adapters: %u checks, %u failures\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
