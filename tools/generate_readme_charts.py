#!/usr/bin/env python3
"""
Generate Charts for README

Creates publication-quality charts for embedding in README.md
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import numpy as np


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


def generate_ef_progression_chart(df: pd.DataFrame, output_path: Path):
    """
    Generate Efficiency Factor progression chart with phase annotations.
    
    Args:
        df: DataFrame with columns: week, ef_mean
        output_path: Where to save the PNG
    """
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    
    # Phase boundaries
    phase_boundaries = {
        'A: Diagnosis': (17, 20),
        'B: Crucible': (21, 24),
        'C: Intervention': (25, 31),
        'D: Breakthrough': (32, 36),
    }
    
    # Phase colors (subtle backgrounds)
    phase_colors = ['#e8f4f8', '#fff4e6', '#e8f8e8', '#ffe8e8']
    
    # Draw phase backgrounds
    for (phase_name, (start, end)), color in zip(phase_boundaries.items(), phase_colors):
        ax.axvspan(start, end, alpha=0.3, color=color, zorder=0)
        # Phase label
        mid_week = (start + end) / 2
        ax.text(mid_week, 0.0193, phase_name.split(':')[0], 
                ha='center', va='bottom', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))
    
    # Plot EF progression
    ax.plot(df['week'], df['ef_mean'], 
            marker='o', markersize=6, linewidth=2.5, 
            color='#2563eb', label='Efficiency Factor',
            markerfacecolor='white', markeredgewidth=2, markeredgecolor='#2563eb')
    
    # Highlight key events
    # Week 23: Heat stress (lowest EF in Phase B)
    heat_week = 23
    heat_ef = df[df['week'] == heat_week]['ef_mean'].values[0]
    ax.scatter([heat_week], [heat_ef], s=150, color='#dc2626', 
               marker='v', zorder=10, edgecolors='white', linewidths=2,
               label='Heat Stress (32°C)')
    
    # Week 35: Peak performance
    peak_week = 35
    peak_ef = df[df['week'] == peak_week]['ef_mean'].values[0]
    ax.scatter([peak_week], [peak_ef], s=150, color='#16a34a', 
               marker='^', zorder=10, edgecolors='white', linewidths=2,
               label='Peak Performance')
    
    # Baseline and final annotations
    baseline_ef = df[df['week'] == 17]['ef_mean'].values[0]
    final_ef = df[df['week'] == 35]['ef_mean'].values[0]
    improvement = ((final_ef - baseline_ef) / baseline_ef) * 100
    
    ax.axhline(y=baseline_ef, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(17.5, baseline_ef - 0.0002, f'Baseline: {baseline_ef:.4f}', 
            fontsize=9, color='gray', va='top')
    
    ax.axhline(y=final_ef, color='#16a34a', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(34.5, final_ef + 0.0002, f'Final: {final_ef:.4f} (+{improvement:.1f}%)', 
            fontsize=9, color='#16a34a', va='bottom', ha='right')
    
    # Labels and formatting
    ax.set_xlabel('Training Week (2025)', fontweight='bold')
    ax.set_ylabel('Efficiency Factor (m·min⁻¹·bpm⁻¹)', fontweight='bold')
    ax.set_title('Efficiency Factor Progression: 103-Day Longitudinal Study', 
                 fontweight='bold', pad=15)
    
    ax.set_xlim(16.5, 36.5)
    ax.set_ylim(0.0154, 0.0194)
    ax.grid(True, alpha=0.2)
    ax.legend(loc='upper left', framealpha=0.95)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Created: {output_path}")
    plt.close()


def generate_decoupling_chart(df: pd.DataFrame, output_path: Path):
    """
    Generate Aerobic Decoupling chart showing thermal resilience.
    
    Args:
        df: DataFrame with columns: week, decoupling_mean
        output_path: Where to save the PNG
    """
    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    
    # Plot decoupling
    weeks = df['week'].values
    decoupling = df['decoupling_mean'].values
    
    # Color code by decoupling level
    colors = ['#16a34a' if d < 5 else '#f59e0b' if d < 10 else '#dc2626' 
              for d in decoupling]
    
    bars = ax.bar(weeks, decoupling, color=colors, alpha=0.7, edgecolor='white', linewidth=1.5)
    
    # Threshold line (5% = good coupling)
    ax.axhline(y=5, color='#16a34a', linestyle='--', linewidth=2, alpha=0.7, 
               label='< 5% (Excellent Coupling)')
    ax.text(36.5, 5.3, '5% threshold', fontsize=9, color='#16a34a', va='bottom', ha='right')
    
    # Highlight heat stress event
    heat_week_idx = list(weeks).index(23)
    bars[heat_week_idx].set_edgecolor('#dc2626')
    bars[heat_week_idx].set_linewidth(3)
    ax.text(23, 20.5, 'Heat Stress\n32.3°C', ha='center', fontsize=9, 
            fontweight='bold', color='#dc2626',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9))
    
    # Labels
    ax.set_xlabel('Training Week (2025)', fontweight='bold')
    ax.set_ylabel('Aerobic Decoupling (%)', fontweight='bold')
    ax.set_title('Aerobic Decoupling: Heat Resilience Breakthrough', 
                 fontweight='bold', pad=15)
    
    ax.set_xlim(16.5, 36.5)
    ax.set_ylim(0, 22)
    ax.grid(True, alpha=0.2, axis='y')
    
    # Custom legend
    from matplotlib.lines import Line2D
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
    """Generate all README charts."""
    print("=== Generating README Charts ===")
    print("")
    
    # Load sample weekly data
    data_path = Path(__file__).parent.parent / "data" / "sample" / "weekly_metrics.csv"
    df = pd.read_csv(data_path)
    
    # Create docs/images directory
    images_dir = Path(__file__).parent.parent / "docs" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup plotting style
    setup_style()
    
    # Generate charts
    print("1. Generating EF progression chart...")
    ef_chart_path = images_dir / "ef_progression.png"
    generate_ef_progression_chart(df, ef_chart_path)
    print("")
    
    print("2. Generating aerobic decoupling chart...")
    decoupling_chart_path = images_dir / "aerobic_decoupling.png"
    generate_decoupling_chart(df, decoupling_chart_path)
    print("")
    
    print("✅ Chart generation complete!")
    print("")
    print(f"Charts saved to: {images_dir}")
    print("  - ef_progression.png")
    print("  - aerobic_decoupling.png")
    print("")
    print("These charts are now ready to embed in README.md")


if __name__ == "__main__":
    main()
