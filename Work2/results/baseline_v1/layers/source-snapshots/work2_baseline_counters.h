#ifndef WORK2_BASELINE_COUNTERS_H
#define WORK2_BASELINE_COUNTERS_H

/* Research-only, single-process counters. Never linked into production. */
typedef struct {
    unsigned long long tp_calls;
    unsigned long long temperature_solves;
    unsigned long long gibbs_vectors;
    unsigned long long equilibrium_nasa9_calls;
    unsigned long long residual_jacobian_evaluations;
    unsigned long long newton_steps;
    unsigned long long linear_solves;
    unsigned long long line_search_trials;
    unsigned long long backtrack_reductions;
    unsigned long long warm_attempts;
    unsigned long long warm_successes;
    unsigned long long cold_starts;
    unsigned long long cold_fallbacks;
    unsigned long long hp_trials;
    unsigned long long mixture_evaluations;
} RpBaselineCounters;

extern RpBaselineCounters rp_baseline_counters;

#endif
