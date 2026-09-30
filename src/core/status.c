#include "rocketperf/status.h"

#include <stdio.h>

const char *rp_status_name(RpStatus status)
{
    switch (status) {
    case RP_OK: return "ok";
    case RP_INVALID_ARGUMENT: return "invalid_argument";
    case RP_OUT_OF_DOMAIN: return "out_of_domain";
    case RP_NOT_BRACKETED: return "not_bracketed";
    case RP_NO_CONVERGENCE: return "no_convergence";
    case RP_NUMERIC_ERROR: return "numeric_error";
    case RP_IO_ERROR: return "io_error";
    case RP_PARSE_ERROR: return "parse_error";
    default: return "unknown_status";
    }
}

void rp_error_clear(RpError *error)
{
    if (error != NULL) {
        error->code = RP_OK;
        error->message[0] = '\0';
    }
}

RpStatus rp_error_set(RpError *error, RpStatus status, const char *message)
{
    if (error != NULL) {
        error->code = status;
        (void)snprintf(error->message, sizeof(error->message), "%s", message);
    }
    return status;
}
