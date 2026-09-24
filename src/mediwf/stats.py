"""Small, dependency-light statistics for MedIWF (NumPy; SciPy is used for t and chi-square tails when installed; Python 3.9).

- logistic regression by Newton-Raphson (IRLS)
- cluster-robust (sandwich) standard errors, clusters = topics
- odds ratios with Wald 95% CIs and p-values
- Benjamini-Hochberg FDR control
- Wilson score intervals and chi-square goodness of fit
Written so that every step is visible to a reviewer; results were checked against a direct likelihood maximisation.
"""
import math
import numpy as np
try:
    from scipy import stats as _sps
    from scipy.special import expit
    norm_sf = _sps.norm.sf
    def t_sf(x, df): return _sps.t.sf(x, df)
    def chi2_sf(x, df): return _sps.chi2.sf(x, df)
except ImportError:  # scipy-free fallbacks (exact for the normal; t uses the normal approximation, adequate for n >= 200;
    # chi-square exact for even df, which covers the 5-option key-position test with df = 4)
    def expit(x): return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))
    def norm_sf(x): return 0.5 * np.vectorize(math.erfc)(np.asarray(x, dtype=float) / math.sqrt(2.0))
    def t_sf(x, df): return norm_sf(x)
    def chi2_sf(x, df):
        if df % 2: raise ValueError("odd df needs scipy")
        k = df // 2; h = x / 2.0
        return math.exp(-h) * sum(h ** j / math.factorial(j) for j in range(k))


def design(df, formula_terms, categorical):
    """Build a design matrix from a pandas DataFrame.
    formula_terms: list of column names (numeric 0/1) to include as-is.
    categorical: dict {column: reference_level}; dummy columns are created for the other levels.
    Returns X (n x p), names (list)."""
    cols = [np.ones(len(df))]; names = ["intercept"]
    for t in formula_terms:
        cols.append(df[t].astype(float).values); names.append(t)
    for c, ref in categorical.items():
        levels = sorted(df[c].unique())
        for lv in levels:
            if lv == ref: continue
            cols.append((df[c] == lv).astype(float).values); names.append("%s[%s]" % (c, lv))
    return np.column_stack(cols), names


def logit_fit(X, y, max_iter=100, tol=1e-9, ridge=1e-8):
    """Newton-Raphson logistic regression. Returns beta, cov_model (inverse Hessian)."""
    n, p = X.shape
    beta = np.zeros(p)
    for _ in range(max_iter):
        mu = expit(X @ beta)
        W = mu * (1 - mu)
        H = X.T @ (X * W[:, None]) + ridge * np.eye(p)
        g = X.T @ (y - mu)
        step = np.linalg.solve(H, g)
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    mu = expit(X @ beta)
    W = mu * (1 - mu)
    H = X.T @ (X * W[:, None]) + ridge * np.eye(p)
    return beta, np.linalg.inv(H)


def cluster_robust_cov(X, y, beta, cov_model, clusters):
    """Liang-Zeger sandwich covariance with small-sample correction (G/(G-1) * (n-1)/(n-p))."""
    mu = expit(X @ beta)
    resid = (y - mu)[:, None] * X          # score contributions
    G = {}
    for c, r in zip(clusters, resid):
        G[c] = G.get(c, 0) + r
    meat = sum(np.outer(v, v) for v in G.values())
    g = len(G); n, p = X.shape
    corr = (g / (g - 1)) * ((n - 1) / (n - p))
    return corr * cov_model @ meat @ cov_model


def summarize(beta, cov, names):
    d = np.diag(cov).copy()
    d[d < 0] = np.nan          # a negative sandwich variance (separation in a nuisance dummy) is reported as nan, not as a number
    se = np.sqrt(d)
    z = beta / se
    p = 2 * norm_sf(np.abs(z))
    out = {}
    for i, nm in enumerate(names):
        out[nm] = dict(coef=beta[i], se=se[i], z=z[i], p=p[i], OR=np.exp(beta[i]),
                       OR_lo=np.exp(beta[i] - 1.96 * se[i]), OR_hi=np.exp(beta[i] + 1.96 * se[i]))
    return out


def logit_cluster(df, y, terms, categorical, cluster_col):
    X, names = design(df, terms, categorical)
    yv = df[y].astype(float).values
    beta, cov_m = logit_fit(X, yv)
    cov = cluster_robust_cov(X, yv, beta, cov_m, df[cluster_col].values)
    return summarize(beta, cov, names)


def bh_fdr(pvals):
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(pvals, dtype=float); n = len(p)
    order = np.argsort(p); ranked = np.empty(n)
    cummin = 1.0
    for i in range(n - 1, -1, -1):
        idx = order[i]
        val = min(cummin, p[idx] * n / (i + 1))
        cummin = val; ranked[idx] = val
    return ranked


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan, np.nan)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def chi2_uniform(counts, letters="ABCDE"):
    obs = np.array([counts.get(l, 0) for l in letters], dtype=float)
    n = obs.sum()
    if n == 0: return np.nan, np.nan
    exp = np.full(len(letters), n / len(letters))
    stat = ((obs - exp) ** 2 / exp).sum()
    return stat, chi2_sf(stat, len(letters) - 1)


def ols_robust(X, y, names):
    """Ordinary least squares with HC1 heteroskedasticity-robust standard errors."""
    n, p = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    meat = X.T @ (X * (resid ** 2)[:, None])
    cov = (n / (n - p)) * XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(cov)); t = beta / se
    pv = 2 * t_sf(np.abs(t), n - p)
    r2 = 1 - resid.var() / y.var()
    return {nm: dict(coef=beta[i], se=se[i], t=t[i], p=pv[i], lo=beta[i] - 1.96 * se[i], hi=beta[i] + 1.96 * se[i]) for i, nm in enumerate(names)}, r2


# ---- added 21 Sep 2026 (reviewer fixes): exact binomial bounds and bootstrap intervals for Cohen's kappa ----
def _binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p), exact (n is small in every use here)."""
    if p <= 0: return 1.0
    if p >= 1: return 1.0 if k >= n else 0.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(x, n, alpha=0.05):
    """Exact (Clopper-Pearson) two-sided confidence bounds for a binomial proportion x/n, by bisection on the exact CDF."""
    if n == 0: return float("nan"), float("nan")
    def solve(target_fn, lo, hi):
        for _ in range(60):
            mid = (lo + hi) / 2
            if target_fn(mid): lo = mid
            else: hi = mid
        return (lo + hi) / 2
    lower = 0.0 if x == 0 else solve(lambda p: 1 - _binom_cdf(x - 1, n, p) < alpha / 2, 0.0, 1.0)
    upper = 1.0 if x == n else solve(lambda p: _binom_cdf(x, n, p) > alpha / 2, 0.0, 1.0)
    return lower, upper


def kappa_from_table(tp, fp, fn, tn):
    n = tp + fp + fn + tn
    if n == 0: return float("nan")
    po = (tp + tn) / n; pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def kappa_ci(tp, fp, fn, tn, B=2000, seed=20260921):
    """Percentile bootstrap interval for Cohen's kappa. Resampling the four cell counts multinomially is identical to
    resampling the n rated pairs with replacement, so no item-level data are needed."""
    n = tp + fp + fn + tn
    if n == 0: return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(n, [tp / n, fp / n, fn / n, tn / n], size=B)
    ks = np.array([kappa_from_table(*d) for d in draws], dtype=float)
    ks = ks[np.isfinite(ks)]
    if len(ks) < B // 2: return float("nan"), float("nan")
    return float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))
