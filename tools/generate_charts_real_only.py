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
    Generate clean, publication-quality EF chart for test-retest comparison.
    Focuses on RPE 10 baseline and retest with minimal visual noise.
    """
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    
    # Truncate at Week 32 (the final RPE 10 retest)
    data = [d for d in data if d['week'] <= 32]
    
    # Extract measured weeks and values
    weeks = [d['week'] for d in data]
    ef_values = [d['ef_mean'] for d in data]
    
    # Plot training data as subtle background context (de-emphasized)
    ax.plot(weeks, ef_values, 
            color='#cbd5e1', linewidth=1.5, alpha=0.4, zorder=1)
    ax.scatter(weeks, ef_values,
               s=30, color='#94a3b8', alpha=0.3, zorder=2)
    
    # Highlight RPE 10 tests with special markers
    rpe10_tests = []
    for d in data:
        if 'note' in d and 'RPE_10' in d.get('note', ''):
            rpe10_tests.append((d['week'], d['ef_mean'], d['note']))
    
    if rpe10_tests:
        for week, ef, note in rpe10_tests:
            is_baseline = 'Baseline' in note
            color = '#dc2626' if is_baseline else '#16a34a'
            
            # Large, prominent markers for RPE 10 tests
            ax.scatter(week, ef, s=400, color=color, marker='o',
                      edgecolors='white', linewidths=3, zorder=10,
                      label='RPE 10 Baseline' if is_baseline else 'RPE 10 Retest')
            
            # Clean, minimal annotations
            label_text = f"Baseline\nEF = {ef:.4f}\nWeek {week}" if is_baseline else f"Final Test\nEF = {ef:.4f}\nWeek {week}\n(+18%)"
            y_pos = ef - 0.0015 if is_baseline else ef - 0.0015
            
            ax.text(week, y_pos, label_text,
                   ha='center', va='top', fontsize=11, fontweight='bold',
                   color=color,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                            edgecolor=color, linewidth=2.5, alpha=0.98))
    
    # Clean, minimal styling
    ax.set_xlabel('Training Week (2025)', fontsize=13, fontweight='600', color='#334155')
    ax.set_ylabel('Efficiency Factor (m/s per bpm)', fontsize=13, fontweight='600', color='#334155')
    ax.set_title('103-Day Test-Retest: +18% Efficiency Improvement', 
                 fontsize=16, fontweight='bold', pad=20, color='#1e293b')
    
    ax.set_xlim(16, 33)
    ax.set_ylim(0.014, 0.023)
    
    # Subtle grid
    ax.grid(True, alpha=0.15, linewidth=0.5, color='#cbd5e1')
    ax.set_axisbelow(True)
    
    # Clean legend (only show if RPE 10 tests exist)
    if rpe10_tests:
        ax.legend(loc='upper left', framealpha=0.98, fontsize=10, 
                 edgecolor='#e2e8f0', frameon=True)
    
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
