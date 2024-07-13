import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly

def main2():
    energy_filename = 'ev_energy_info_diff_evtimes.csv'

    ev_demand_filename = 'controlled_ev_demand_smooth_diff_evtimes.csv'  # 'controlled_ev_demand_smooth3.csv'

    grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast2.csv'

    # energy_filename = 'ev_energy_info.csv'
    #
    # ev_demand_filename = 'controlled_ev_demand_smooth3.csv'
    #
    # grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast.csv'

    savfilename = "BatteryStoredEnergy_EVScm_GridDemand.html"

    # for energy curve
    makeflatdrop = True
    # for ev demand curve
    makeflatup = True

    year = 2040
    month = 7
    day = 11

    energy_df = pd.read_csv(energy_filename)
    ev_demand_df = pd.read_csv(ev_demand_filename)
    grid_demand_df = pd.read_csv(grid_forecast_filename)

    # energy_df = energy_df[(energy_df["day"] == 11) | (energy_df["day"] == 12)]
    # ev_demand_df = ev_demand_df[(ev_demand_df["day"] == 11) | (ev_demand_df["day"] == 12)]

    energy_df = energy_df[(energy_df["day"] == day)]
    ev_demand_df = ev_demand_df[(ev_demand_df["day"] == day)]
    grid_demand_df = grid_demand_df[(grid_demand_df["# timestamp"].dt.day == day)]
    grid_demand_df = grid_demand_df[(grid_demand_df["day"] == day)]

    days_list = list(energy_df["day"])
    hours_list = list(energy_df["hour"])

    x_values_m = [datetime(year, month, x, hours_list[idx], 0) for idx, x in enumerate(days_list)]
    x_values = np.array(x_values_m)
    x_values_ma = np.array(x_values_m)
    x_values_ma2 = np.array(x_values_m)
    if makeflatdrop:
        for i in range(1, 60):
            x_values = np.append(x_values, datetime(year, month, day, 7, i))

        for i in range(1, 60):
            x_values_ma2 = np.append(x_values_ma2, datetime(year, month, day, 18, i))
    if makeflatup:
        for i in range(1, 60):
            x_values = np.append(x_values, datetime(year, month, day, 18, i))

    idx = np.argsort(x_values)
    x_values = x_values[idx]

    idxa2 = np.argsort(x_values_ma2)
    x_values_ma2 = x_values_ma2[idxa2]

    idxa = np.argsort(x_values_ma)
    x_values_ma = x_values_ma[idxa]

    # drop days and hours columns so it does not get added in the .sum() operation
    energy_df = energy_df.drop(columns=["day", "hour"])
    ev_demand_df = ev_demand_df.drop(columns=["day", "hour"])
    grid_demand_df = grid_demand_df.drop(columns=["day", "hour", "# timestamp"])

    energy_y_values_m = energy_df.sum(axis=1) / 1000  # convert to mwh
    energy_y_values = np.array(energy_y_values_m)
    if makeflatdrop:
        for i in range(1, 60):
            energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[23])
        # energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[0])
        # for i in range(1, 60):
        #     energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[23])
    if makeflatup:
        for i in range(1, 60):
            energy_y_values = np.append(energy_y_values, np.nan)

    energy_y_values = energy_y_values[idx]

    if makeflatup:
        nans = np.isnan(energy_y_values)
        x_pioij = lambda z: z.nonzero()[0]
        energy_y_values[nans] = np.interp(x_pioij(nans), x_pioij(~nans), energy_y_values[~nans])

    energy_y_values[energy_y_values < 57] = 0

    ev_demand_y_values = ev_demand_df.sum(axis=1) / 1000  # convert to mwh
    ev_demand_y_values = np.array(ev_demand_y_values)
    if makeflatup:
        # ev_demand_y_values = np.append(ev_demand_y_values, 0)
        for i in range(1, 60):
            ev_demand_y_values = np.append(ev_demand_y_values, ev_demand_y_values[10])
    ev_demand_y_values = ev_demand_y_values[idxa2]

    ev_demand_y_values = [list(ev_demand_y_values)[-1]] + list(ev_demand_y_values)[:-1]

    grid_demand_y_values = grid_demand_df.sum(axis=1) / 1000 / 1000  # convert to mwh
    grid_demand_y_values = np.array(grid_demand_y_values)
    # if makeflatdrop:
    #     grid_demand_y_values = np.append(grid_demand_y_values, grid_demand_y_values[8])
    grid_demand_y_values = grid_demand_y_values[idxa]
    grid_demand_y_values = [x + ev_demand_y_values[fx] for fx, x in enumerate(grid_demand_y_values)]

    # fig = go.Figure()
    fig = plotly.subplots.make_subplots(rows=3, cols=1)

    fig.add_trace(go.Scatter(
        x=x_values,
        y=energy_y_values,
        name="Aggregated Stored Energy in EVs (MWh)",
        mode='lines',
        marker=dict(color='rgb(31, 119, 180)'),
        showlegend=True
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_values_ma2,
        y=ev_demand_y_values,
        name="Aggregated EV Charging (MW)",
        # yaxis="y2",
        mode='lines',
        marker=dict(color='rgb(255, 127, 14)'),
        showlegend=True
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=x_values_ma,
        y=grid_demand_y_values,
        name="Total Grid Demand (EV+Base) (MW)",
        # yaxis="y",
        mode='lines',
        line=dict(color='rgb(44, 160, 44)'),
        showlegend=True
    ), row=3, col=1)

    fig.update_layout(
        # group together boxes of the different
        # traces for each value of x
        yaxis=dict(
            # title="Aggregated Stored Energy in EVs (MWh)",
            titlefont_size=20,
            tickfont_size=16,
            titlefont=dict(
                color="#1f77b4"
            ),
            tickfont=dict(
                color="#1f77b4"
            )
        ),
        # yaxis2=dict(
        #     title="Aggregated EV Charging (MW)",
        #     titlefont_size=20,
        #     tickfont_size=16,
        #     titlefont=dict(
        #         color="#ff7f0e"
        #     ),
        #     tickfont=dict(
        #         color="#ff7f0e"
        #     ),
        #     # anchor="free",
        #     overlaying="y",
        #     side="right",
        #     # position=0.15,
        #     tickmode="sync"
        # ),
        # yaxis3=dict(
        #     title="Total Grid Demand (EV+Base) (MW)",
        #     titlefont_size=20,
        #     tickfont_size=16,
        #     titlefont=dict(
        #         color="#2ca02c"
        #     ),
        #     tickfont=dict(
        #         color="#2ca02c"
        #     ),
        #     anchor="free",
        #     overlaying="y",
        #     # side="right",
        #     tickmode="sync",
        #     autoshift=True
        # ),
        xaxis=dict(
            titlefont_size=20,
            tickfont_size=16,
        ),
        font=dict(
            family="Courier New, monospace",
            size=20,
            color="RebeccaPurple"
        ),
        paper_bgcolor='rgba(255,255,255,1)',
        plot_bgcolor='rgba(255,255,255,1)',
        boxmode='group'
    )
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black')
    # fig.show()

    plotly.offline.plot(fig,
                        filename=savfilename,
                        auto_open=True)

    # # -------------------------------------
    #
    # # Create figure with secondary y-axis
    # fig = make_subplots(specs=[[{"secondary_y": True}]])
    #
    # # Add traces
    # fig.add_trace(
    #     go.Scatter(x=x_values, y=energy_y_values, name="Aggregated Stored Energy in EVs (MWh)"),
    #     secondary_y=False,
    # )
    #
    # fig.add_trace(
    #     go.Scatter(x=x_values, y=ev_demand_y_values, name="Aggregated EV Charging (MW)"),
    #     secondary_y=True,
    # )
    #
    # # Add figure title
    # fig.update_layout(
    #     title_text="Controlled Scenario with EV Charging and Stored Energy"
    # )
    #
    # # Set x-axis title
    # fig.update_xaxes(title_text="Hour and day")
    #
    # # Set y-axes titles
    # fig.update_yaxes(title_text="Aggregated Battery Stored Energy in MWh", secondary_y=False)
    # fig.update_yaxes(title_text="Aggregated EV Charging in MW", secondary_y=True)
    #
    # fig.update_layout(
    #     # group together boxes of the different
    #     # traces for each value of x
    #     yaxis=dict(
    #         titlefont_size=20,
    #         tickfont_size=16,
    #     ),
    #     xaxis=dict(
    #         titlefont_size=20,
    #         tickfont_size=16,
    #     ),
    #     font=dict(
    #         family="Courier New, monospace",
    #         size=20,
    #         color="RebeccaPurple"
    #     ),
    #     paper_bgcolor='rgba(255,255,255,1)',
    #     plot_bgcolor='rgba(255,255,255,1)',
    #     boxmode='group'
    # )
    # fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    # fig.update_yaxes(showline=True, linewidth=2, linecolor='black')
    #
    # # fig.show()
    # plotly.offline.plot(fig,
    #                     filename=f"Battery_stored_energy.html",
    #                     auto_open=False)

    # # plot script
    # fig, ax1 = plt.subplots()
    #
    # color = 'tab:red'
    # ax1.set_xlabel('time (s)')
    # ax1.set_ylabel('Aggregated Battery Stored Energy in MWh', color=color)
    # ax1.stairs(x_values, energy_y_values, color=color)
    # ax1.tick_params(axis='y', labelcolor=color)
    #
    # ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    #
    # color = 'tab:blue'
    # ax2.set_ylabel('Aggregated EV Charging in MW', color=color)  # we already handled the x-label with ax1
    # ax2.stairs(x_values, ev_demand_y_values, color=color)
    # ax2.tick_params(axis='y', labelcolor=color)
    #
    # fig.tight_layout()  # otherwise the right y-label is slightly clipped
    # plt.show()

    k = 1

