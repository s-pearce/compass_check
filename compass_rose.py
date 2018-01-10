# compass rose plots for glider compass checks

import matplotlib.pyplot as plt
import numpy as np


def glider_compass_plot(true_directions, measured_directions):
    ax = plt.subplot(111, polar=True)
    ax.set_theta_direction(-1)
    ax.set_theta_offset(0.5 * np.pi)

    def compass_plot(deg, clr, lw=2):
        rad = np.deg2rad(deg)
        ax.plot([rad, rad], [0, 1], color=clr, linewidth=lw)

    # show the nominal directionals
    for td in true_direction:
        compass_plot(td, 'b', lw=1)

    for heading in measured_direction:
        compass_plot(heading, 'r')

    plt.title('You choose')
    plt.show()