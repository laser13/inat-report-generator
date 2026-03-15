"""Chart generation with Matplotlib."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

matplotlib.use("Agg")

MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.grid": True,
            "grid.alpha": 0.3,
            "font.size": 11,
        }
    )


def chart_monthly_observations(monthly: pd.DataFrame, output_path: Path, year: int) -> Path:
    """Bar chart of monthly observation counts."""
    _setup_style()
    fig, ax = plt.subplots(figsize=(10, 5))
    months = monthly["month"].astype(int)
    labels = [MONTH_NAMES[m - 1] for m in months]
    ax.bar(labels, monthly["observations"], color="#2ecc71", edgecolor="white", linewidth=0.5)
    ax.set_title(f"Monthly Observations ({year})", fontsize=14, fontweight="bold")
    ax.set_ylabel("Observations")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def chart_cumulative_species(df: pd.DataFrame, output_path: Path, year: int) -> Path:
    """Line chart of cumulative species richness over the year."""
    _setup_style()
    sorted_df = df[df["scientific_name"].notna()].sort_values("observed_on")
    seen: set[str] = set()
    cumulative: list[int] = []
    for month in range(1, 13):
        month_species = sorted_df[sorted_df["observed_month"] == month]["scientific_name"].unique()
        seen.update(month_species)
        cumulative.append(len(seen))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(MONTH_NAMES, cumulative, marker="o", color="#3498db", linewidth=2, markersize=6)
    ax.fill_between(MONTH_NAMES, cumulative, alpha=0.15, color="#3498db")
    ax.set_title(f"Cumulative Species Richness ({year})", fontsize=14, fontweight="bold")
    ax.set_ylabel("Unique Species")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def chart_yearly_dynamics(dynamics: pd.DataFrame, output_path: Path, title: str) -> Path:
    """Multi-panel chart showing year-over-year dynamics."""
    _setup_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    years = dynamics["year"].astype(str).tolist()

    # 1. Observations per year
    ax = axes[0, 0]
    ax.bar(years, dynamics["observations"], color="#2ecc71", edgecolor="white")
    ax.set_title("Observations per Year", fontweight="bold")
    ax.set_ylabel("Observations")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # 2. Observers per year
    ax = axes[0, 1]
    ax.bar(years, dynamics["observers"], color="#3498db", edgecolor="white")
    ax.set_title("Observers per Year", fontweight="bold")
    ax.set_ylabel("Observers")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # 3. Species per year + new species
    ax = axes[1, 0]
    ax.bar(years, dynamics["species"], color="#e67e22", edgecolor="white", label="Total species")
    ax.bar(years, dynamics["new_species"], color="#e74c3c", edgecolor="white", label="New species")
    ax.set_title("Species per Year", fontweight="bold")
    ax.set_ylabel("Species")
    ax.legend(fontsize=9)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # 4. Cumulative species
    ax = axes[1, 1]
    ax.plot(years, dynamics["cumulative_species"], marker="o", color="#9b59b6", linewidth=2)
    ax.fill_between(years, dynamics["cumulative_species"], alpha=0.15, color="#9b59b6")
    ax.set_title("Cumulative Species Discovery", fontweight="bold")
    ax.set_ylabel("Total Unique Species")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Rotate year labels on all axes
    for ax_row in axes:
        for ax in ax_row:
            ax.tick_params(axis="x", rotation=45)

    fig.suptitle(f"{title} — Year-over-Year Dynamics", fontsize=16, fontweight="bold", y=1.02)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def chart_top_species(top_species: pd.DataFrame, output_path: Path, year: int) -> Path:
    """Horizontal bar chart of top species by observation count."""
    _setup_style()
    fig, ax = plt.subplots(figsize=(10, max(6, len(top_species) * 0.4)))
    species = top_species["scientific_name"].tolist()[::-1]
    counts = top_species["count"].tolist()[::-1]
    ax.barh(species, counts, color="#e67e22", edgecolor="white", linewidth=0.5)
    ax.set_title(f"Top Species by Observations ({year})", fontsize=14, fontweight="bold")
    ax.set_xlabel("Observations")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