def main():
    # energy_filename = 'ev_energy_info_diff_evtimes.csv'
    #
    # ev_demand_filename = 'controlled_ev_demand_smooth_diff_evtimes.csv'  # 'controlled_ev_demand_smooth3.csv'
    #
    # grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast2.csv'

    energy_filename = 'ev_energy_info.csv'

    ev_demand_filename = 'controlled_ev_demand_smooth3.csv'

    grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast.csv'

    savfilename = "BatteryStoredEnergy_EVScm_GridDemand.html"

    # for energy curve
    makeflatdrop = True
    # for ev demand curve
    makeflatup = True

    year = 2040
    month = 7
    day = 14

    energy_df = pd.read_csv(energy_filename)
    ev_demand_df = pd.read_csv(ev_demand_filename)
    grid_demand_df = pd.read_csv(grid_forecast_filename)

    # energy_df = energy_df[(energy_df["day"] == 11) | (energy_df["day"] == 12)]
    # ev_demand_df = ev_demand_df[(ev_demand_df["day"] == 11) | (ev_demand_df["day"] == 12)]

    energy_df = energy_df[(energy_df["day"] == day)]
    ev_demand_df = ev_demand_df[(ev_demand_df["day"] == day)]
    grid_demand_df = grid_demand_df[(grid_demand_df["day"] == day)]

    days_list = list(energy_df["day"])
    hours_list = list(energy_df["hour"])

    x_values_m = [datetime(year, month, x, hours_list[idx], 0) for idx, x in enumerate(days_list)]
    x_values = np.array(x_values_m)
    x_values_ma = np.array(x_values_m)
    x_values_ma2 = np.array(x_values_m)
    if makeflatdrop:
        for i in range(1, 60):
            x_values = np.append(x_values, datetime(year, month, day, 7, i))

        for i in range(1, 60):
            x_values_ma2 = np.append(x_values_ma2, datetime(year, month, day, 18, i))
    if makeflatup:
        for i in range(1, 60):
            x_values = np.append(x_values, datetime(year, month, day, 18, i))

    idx = np.argsort(x_values)
    x_values = x_values[idx]

    idxa2 = np.argsort(x_values_ma2)
    x_values_ma2 = x_values_ma2[idxa2]

    idxa = np.argsort(x_values_ma)
    x_values_ma = x_values_ma[idxa]

    # drop days and hours columns so it does not get added in the .sum() operation
    energy_df = energy_df.drop(columns=["day", "hour"])
    ev_demand_df = ev_demand_df.drop(columns=["day", "hour"])
    grid_demand_df = grid_demand_df.drop(columns=["day", "hour", "# timestamp"])

    energy_y_values_m = energy_df.sum(axis=1) / 1000  # convert to mwh
    energy_y_values = np.array(energy_y_values_m)
    if makeflatdrop:
        for i in range(1, 60):
            energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[23])
        # energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[0])
        # for i in range(1, 60):
        #     energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[23])
    if makeflatup:
        for i in range(1, 60):
            energy_y_values = np.append(energy_y_values, np.nan)

    energy_y_values = energy_y_values[idx]

    if makeflatup:
        nans = np.isnan(energy_y_values)
        x_pioij = lambda z: z.nonzero()[0]
        energy_y_values[nans] = np.interp(x_pioij(nans), x_pioij(~nans), energy_y_values[~nans])

    energy_y_values[energy_y_values < 57] = 0

    ev_demand_y_values = ev_demand_df.sum(axis=1) / 1000  # convert to mwh
    ev_demand_y_values = np.array(ev_demand_y_values)
    if makeflatup:
        # ev_demand_y_values = np.append(ev_demand_y_values, 0)
        for i in range(1, 60):
            ev_demand_y_values = np.append(ev_demand_y_values, ev_demand_y_values[10])
    ev_demand_y_values = ev_demand_y_values[idxa2]

    ev_demand_y_values = [list(ev_demand_y_values)[-1]] + list(ev_demand_y_values)[:-1]

    grid_demand_y_values = grid_demand_df.sum(axis=1) / 1000 / 1000  # convert to mwh
    grid_demand_y_values = np.array(grid_demand_y_values)
    # if makeflatdrop:
    #     grid_demand_y_values = np.append(grid_demand_y_values, grid_demand_y_values[8])
    grid_demand_y_values = grid_demand_y_values[idxa]
    grid_demand_y_values = [x + ev_demand_y_values[fx] for fx, x in enumerate(grid_demand_y_values)]

    # fig = go.Figure()
    fig = plotly.subplots.make_subplots(rows=3, cols=1)

    fig.add_trace(go.Scatter(
        x=x_values,
        y=energy_y_values,
        name="Aggregated Stored Energy in EVs (MWh)",
        mode='lines',
        marker=dict(color='rgb(31, 119, 180)'),
        showlegend=True
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_values_ma2,
        y=ev_demand_y_values,
        name="Aggregated EV Charging (MW)",
        # yaxis="y2",
        mode='lines',
        marker=dict(color='rgb(255, 127, 14)'),
        showlegend=True
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=x_values_ma,
        y=grid_demand_y_values,
        name="Total Grid Demand (EV+Base) (MW)",
        # yaxis="y",
        mode='lines',
        line=dict(color='rgb(44, 160, 44)'),
        showlegend=True
    ), row=3, col=1)

    fig.update_layout(
        # group together boxes of the different
        # traces for each value of x
        yaxis=dict(
            # title="Aggregated Stored Energy in EVs (MWh)",
            titlefont_size=20,
            tickfont_size=16,
            titlefont=dict(
                color="#1f77b4"
            ),
            tickfont=dict(
                color="#1f77b4"
            )
        ),
        # yaxis2=dict(
        #     title="Aggregated EV Charging (MW)",
        #     titlefont_size=20,
        #     tickfont_size=16,
        #     titlefont=dict(
        #         color="#ff7f0e"
        #     ),
        #     tickfont=dict(
        #         color="#ff7f0e"
        #     ),
        #     # anchor="free",
        #     overlaying="y",
        #     side="right",
        #     # position=0.15,
        #     tickmode="sync"
        # ),
        # yaxis3=dict(
        #     title="Total Grid Demand (EV+Base) (MW)",
        #     titlefont_size=20,
        #     tickfont_size=16,
        #     titlefont=dict(
        #         color="#2ca02c"
        #     ),
        #     tickfont=dict(
        #         color="#2ca02c"
        #     ),
        #     anchor="free",
        #     overlaying="y",
        #     # side="right",
        #     tickmode="sync",
        #     autoshift=True
        # ),
        xaxis=dict(
            titlefont_size=20,
            tickfont_size=16,
        ),
        font=dict(
            family="Courier New, monospace",
            size=20,
            color="RebeccaPurple"
        ),
        paper_bgcolor='rgba(255,255,255,1)',
        plot_bgcolor='rgba(255,255,255,1)',
        boxmode='group'
    )
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black')
    # fig.show()

    plotly.offline.plot(fig,
                        filename=savfilename,
                        auto_open=True)

    # # -------------------------------------
    #
    # # Create figure with secondary y-axis
    # fig = make_subplots(specs=[[{"secondary_y": True}]])
    #
    # # Add traces
    # fig.add_trace(
    #     go.Scatter(x=x_values, y=energy_y_values, name="Aggregated Stored Energy in EVs (MWh)"),
    #     secondary_y=False,
    # )
    #
    # fig.add_trace(
    #     go.Scatter(x=x_values, y=ev_demand_y_values, name="Aggregated EV Charging (MW)"),
    #     secondary_y=True,
    # )
    #
    # # Add figure title
    # fig.update_layout(
    #     title_text="Controlled Scenario with EV Charging and Stored Energy"
    # )
    #
    # # Set x-axis title
    # fig.update_xaxes(title_text="Hour and day")
    #
    # # Set y-axes titles
    # fig.update_yaxes(title_text="Aggregated Battery Stored Energy in MWh", secondary_y=False)
    # fig.update_yaxes(title_text="Aggregated EV Charging in MW", secondary_y=True)
    #
    # fig.update_layout(
    #     # group together boxes of the different
    #     # traces for each value of x
    #     yaxis=dict(
    #         titlefont_size=20,
    #         tickfont_size=16,
    #     ),
    #     xaxis=dict(
    #         titlefont_size=20,
    #         tickfont_size=16,
    #     ),
    #     font=dict(
    #         family="Courier New, monospace",
    #         size=20,
    #         color="RebeccaPurple"
    #     ),
    #     paper_bgcolor='rgba(255,255,255,1)',
    #     plot_bgcolor='rgba(255,255,255,1)',
    #     boxmode='group'
    # )
    # fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    # fig.update_yaxes(showline=True, linewidth=2, linecolor='black')
    #
    # # fig.show()
    # plotly.offline.plot(fig,
    #                     filename=f"Battery_stored_energy.html",
    #                     auto_open=False)

    # # plot script
    # fig, ax1 = plt.subplots()
    #
    # color = 'tab:red'
    # ax1.set_xlabel('time (s)')
    # ax1.set_ylabel('Aggregated Battery Stored Energy in MWh', color=color)
    # ax1.stairs(x_values, energy_y_values, color=color)
    # ax1.tick_params(axis='y', labelcolor=color)
    #
    # ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    #
    # color = 'tab:blue'
    # ax2.set_ylabel('Aggregated EV Charging in MW', color=color)  # we already handled the x-label with ax1
    # ax2.stairs(x_values, ev_demand_y_values, color=color)
    # ax2.tick_params(axis='y', labelcolor=color)
    #
    # fig.tight_layout()  # otherwise the right y-label is slightly clipped
    # plt.show()

    k = 1

