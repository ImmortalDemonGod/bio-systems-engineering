#!/usr/bin/env python3
"""
Generate charts using ONLY real measured data.
NO interpolation. NO fabrication. Shows gaps where data doesn't exist.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import numpy as np


def load_real_data():
    """Load ONLY real measured weekly data from JSON."""
    data_file = Path(__file__).parent.parent / "data" / "real_weekly_data.json"
    
    if not data_file.exists():
        raise FileNotFoundError(
            f"Real data file not found: {data_file}\n"
            "Run: python cultivation/scripts/running/get_real_metrics.py first!"
        )
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    return data


def setup_style():
    """Configure matplotlib for clean, professional charts."""
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.rcParams.update({
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 13,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.titlesize': 14,
        'axes.spines.top': False,
        'axes.spines.right': False,
    })


def generate_ef_chart(data, output_path: Path):
    """
    Generate EF chart using ONLY real measured data.
    Shows gaps where no data exists (no interpolation).
    """
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    
    # Extract measured weeks and values
    weeks = [d['week'] for d in data]
    ef_values = [d['ef_mean'] for d in data]
    run_counts = [d['num_runs'] for d in data]
    
    # Phase boundaries (for background coloring)
    phase_boundaries = {
        'A: Diagnosis': (17, 20),
        'B: Crucible': (21, 24),
        'C: Intervention': (25, 31),
        'D: Breakthrough': (32, 36),
    }
    
    phase_colors = ['#e8f4f8', '#fff4e6', '#e8f8e8', '#ffe8e8']
    
    # Draw phase backgrounds
    for (phase_name, (start, end)), color in zip(phase_boundaries.items(), phase_colors):
        ax.axvspan(start, end, alpha=0.3, color=color, zorder=0)
        mid_week = (start + end) / 2
        ax.text(mid_week, 0.0179, phase_name.split(':')[0], 
                ha='center', va='bottom', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))
    
    # Plot ONLY measured data points (with gaps)
    ax.plot(weeks, ef_values, 
            marker='o', markersize=8, linewidth=0,  # NO LINE between gaps
            color='#2563eb', label='Measured EF (Real Data)',
            markerfacecolor='#2563eb', markeredgewidth=2, markeredgecolor='white')
    
    # Draw lines only between consecutive weeks
    for i in range(len(weeks) - 1):
        if weeks[i+1] == weeks[i] + 1:  # Only connect consecutive weeks
            ax.plot([weeks[i], weeks[i+1]], [ef_values[i], ef_values[i+1]], 
                   color='#2563eb', linewidth=2, alpha=0.5)
    
    # Check for gaps (only show if data is actually missing)
    missing_weeks = [w for w in range(17, 37) if w not in weeks]
    if missing_weeks:
        # Find contiguous gaps
        gap_start = min(missing_weeks)
        gap_end = max(missing_weeks)
        ax.axvspan(gap_start, gap_end, alpha=0.15, color='gray', zorder=0)
        ax.text((gap_start + gap_end) / 2, 0.0110, f'NO DATA\n(Weeks {gap_start}-{gap_end})', 
                ha='center', va='bottom', fontsize=10, style='italic',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, 
                         edgecolor='gray', linestyle='--', linewidth=2))
    
    # Calculate phase averages from REAL data
    baseline_weeks = [d for d in data if d['week'] <= 20]
    final_weeks = [d for d in data if d['week'] >= 34]
    
    baseline_ef = sum(d['ef_mean'] for d in baseline_weeks) / len(baseline_weeks)
    final_ef = sum(d['ef_mean'] for d in final_weeks) / len(final_weeks)
    improvement = ((final_ef - baseline_ef) / baseline_ef) * 100
    
    # Baseline annotation
    ax.axhline(y=baseline_ef, xmin=0, xmax=0.15, color='gray', linestyle='--', alpha=0.7, linewidth=2)
    ax.text(17.5, baseline_ef - 0.0004, 
            f'Baseline: {baseline_ef:.4f}\n({len(baseline_weeks)} weeks, {sum(d["num_runs"] for d in baseline_weeks)} runs)', 
            fontsize=9, color='gray', va='top', ha='left')
    
    # Final annotation
    ax.axhline(y=final_ef, xmin=0.85, xmax=1.0, color='#16a34a', linestyle='--', alpha=0.7, linewidth=2)
    ax.text(35.5, final_ef + 0.0004, 
            f'Final: {final_ef:.4f}\n(+{improvement:.1f}%)', 
            fontsize=9, color='#16a34a', va='bottom', ha='right', fontweight='bold')
    
    # Labels
    ax.set_xlabel('Training Week (2025)', fontweight='bold')
    ax.set_ylabel('Efficiency Factor (m·min⁻¹·bpm⁻¹)', fontweight='bold')
    ax.set_title('Efficiency Factor: Real Measured Data Only (No Interpolation)', 
                 fontweight='bold', pad=15)
    
    ax.set_xlim(16.5, 36.5)
    ax.set_ylim(0.0110, 0.0180)
    ax.grid(True, alpha=0.2)
    
    # Legend with data points count
    legend_label = f'Measured Data ({len(weeks)} weeks, {sum(run_counts)} total runs)'
    ax.plot([], [], marker='o', markersize=8, linewidth=0, 
           color='#2563eb', markerfacecolor='#2563eb', 
           markeredgewidth=2, markeredgecolor='white', label=legend_label)
    ax.legend(loc='upper left', framealpha=0.95)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Created: {output_path}")
    plt.close()


def generate_decoupling_chart(data, output_path: Path):
    """Generate aerobic decoupling chart from real measured data."""
    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    
    # Extract weeks with decoupling data
    weeks = [d['week'] for d in data if d['decoupling_mean'] is not None]
    decouplings = [d['decoupling_mean'] for d in data if d['decoupling_mean'] is not None]
    
    # Color code by decoupling level
    colors = ['#16a34a' if d < 5 else '#f59e0b' if d < 10 else '#dc2626' 
              for d in decouplings]
    
    bars = ax.bar(weeks, decouplings, color=colors, alpha=0.7, edgecolor='white', linewidth=1.5)
    
    # Threshold line
    ax.axhline(y=5, color='#16a34a', linestyle='--', linewidth=2, alpha=0.7)
    ax.text(36.5, 5.3, '5% threshold\n(excellent)', fontsize=9, color='#16a34a', va='bottom', ha='right')
    
    # Highlight heat stress weeks if high decoupling
    if 23 in weeks:
        week_23_idx = weeks.index(23)
        if decouplings[week_23_idx] > 10:
            bars[week_23_idx].set_edgecolor('#dc2626')
            bars[week_23_idx].set_linewidth(3)
    
    ax.set_xlabel('Training Week (2025)', fontweight='bold')
    ax.set_ylabel('Aerobic Decoupling (%)', fontweight='bold')
    ax.set_title('Aerobic Decoupling: Real Measured Data', 
                 fontweight='bold', pad=15)
    
    ax.set_xlim(16.5, 36.5)
    ax.set_ylim(0, max(decouplings) * 1.2)
    ax.grid(True, alpha=0.2, axis='y')
    
    # Legend
    legend_elements = [
        mpatches.Patch(facecolor='#16a34a', alpha=0.7, label='Excellent (< 5%)'),
        mpatches.Patch(facecolor='#f59e0b', alpha=0.7, label='Moderate (5-10%)'),
        mpatches.Patch(facecolor='#dc2626', alpha=0.7, label='Poor (> 10%)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.95)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Created: {output_path}")
    plt.close()


def main():
    """Generate charts from ONLY real measured data."""
    print("="*60)
    print("GENERATING CHARTS - REAL DATA ONLY")
    print("="*60)
    print()
    
    # Load real data
    print("1. Loading real measured data...")
    data = load_real_data()
    print(f"   ✅ Loaded {len(data)} weeks with measured data")
    print(f"   Weeks: {sorted([d['week'] for d in data])}")
    print(f"   Total runs: {sum(d['num_runs'] for d in data)}")
    
    # Check how many have decoupling data
    with_decoupling = sum(1 for d in data if d['decoupling_mean'] is not None)
    print(f"   Weeks with decoupling: {with_decoupling}/{len(data)}")
    print()
    
    # Create output directory
    images_dir = Path(__file__).parent.parent / "docs" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate charts
    setup_style()
    
    print("2. Generating EF progression chart (real data only)...")
    ef_chart = images_dir / "ef_progression.png"
    generate_ef_chart(data, ef_chart)
    print()
    
    print("3. Generating aerobic decoupling chart (real data only)...")
    decoupling_chart = images_dir / "aerobic_decoupling.png"
    generate_decoupling_chart(data, decoupling_chart)
    print()
    
    # Validation
    baseline_weeks = [d for d in data if d['week'] <= 20]
    final_weeks = [d for d in data if d['week'] >= 34]
    
    baseline_ef = sum(d['ef_mean'] for d in baseline_weeks) / len(baseline_weeks)
    final_ef = sum(d['ef_mean'] for d in final_weeks) / len(final_weeks)
    improvement = ((final_ef - baseline_ef) / baseline_ef) * 100
    
    print("="*60)
    print("VALIDATION")
    print("="*60)
    measured_weeks = sorted([d['week'] for d in data])
    missing_weeks = [w for w in range(17, 37) if w not in measured_weeks]
    
    print(f"Measured weeks: {measured_weeks}")
    if missing_weeks:
        print(f"Missing weeks: {missing_weeks}")
    else:
        print(f"✅ COMPLETE: All 20 weeks have data!")
    print()
    print(f"Baseline (W17-20): {baseline_ef:.5f} ({len(baseline_weeks)} weeks, {sum(d['num_runs'] for d in baseline_weeks)} runs)")
    print(f"Final (W34-36):    {final_ef:.5f} ({len(final_weeks)} weeks, {sum(d['num_runs'] for d in final_weeks)} runs)")
    print(f"Improvement:       {improvement:+.1f}%")
    print()
    print("✅ Chart shows ONLY real measured data")
    print("✅ NO interpolation or fabrication")
    if missing_weeks:
        print("✅ Gaps clearly marked where data doesn't exist")
    else:
        print("✅ Complete longitudinal dataset (all 20 weeks)")
    print("="*60)


if __name__ == "__main__":
    main()
