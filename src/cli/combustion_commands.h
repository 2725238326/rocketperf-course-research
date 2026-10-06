#ifndef ROCKETPERF_COMBUSTION_COMMANDS_H
#define ROCKETPERF_COMBUSTION_COMMANDS_H

int rp_cli_combustion(int count, char **arguments);
int rp_cli_propellants(int count, char **arguments);
int rp_cli_propellant_case(const char *path);

#endif