def main_plot_perfect_actual():
    energy_filename = 'ev_energy_info_diff_evtimes.csv'

    ev_demand_filename = 'controlled_ev_demand_smooth_diff_evtimes.csv'  # 'controlled_ev_demand_smooth3.csv'

    grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast2.csv'


    savfilename = "BatteryStoredEnergy_EVScm_GridDemand.html"

    # for energy curve
    makeflatdrop = False
    # for ev demand curve
    makeflatup = False

    year = 2040
    month = 7
    day = 10

    energy_df = pd.read_csv(energy_filename)
    ev_demand_df = pd.read_csv(ev_demand_filename)
    grid_demand_df = pd.read_csv(grid_forecast_filename)

    # energy_df = energy_df[(energy_df["day"] == 11) | (energy_df["day"] == 12)]
    # ev_demand_df = ev_demand_df[(ev_demand_df["day"] == 11) | (ev_demand_df["day"] == 12)]

    energy_df = energy_df[(energy_df["day"] == day)]
    ev_demand_df = ev_demand_df[(ev_demand_df["day"] == day)]
    grid_demand_df = grid_demand_df[(grid_demand_df["day"] == day)]

    days_list = list(energy_df["day"])
    hours_list = list(energy_df["hour"])

    x_values_m = [datetime(year, month, x, hours_list[idx], 0) for idx, x in enumerate(days_list)]
    x_values = np.array(x_values_m)
    x_values_ma = np.array(x_values_m)
    x_values_ma2 = np.array(x_values_m)
    if makeflatdrop:
        for i in range(1, 60):
            x_values = np.append(x_values, datetime(year, month, day, 7, i))

        for i in range(1, 60):
            x_values_ma2 = np.append(x_values_ma2, datetime(year, month, day, 18, i))
    if makeflatup:
        for i in range(1, 60):
            x_values = np.append(x_values, datetime(year, month, day, 18, i))

    idx = np.argsort(x_values)
    x_values = x_values[idx]

    idxa2 = np.argsort(x_values_ma2)
    x_values_ma2 = x_values_ma2[idxa2]

    idxa = np.argsort(x_values_ma)
    x_values_ma = x_values_ma[idxa]

    # drop days and hours columns so it does not get added in the .sum() operation
    energy_df = energy_df.drop(columns=["day", "hour"])
    ev_demand_df = ev_demand_df.drop(columns=["day", "hour"])
    grid_demand_df = grid_demand_df.drop(columns=["day", "hour", "# timestamp"])

    energy_y_values_m = energy_df.sum(axis=1) / 1000  # convert to mwh
    energy_y_values = np.array(energy_y_values_m)
    if makeflatdrop:
        for i in range(1, 60):
            energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[23])
        # energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[0])
        # for i in range(1, 60):
        #     energy_y_values = np.append(energy_y_values, np.array(energy_y_values_m)[23])
    if makeflatup:
        for i in range(1, 60):
            energy_y_values = np.append(energy_y_values, np.nan)

    energy_y_values = energy_y_values[idx]

    if makeflatup:
        nans = np.isnan(energy_y_values)
        x_pioij = lambda z: z.nonzero()[0]
        energy_y_values[nans] = np.interp(x_pioij(nans), x_pioij(~nans), energy_y_values[~nans])

    # energy_y_values[energy_y_values < 57] = 0

    ev_demand_y_values = ev_demand_df.sum(axis=1) / 1000  # convert to mwh
    ev_demand_y_values = np.array(ev_demand_y_values)
    if makeflatup:
        # ev_demand_y_values = np.append(ev_demand_y_values, 0)
        for i in range(1, 60):
            ev_demand_y_values = np.append(ev_demand_y_values, ev_demand_y_values[10])
    ev_demand_y_values = ev_demand_y_values[idxa2]

    ev_demand_y_values = [list(ev_demand_y_values)[-1]] + list(ev_demand_y_values)[:-1]

    grid_demand_y_values = grid_demand_df.sum(axis=1) / 1000 / 1000  # convert to mwh
    grid_demand_y_values = np.array(grid_demand_y_values)
    # if makeflatdrop:
    #     grid_demand_y_values = np.append(grid_demand_y_values, grid_demand_y_values[8])
    grid_demand_y_values = grid_demand_y_values[idxa]
    grid_demand_y_values = [x + ev_demand_y_values[fx] for fx, x in enumerate(grid_demand_y_values)]

    # fig = go.Figure()
    fig = plotly.subplots.make_subplots(rows=3, cols=1)

    fig.add_trace(go.Scatter(
        x=x_values,
        y=energy_y_values,
        name="Aggregated Stored Energy in EVs (MWh)",
        mode='lines',
        marker=dict(color='rgb(31, 119, 180)'),
        showlegend=True
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=x_values_ma2,
        y=ev_demand_y_values,
        name="Aggregated EV Charging (MW)",
        # yaxis="y2",
        mode='lines',
        marker=dict(color='rgb(255, 127, 14)'),
        showlegend=True
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=x_values_ma,
        y=grid_demand_y_values,
        name="Total Grid Demand (EV+Base) (MW)",
        # yaxis="y",
        mode='lines',
        line=dict(color='rgb(44, 160, 44)'),
        showlegend=True
    ), row=3, col=1)

    fig.update_layout(
        # group together boxes of the different
        # traces for each value of x
        yaxis=dict(
            # title="Aggregated Stored Energy in EVs (MWh)",
            titlefont_size=20,
            tickfont_size=16,
            titlefont=dict(
                color="#1f77b4"
            ),
            tickfont=dict(
                color="#1f77b4"
            )
        ),
        # yaxis2=dict(
        #     title="Aggregated EV Charging (MW)",
        #     titlefont_size=20,
        #     tickfont_size=16,
        #     titlefont=dict(
        #         color="#ff7f0e"
        #     ),
        #     tickfont=dict(
        #         color="#ff7f0e"
        #     ),
        #     # anchor="free",
        #     overlaying="y",
        #     side="right",
        #     # position=0.15,
        #     tickmode="sync"
        # ),
        # yaxis3=dict(
        #     title="Total Grid Demand (EV+Base) (MW)",
        #     titlefont_size=20,
        #     tickfont_size=16,
        #     titlefont=dict(
        #         color="#2ca02c"
        #     ),
        #     tickfont=dict(
        #         color="#2ca02c"
        #     ),
        #     anchor="free",
        #     overlaying="y",
        #     # side="right",
        #     tickmode="sync",
        #     autoshift=True
        # ),
        xaxis=dict(
            titlefont_size=20,
            tickfont_size=16,
        ),
        font=dict(
            family="Courier New, monospace",
            size=20,
            color="RebeccaPurple"
        ),
        paper_bgcolor='rgba(255,255,255,1)',
        plot_bgcolor='rgba(255,255,255,1)',
        boxmode='group'
    )
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black')
    # fig.show()

    plotly.offline.plot(fig,
                        filename=savfilename,
                        auto_open=True)



if __name__ == '__main__':

    # main()

    main_plot_perfect_actual()