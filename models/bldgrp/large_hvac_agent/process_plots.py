import matplotlib.pyplot as plt


def plot_approximation(y, y_predict, name):
    fig, ax = plt.subplots()
    ax.plot(y.values, color="r", label="real")
    ax.plot(y_predict.values, color='g', label='fitted-equation')
    ax.set_title(name)
    ax.legend()
    plt.show()
