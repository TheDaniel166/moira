import numpy as np
import math

def build_spline_matrices(x, y):
    n = len(x)
    h = np.diff(x)
    
    # Build R (size n-2 x n-2)
    R = np.zeros((n-2, n-2))
    for i in range(n-2):
        R[i, i] = (h[i] + h[i+1]) / 3.0
        if i < n-3:
            R[i, i+1] = h[i+1] / 6.0
            R[i+1, i] = h[i+1] / 6.0
            
    # Build Q (size n x n-2)
    Q = np.zeros((n, n-2))
    for j in range(n-2):
        Q[j, j] = 1.0 / h[j]
        Q[j+1, j] = -1.0 / h[j] - 1.0 / h[j+1]
        Q[j+2, j] = 1.0 / h[j+1]
        
    return Q, R

def solve_pentadiagonal_cholesky(d, e, f, b):
    N = len(d)
    l = np.zeros(N)
    c = np.zeros(N - 1)
    g = np.zeros(N - 2)
    
    # Cholesky decomposition
    l[0] = math.sqrt(d[0])
    c[0] = e[0] / l[0]
    g[0] = f[0] / l[0]
    
    l[1] = math.sqrt(d[1] - c[0]**2)
    c[1] = (e[1] - c[0] * g[0]) / l[1]
    if N > 2:
        g[1] = f[1] / l[1]
        
    for i in range(2, N):
        val = d[i] - c[i-1]**2 - g[i-2]**2
        l[i] = math.sqrt(val)
        if i < N - 1:
            c[i] = (e[i] - c[i-1] * g[i-1]) / l[i]
        if i < N - 2:
            g[i] = f[i] / l[i]
            
    # Forward substitution: L * z = b
    z = np.zeros(N)
    z[0] = b[0] / l[0]
    z[1] = (b[1] - c[0] * z[0]) / l[1]
    for i in range(2, N):
        z[i] = (b[i] - c[i-1] * z[i-1] - g[i-2] * z[i-2]) / l[i]
        
    # Backward substitution: L^T * M = z
    M = np.zeros(N)
    M[-1] = z[-1] / l[-1]
    M[-2] = (z[-2] - c[-2] * M[-1]) / l[-2]
    for i in range(N-3, -1, -1):
        M[i] = (z[i] - c[i] * M[i+1] - g[i] * M[i+2]) / l[i]
        
    return M

def fit_smoothing_spline(x, y, p):
    n = len(x)
    Q, R = build_spline_matrices(x, y)
    
    # K = p * Q^T * Q + R
    # Since Q has 3 non-zero elements per column, Q^T @ Q is pentadiagonal
    # We can build the diagonals of K directly:
    N = n - 2
    h = np.diff(x)
    
    d = np.zeros(N)
    e = np.zeros(N - 1)
    f = np.zeros(N - 2)
    
    for j in range(N):
        # Q^T @ Q diagonal at j:
        qtq_j = 1.0 / h[j]**2 + (1.0 / h[j] + 1.0 / h[j+1])**2 + 1.0 / h[j+1]**2
        d[j] = p * qtq_j + (h[j] + h[j+1]) / 3.0
        
        if j < N - 1:
            qtq_je = -1.0 / h[j+1] * (1.0 / h[j] + 2.0 / h[j+1] + 1.0 / h[j+2])
            e[j] = p * qtq_je + h[j+1] / 6.0
            
        if j < N - 2:
            qtq_jf = 1.0 / (h[j+1] * h[j+2])
            f[j] = p * qtq_jf
            
    b = Q.T @ y
    
    M_cholesky = solve_pentadiagonal_cholesky(d, e, f, b)
    
    # Check against numpy solve
    K = p * (Q.T @ Q) + R
    M_linalg = np.linalg.solve(K, b)
    max_diff = np.max(np.abs(M_linalg - M_cholesky))
    print(f"Cholesky solver difference on real data: {max_diff:.6e}")
    
    y_hat = y - p * (Q @ M_cholesky)
    return y_hat, M_cholesky

# Let's extract raw residuals from delta_t_physical.py context
from moira.delta_t_physical import (
    _RESIDUAL_FIT_START, _RESIDUAL_TAPER_END, secular_trend,
    _modern_bridge_delta_t, fluid_lowfreq, core_delta_t, cryo_delta_t,
    _cosine_taper
)
from moira.julian import delta_t as _iers_delta_t

years_raw = []
residuals_raw = []
y = _RESIDUAL_FIT_START
while y <= _RESIDUAL_TAPER_END + 0.01:
    iers_val = _iers_delta_t(y)
    model_val = (
        secular_trend(y)
        + _modern_bridge_delta_t(y)
        + fluid_lowfreq(y)
        + core_delta_t(y)
        + cryo_delta_t(y)
    )
    years_raw.append(y)
    residuals_raw.append(iers_val - model_val)
    y += 1.0

# Mirror python delta_t_physical.py:
res_fit = residuals_raw[:]
for i in range(len(years_raw)):
    res_fit[i] *= _cosine_taper(years_raw[i])

spline_years = years_raw[:]
spline_residuals = res_fit[:]
if len(spline_years) >= 2:
    left_anchor_year = spline_years[0] - 1.0
    left_anchor_val = 2.0 * spline_residuals[0] - spline_residuals[1]
    spline_years.insert(0, left_anchor_year)
    spline_residuals.insert(0, left_anchor_val)

y_hat, M = fit_smoothing_spline(spline_years, spline_residuals, 1.483103e-01)
