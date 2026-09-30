#include "case_file.h"
#include "rocketperf/version.h"

#include <locale.h>
#include <stdio.h>
#include <string.h>

static int cli_main(int argc, char **argv)
{
    RpCase study;
    RpNozzleResult result;
    RpError error = {0};
    RpStatus status;
    (void)setlocale(LC_NUMERIC, "C");
    if (argc == 2 && strcmp(argv[1], "--version") == 0) {
        (void)printf("rocketperf %s\n", RP_VERSION);
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        (void)puts("Usage: rocketperf run CASE.ini\n       rocketperf --version\nThe v1 model accepts synthetic benchmarks/research scenarios, not verified engine datasets.");
        return 0;
    }
    if (argc != 3 || strcmp(argv[1], "run") != 0) {
        (void)fputs("Usage: rocketperf run CASE.ini (or --help / --version)\n", stderr);
        return 2;
    }
    status = rp_case_load(argv[2], &study, &error);
    if (status == RP_OK) { status = rp_nozzle_solve_ideal(&study.input, NULL, &result, &error); }
    if (status == RP_OK) { status = rp_case_write_json(stdout, &study, &result, &error); }
    if (status == RP_OK && fflush(stdout) != 0) {
        status = rp_error_set(&error, RP_IO_ERROR, "Cannot flush JSON report.");
    }
    if (status != RP_OK) {
        (void)fprintf(stderr, "%s: %s\n", rp_status_name(status), error.message);
        return status == RP_PARSE_ERROR || status == RP_IO_ERROR ? 3 : 4;
    }
    return 0;
}

#ifdef _WIN32
#include <windows.h>
#include <stdlib.h>

int wmain(int argc, wchar_t **wide_argv);
int wmain(int argc, wchar_t **wide_argv)
{
    char **argv = calloc((size_t)argc + 1U, sizeof(*argv));
    int code = 3;
    if (argv == NULL) { (void)fputs("io_error: Cannot allocate arguments.\n", stderr); return code; }
    for (int i = 0; i < argc; ++i) {
        const int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide_argv[i], -1, NULL, 0, NULL, NULL);
        if (size <= 0 || (argv[i] = malloc((size_t)size)) == NULL ||
            WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide_argv[i], -1, argv[i], size, NULL, NULL) == 0) {
            (void)fputs("io_error: Cannot encode arguments as UTF-8.\n", stderr);
            goto cleanup;
        }
    }
    code = cli_main(argc, argv);
cleanup:
    for (int i = 0; i < argc; ++i) { free(argv[i]); }
    free(argv);
    return code;
}
#else
int main(int argc, char **argv)
{
    return cli_main(argc, argv);
}
#endif
