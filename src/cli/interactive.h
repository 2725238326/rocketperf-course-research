#ifndef ROCKETPERF_CLI_INTERACTIVE_H
#define ROCKETPERF_CLI_INTERACTIVE_H

#include <stdio.h>

/* Menu-driven screen-input mode: prompts named parameters with units and
 * defaults, solves through the same public C APIs as batch commands and
 * prints human-readable reports. Returns the process exit code. */
int rp_cli_interactive(void);
/* Static list of the bundled .ini cases with run instructions. */
int rp_cli_cases(FILE *stream);

/* UTF-8 console codepage for human-readable output; no-ops off Windows.
 * Restore the returned state after writing localized text. */
typedef struct { unsigned int output_cp; unsigned int input_cp; } RpConsoleCodepage;
RpConsoleCodepage rp_cli_console_utf8(void);
void rp_cli_console_restore(RpConsoleCodepage previous);

#endif
