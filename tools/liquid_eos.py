"""Independent coefficient evaluation for archived HEOS checks, never production."""
from __future__ import annotations

import math

from thermo_data import CEA_GAS_CONSTANT


def ideal(eos, temperature, molar_density=1.0):
    """Return alpha0, H0 and Cp0, retaining the database reference offsets."""
    reducing = eos["STATES"]["reducing"]
    tau = reducing["T"] / temperature
    delta = molar_density / reducing["rhomolar"]
    alpha, first, second = math.log(delta), 0.0, 0.0
    for term in eos["alpha0"]:
        kind = term["type"]
        if kind in ("IdealGasHelmholtzLead", "IdealGasHelmholtzEnthalpyEntropyOffset"):
            alpha += term["a1"] + term["a2"] * tau
            first += term["a2"]
        elif kind == "IdealGasHelmholtzLogTau":
            alpha += term["a"] * math.log(tau)
            first += term["a"] / tau
            second -= term["a"] / tau**2
        elif kind in ("IdealGasHelmholtzPlanckEinstein",
                      "IdealGasHelmholtzPlanckEinsteinFunctionT"):
            powers = term.get("t")
            if powers is None:
                powers = [v / term["Tcrit"] for v in term["v"]]
            for n, power in zip(term["n"], powers, strict=True):
                x = power * tau
                decay = math.exp(-x)
                denominator = -math.expm1(-x)
                alpha += n * math.log(denominator)
                first += n * power * decay / denominator
                second -= n * power**2 * decay / denominator**2
        else:
            raise ValueError("Unsupported archived ideal term: " + kind)
    gas = eos["gas_constant"]
    return dict(alpha0=alpha, h0_j_per_mol=gas*temperature*(1+tau*first),
                cp0_j_per_mol_k=gas*(1-tau**2*second))


def residual(eos, temperature, molar_density):
    """Analytic alpha_r and scaled derivatives of the pinned power/Gaussian terms."""
    reducing = eos["STATES"]["reducing"]
    tau = reducing["T"] / temperature
    delta = molar_density / reducing["rhomolar"]
    alpha, d_delta, d_tau, dd_delta = 0.0, 0.0, 0.0, 0.0
    for term in eos["alphar"]:
        kind = term["type"]
        if kind == "ResidualHelmholtzPower":
            for n, d, t, l in zip(term["n"], term["d"], term["t"], term["l"], strict=True):
                damping = delta**l if l else 0.0
                value = n * delta**d * tau**t * math.exp(-damping)
                slope = d - l*damping
                alpha += value
                d_delta += value*slope
                d_tau += value*t
                dd_delta += value*(slope**2-slope-l*l*damping)
        elif kind == "ResidualHelmholtzGaussian":
            for n, d, t, eta, beta, epsilon, gamma in zip(
                term["n"], term["d"], term["t"], term["eta"], term["beta"],
                term["epsilon"], term["gamma"], strict=True
            ):
                value = n*delta**d*tau**t*math.exp(
                    -eta*(delta-epsilon)**2-beta*(tau-gamma)**2)
                slope = d-2*eta*delta*(delta-epsilon)
                alpha += value
                d_delta += value*slope
                d_tau += value*(t-2*beta*tau*(tau-gamma))
                dd_delta += value*(slope**2-d-2*eta*delta**2)
        else:
            raise ValueError("Unsupported archived residual term: " + kind)
    return alpha, d_delta, d_tau, dd_delta


def evaluate(eos, temperature, molar_density):
    gas = eos["gas_constant"]
    zero = ideal(eos, temperature, molar_density)
    alpha, d_delta, d_tau, dd_delta = residual(eos, temperature, molar_density)
    h_residual = gas*temperature*(d_delta+d_tau)
    return dict(
        pressure_pa=molar_density*gas*temperature*(1+d_delta),
        h0_j_per_mol=zero["h0_j_per_mol"],
        h_residual_j_per_mol=h_residual,
        h_j_per_mol=zero["h0_j_per_mol"]+h_residual,
        cp0_j_per_mol_k=zero["cp0_j_per_mol_k"],
        g_j_per_mol=gas*temperature*(1+zero["alpha0"]+alpha+d_delta),
        dp_drhomolar_j_per_mol=gas*temperature*(1+2*d_delta+dd_delta),
    )


def nasa9(species, temperature):
    ranges = species["ranges"]
    interval = next((r for i, r in enumerate(ranges)
                     if r["t_min_k"] <= temperature < r["t_max_k"]
                     or i == len(ranges)-1 and temperature == r["t_max_k"]), None)
    if interval is None:
        raise ValueError("NASA9 ideal temperature outside fit")
    a = interval["coefficients"]
    t = temperature
    cp = a[0]/t**2+a[1]/t+a[2]+a[3]*t+a[4]*t**2+a[5]*t**3+a[6]*t**4
    h = -a[0]/t+a[1]*math.log(t)+a[2]*t+a[3]*t**2/2+a[4]*t**3/3+a[5]*t**4/4+a[6]*t**5/5+a[7]
    return dict(h_j_per_mol=CEA_GAS_CONSTANT/1000*h,
                cp_j_per_mol_k=CEA_GAS_CONSTANT/1000*cp)


def close(actual, expected, label, rel=2e-9, absolute=2e-5):
    if (type(actual) not in (int, float) or not math.isfinite(actual)
        or not math.isclose(actual, expected, rel_tol=rel, abs_tol=absolute)):
        raise ValueError("Liquid reference relation failed: " + label)


def coefficients_equal(actual, expected, label="fluid"):
    """Only binary64 serialization roundoff is accepted, including nested arrays."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError("Fluid coefficient object differs: " + label)
        for key, value in expected.items():
            coefficients_equal(actual[key], value, label+"."+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError("Fluid coefficient array differs: " + label)
        for i, value in enumerate(expected):
            coefficients_equal(actual[i], value, label+"."+str(i))
    elif type(expected) in (int, float):
        close(actual, expected, label, rel=5e-15, absolute=0)
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError("Fluid coefficient identity differs: " + label)
