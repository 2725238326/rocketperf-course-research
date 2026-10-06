#ifndef ROCKETPERF_CLI_ARGUMENTS_H
#define ROCKETPERF_CLI_ARGUMENTS_H

/* Decimal token terminated by a comma, whitespace or end of input. */
int rp_cli_parse_decimal(const char *start, const char **next, double *output);

#endif
