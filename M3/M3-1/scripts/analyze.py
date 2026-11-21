import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--logs', default='logs')
    parser.add_argument('--out', default='results')
    args = parser.parse_args()
    logs, out = Path(args.logs), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runs = json.loads((logs/'runs.json').read_text())
    if len(runs) < 10:
        raise RuntimeError('At least ten actual laps required')
    lines = ['# Actual Gazebo closed-loop measurements', '', '| Run | Odom closure m | Truth closure m | Odom heading deg | Truth heading deg |', '|---|---:|---:|---:|---:|']
    for run in runs:
        lines.append('| {lap} | {odom_position_error_m:.6f} | {truth_position_error_m:.6f} | {odom_angle_error_deg:.5f} | {truth_angle_error_deg:.5f} |'.format(**run))
    stats = {}
    for key in ['odom_position_error_m','truth_position_error_m','odom_angle_error_deg','truth_angle_error_deg']:
        values = [run[key] for run in runs]
        stats[key] = {'mean': float(np.mean(values)), 'sample_std': float(np.std(values, ddof=1)), 'n': len(values)}
        lines.append('\n%s: %.6f +/- %.6f (sample SD, n=%d)' % (key, np.mean(values), np.std(values, ddof=1), len(values)))
    (out/'closed_loop_stats.md').write_text('\n'.join(lines))
    (out/'statistics.json').write_text(json.dumps(stats, indent=2))
    fig, ax = plt.subplots(figsize=(7,6))
    for source, color in [('truth','green'),('odom','red')]:
        rows = np.genfromtxt(logs/('run_01_'+source+'.csv'), delimiter=',', names=True)
        xy = np.column_stack((rows['x']-rows['x'][0], rows['y']-rows['y'][0]))
        theta = rows['theta'][0]
        rotation = np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
        xy = xy@rotation
        ax.plot(xy[:,0], xy[:,1], color=color, label=source)
        ax.scatter(xy[-1,0],xy[-1,1],color=color,marker='x',s=70,label=source+' end')
    ax.scatter(0,0,color='black',label='start')
    ax.set_aspect('equal', adjustable='box')
    ax.set(xlabel='x (m)', ylabel='y (m)', title='2 m rounded square: actual Gazebo vs wheel odometry')
    first=runs[0]
    ax.text(.5,.48,
        'Run 1 closure\nTruth: %.4f m / %.2f deg\nOdom: %.4f m / %.2f deg' % (
            first['truth_position_error_m'],first['truth_angle_error_deg'],
            first['odom_position_error_m'],first['odom_angle_error_deg']),
        transform=ax.transAxes,ha='center',va='center',fontsize=10,
        bbox=dict(boxstyle='round,pad=.6',facecolor='white',edgecolor='#ced8dd',alpha=.95))
    ax.legend(); ax.grid(True)
    fig.tight_layout(); fig.savefig(out/'trajectory_compare.png',dpi=160)
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
