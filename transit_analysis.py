import os
import numpy as np
import matplotlib.pyplot as plt
import lightkurve as lk

CACHE = "kepler7_raw.fits"

# Stellar radius in solar radii. Check this against the NASA Exoplanet Archive
# or Latham et al. (2010) and cite the source you use here.
RS_SUN = 1.84
RSUN_TO_RJUP = 9.73


def load_raw():
    if os.path.exists(CACHE):
        print("Loaded from local file")
        return lk.read(CACHE)
    search = lk.search_lightcurve("Kepler-7", author="Kepler", cadence="long")
    print(search)
    lc_raw = search.download_all().stitch()
    lc_raw.to_fits(CACHE, overwrite=True)
    print("Saved to", CACHE)
    return lc_raw


def main():
    lc_raw = load_raw()

    # Raw plot (replaces transit_finder.py)
    lc_raw.plot()
    plt.savefig("01_raw.png", dpi=150)
    plt.close()

    # Clean (upper outliers only, so transits survive)
    lc = (lc_raw.remove_nans()
                .flatten(window_length=901)
                .remove_outliers(sigma_upper=4, sigma_lower=float("inf")))
    lc.plot()
    plt.savefig("02_clean.png", dpi=150)
    plt.close()

    # BLS, two-stage
    print("Coarse search...")
    coarse_periods = np.linspace(1, 10, 40000)   # was 3000
    coarse = lc.to_periodogram(method="bls", period=coarse_periods, duration=[0.15])
    P0 = coarse.period_at_max_power.value
    print("Coarse period:", P0)
    coarse.plot()
    plt.savefig("03_periodogram.png", dpi=150)
    plt.close()

    print("Fine search...")
    fine_periods = np.linspace(P0 - 0.05, P0 + 0.05, 2000)
    bls = lc.to_periodogram(method="bls", period=fine_periods,
                            duration=[0.1, 0.15, 0.2])

    P = bls.period_at_max_power
    t0 = bls.transit_time_at_max_power
    dur = bls.duration_at_max_power
    depth = bls.depth_at_max_power

    # Fold
    folded = lc.fold(period=P, epoch_time=t0)
    ax = folded.scatter(alpha=0.2)
    folded.bin(time_bin_size=0.01).plot(ax=ax, color="red")
    plt.savefig("04_folded.png", dpi=150)
    plt.close()

    # Planet radius
    depth_val = abs(depth.value) if hasattr(depth, "value") else abs(depth)
    Rp_rjup = RS_SUN * np.sqrt(depth_val) * RSUN_TO_RJUP

    print(f"Period:   {P.value:.4f} d   (published ~4.885)")
    print(f"Epoch:    {t0.value:.4f} BKJD")
    print(f"Depth:    {depth_val*100:.3f} %")
    print(f"Duration: {dur.value*24:.2f} hours")
    print(f"Planet radius: {Rp_rjup:.2f} R_jup   (published ~1.6)")


if __name__ == "__main__":
    main()