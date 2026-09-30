#ifndef ROCKETPERF_STATUS_H
#define ROCKETPERF_STATUS_H

typedef enum {
    RP_OK = 0,
    RP_INVALID_ARGUMENT,
    RP_OUT_OF_DOMAIN,
    RP_NOT_BRACKETED,
    RP_NO_CONVERGENCE,
    RP_NUMERIC_ERROR,
    RP_IO_ERROR,
    RP_PARSE_ERROR
} RpStatus;

typedef struct {
    RpStatus code;
    char message[192];
} RpError;

const char *rp_status_name(RpStatus status);
void rp_error_clear(RpError *error);
RpStatus rp_error_set(RpError *error, RpStatus status, const char *message);

#endif
