
# ---------------------------------------------------------
# 
# ---------------------------------------------------------

def draw_growth_arrow(ax, df, target_idx, compare_idx, label, color, offset_y):
    if target_idx < len(df) and compare_idx >= 0 and compare_idx < len(df):
        val_target = df.iloc[target_idx]['Revenue']
        val_compare = df.iloc[compare_idx]['Revenue']
        if val_target and val_compare and val_compare != 0:
            pct = (val_target / val_compare) * 100
            ax.annotate('', xy=(target_idx, val_target), xytext=(compare_idx, val_compare),
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=2, ls="--", connectionstyle="arc3,rad=-0.25"), zorder=4)
            mid_x, mid_y = (target_idx + compare_idx) / 2, (val_target + val_compare) / 2 + offset_y
            ax.text(mid_x, mid_y, f"{label}\n{pct:.1f}%", color=color, fontsize=9, weight='bold', ha='center', va='center', zorder=5,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, lw=1, alpha=0.9))
