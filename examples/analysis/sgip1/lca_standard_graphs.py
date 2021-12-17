# @Author: Allison Campbell <camp426>
# @Date:   2020-10-13T18:53:01-07:00
# @Email:  allison.m.campbell@pnnl.gov
# @Last modified by:   camp426
# @Last modified time: 2021-11-09T14:20:18-08:00



import pandas as pd
import numpy as np
import seaborn as sns
import pdb
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
import matplotlib.ticker as ticker


def build_comparison_table(dfs, names, fillna=None, column_name='Scenarios'):
    """ Simple function to combine dataframes in a multi-index comparison table

    Parameters
    ----------
    dfs : list of pandas dataframes to be compared
    names : list of names to assign to each dataframe
        Labels to distinguish each dataframe's respective data in the compiled comparison table
    fillna: None (default), or float
        Value with which to replace any potential NaN instance
    column_name : string
        Name of multi-index level that holds the `names` values.

    Returns
    -------
    comp: dataframe
        A comparison dataframe

    """

    for i, df in enumerate(dfs):
        # Add the name of each dataframe for disambiguation
        df.insert(0, column_name, names[i], allow_duplicates=True)

    # Concatenate
    comp = pd.concat(dfs, sort=False)
    #comp.sort_index(inplace=True)
    comp.set_index(column_name, append=True, inplace=True)

    if fillna is not None:
        comp.fillna(fillna, inplace=True)

    return comp
#palette_def=('pastel', 'deep', 'dark')
def plot_grouped_stackedbars(df, ix_categories, ix_entities_compared, norm='max', err_pos=None, err_neg=None,
                             palette_def=('pastel', 'deep', 'dark'), width=0.3, figsize=(8, 4), xaxis_label='',
                             yaxis_label='',saveplot='',format_dollars=False):
    """ Grouped stacked-bars for both comparison and contribution analysis

    This plot groups bars, representing the total scores of different entities
    [ix_entities_compared] in terms of multiple comparison categories
    [ix_categories], while at the same time breaking down these total scores
    into contribution analysis.

    For example, compare two vehicles (ix_entities_compared) in terms of
    climate change and resource depletion impacts (ix_categories), and break
    down their total impacts in terms of multiple lifecycle stages, such as the
    contribution of vehicle production, use phase and end-of-life treatment.

    The function uses a color polette to distinguish between lifecycle stages,
    and increasingly darker variants of this palette (from pastel, to deep, to
    dark, by default) to distinguish between the technologies/scenarios
    being compared (ix_entities_compared).

    All colour palettes must be defined explicitly. For comparisons involving
    many compared entities (>3), it may be more convenient to use
    `plot_grouped_stackedbar_wlargegroups()`, which automatically generates the
    shading gradient. Unfortunately, this function does not allow for the
    definition of error margins (confidence intervals).


    Parameters
    ----------

    df : pandas multi-index dataframe, as generated from build_comparsison_table()

        The DataFrame must be multi-index, with one index level indicating the
        comparison category/criteria, and another level indicating the entities
        being compared. All columns must represent an element of the
        contribution analysis

        Important: ALL columns in the dataframe must be relevant for the
        contribution analysis, except those that are singled out as defining
        confidence intervals (`err_pos`, `err_neg`). All other columns should
        be removed or used as indexes

    ix_categories : string
        The name of the index level that holds the categories/criteria for the
        comparison. For example, types of life cycle impacts

    ix_entities_compared : string
        The name of the index level that holds the entities being compared,
        such as competing products, technologies, or scenarios

    norm : None or string {'max' | index of reference entity }
        If Norm is None, the stacked bars are not being normalized

        If norm == 'max' (default): Within each comparison categories, the
        different entities are normalized relative to the entity with the
        largest score.

        If norm is the index of a specific reference entity, all other
        entities are normalized relative to that one.

    err_neg, err_pos: None, or string
        The name of the column that holds the negative and positive errors
        associated with the total sum of each row of df values
        If None, no error bars will be drawn

    palette_def: tupple of matplotlib or seaborn "categorical" palette definitions
        These palettes should present the same colors, but with different
        lightness levels, forming a gradient from lightest to darkest.

    width : float
        The width of the bars.

    figsize : tuple
        The width and height of figure

    xaxis_label : string
        The label/title of the x-axis

    Returns
    -------
    ax, fig : matplotlib axes and figure

    See Also
    --------
    Depends on internal functions _normalize_impacts() and _generate_legend()

    """

    # Alternative approach (maybe simpler for just two scenarios):
    # https://stackoverflow.com/questions/40121562/clustered-stacked-bar-in-python-pandas

    # Hardcoded
    edgecolor = 'k'
    transparent = (0, 0, 0, 0)

    # Test that there are not too many entities compared.
    if len(df.index.get_level_values(ix_entities_compared).unique()) > 3:
        print("Warning. Too many entities being compared. Please use `plot_grouped_stackedbars_wlargegroups()` instead.")
        return None

    # Normalize
    if norm is not None:
        if norm == 'max':
            df = _normalize_impacts(df, ix_categories, ix_entities_compared,
                                    donotsumbutnormalize=(err_neg, err_pos))
        else:
            df = _normalize_impacts(df, ix_categories, ix_entities_compared, ref=norm,
                                    donotsumbutnormalize=(err_neg, err_pos))

    # Initializations. Creates two subplots, the first one (ax) for the actual figure, and the second (ax2) as dummy to
    # display the legend without this legend overlapping with the plot but still within the bounds of the figure.
    # width_ratios is dummy ratio to make second plot very small
    fig, (ax, ax2) = plt.subplots(1, 2, gridspec_kw = {'width_ratios':[100, 1]},
                                  facecolor='white', figsize=figsize)
    # make dummy axis disapear
    ax2.get_yaxis().set_ticks([])
    ax2.axis('off')

    # All compared entities, in order of appearance
    all_entities = df.index.get_level_values(ix_entities_compared).unique()
    all_contributions = [i for i in df.columns if i not in [err_neg, err_pos]]

    # Determine number of entities, portions, and colors
    n_entities_compared = len(all_entities)
    n_palettes = len(palette_def)

    # Define palettes
    palettes = []
    if n_entities_compared <= n_palettes:
        for i in range(n_palettes - n_entities_compared, n_palettes):
            palettes += [sns.color_palette(palette_def[i])]
    else:
        palettes = None

    # Loop over all entities compared
    for i, ent in enumerate(all_entities):

        # Subset of contribution data for this loop
        sub = df.xs(ent, axis=0, level=ix_entities_compared)[all_contributions]

        if err_pos:
            # Error bar data fro this loop, if applicable
            err = df.xs(ent, axis=0, level=ix_entities_compared)[[err_neg, err_pos]].values.T
        else:
            err = None

        # Plot horizontal bar
        sub.plot.bar(ax=ax, stacked=True, position=i, width=width, zorder=-1,
                      color=sns.color_palette(palettes[i]), edgecolor=edgecolor, label='_nolegend_')

        # Plot over this bar with a transparent bar, to add the confidence interval
        sub.sum(1).plot.bar(ax=ax, position=i, width=width, color=transparent, xerr=err, label='_nolegend_')

        if i == n_entities_compared - 1:

            # Generate the legend complement explaining about shading
            #legend_elements = _generate_legend(all_entities)

            # Integrate in legend and plot legend
            handles, labels = ax.get_legend_handles_labels()
            handles2 = handles[-len(all_contributions):] #+ legend_elements
            order = [2,1,0]
            plt.legend([handles[idx] for idx in order],[labels[idx] for idx in order])

            print(handles2)
    # Legend definition (hidden in first subplot, but displayed in second)
    ax.get_legend().remove()
    ax2.legend(handles=[handles2[idx] for idx in order], loc='center left', bbox_to_anchor=(0, 0.5),prop={"size":16})

    # Axis title
    #ax.xaxis.set_label_text(xaxis_label)
    #ax.yaxis.set_label_text(yaxis_label)

    if format_dollars:
        formatter = ticker.FormatStrFormatter('$%1.2f')
        ax.yaxis.set_major_formatter(formatter)
    ax.grid(which='major', axis='y', linestyle='--', zorder=0)
    ax.set_xlabel(xaxis_label,fontsize=16)
    ax.set_ylabel(yaxis_label,fontsize=16)
    ax.tick_params(labelsize=14)

    # Rescale
    ax.autoscale()  # Important to not have the bars come right up to th edge of figure
    fig.tight_layout() # Important to not have labels and legend extend beyond figure

    if len(saveplot)>0:
        plt.savefig(saveplot)

    return ax, fig


def plot_grouped_stackedbars_wlargegroups(df, ix_categories, ix_entities_compared, norm='max', orient='h',
                                         palette_def=('pastel', 'deep', 'dark')):
    """ Grouped stacked-bars for both comparison and contribution analysis

    Group bars, representing the total scores of different compared entities
    [ix_entities_compared] around multiple comparison categories
    [ix_categories], while at the same time breaking down these totals into
    contribution analysis.

    For example, compare two vehicles (ix_entities_compared) in terms of
    climate change and resource depletion (ix_categories), and break down their
    total impacts in terms of multiple lifecycle stages, such as vehicle
    production, use phase and end-of-life treatment.

    Parameters
    ----------

    df : DataFrame, following a specific format
        The DataFrame must be multi-index, with one index level indicating the
        comparison category/criteria, and another level indicating the entities
        being compared. All columns must represent an element of the
        contribution analysis

    ix_categories : string
        The name of the index level that holds the categories/criteria for the
        comparison. For example, types of life cycle impacts

    ix_entities_compared : string
        The name of the index level that holds the entities being compared,
        such as competing products, technologies, or scenarios

    norm : None or string {'max' | index of reference entity }
        If Norm is None, the stacked bars are not being normalized

        If norm == 'max', within each comparison categories, the different
        entities are normalized relative to the largest contributor

        If norm is the index of a reference entity, all other
        entities are normalized relative to that one.

    orient : string {'h' | 'v'}
        Whether to have horizontal ('h') or vertical ('v') bar graph

    palette_def: tupple of matplotlib or seaborn "categorical" palette definitions
        These palettes should present the same colors, but with different
        lightness levels, forming a gradient from lightest to darkest.


    Returns
    -------

    fig : matplotlib figure object
    ax :  matplotlib axis object


    See Also
    --------

    This function is really the sequential application of three internal
    functions: `_normalize_impacts()`, `_calc_cumsum_tidy_df`, and
    `_plot_grouped_stackedbars_from_tidycumsum`.

    """

    # Whether to normalize dataframe rows, and if so relative to either the
    # rowsum of a specific entity (from index) or the entity with the maximum
    # rowsum for each category
    if norm is not None:
        if norm == 'max':
            df = _normalize_impacts(df,
                                    ix_categories=ix_categories,
                                    ix_ref_level=ix_entities_compared)
        else:
            df = _normalize_impacts(df,
                                    ix_categories=ix_categories,
                                    ix_ref_level=ix_entities_compared,
                                    ref=norm)

    # Calculate the row-wise cummulative sum in the dataframe, as a trick to
    # make a stacked bar graph
    df = _calc_cumsum_tidy_df(df, var_name='stages')

    # Make grouped stacked bar contribution-comparison graph
    ax, fig = _plot_grouped_stackedbars_from_tidycumsum(df,
                                                        categories=ix_categories,
                                                        stacked_portions='stages',
                                                        values='value',
                                                        entities_compared=ix_entities_compared,
                                                        orient=orient,
                                                        palette_def=palette_def)
    return ax, fig


def plot_stochastic_comparison(scen1, scen2, name1, name2, palette='deep'):
    """ Plot the probability that scenario 1 or 2 have lower impacts

    Parameters
    ----------
    scen1, scen2 : Pandas DataFrames
        With impacts as indexes, defining the comparison categories, and with
        stochastic iterations as columns

    name1, name2 : string
        Names to identify the scenarios to be compared, i.e. those in scen1 and
        scen2

    palette : seaborn or matplotlib color palette to use


    Returns
    -------
    ax, fig : matplotlib axes and figure

    """

    # Initialize and get dimensions
    n_iter = scen1.shape[1]
    prob_better = pd.DataFrame(index=scen1.index, columns=[name1, name2])

    # Perform calculation as numpy array (50x faster)
    scen2 = scen2.reindex_like(scen1)
    scen1 = scen1.values
    scen2 = scen2.values

    # calculate probability of scen1 being better than scen2 for all impact categories
    prob_better.loc[:, name1] = -1 * ((scen1 < scen2).sum(1) + 0.5 * (scen1 == scen2).sum(1)) / n_iter * 100

    # And vice versa
    # note: we calculate the probability of scenario2 < scenario1 independently.
    #       this could be done more efficiently with `100% - prob_better.loc[:, name1]`,
    #       but it has the potential of hiding failures. For example if a whole row is zero by mistake
    #       (NaN issue, etc.), we want both scenarios at 0%, not accidently ascribe 100% to scenario2
    #       as the residual
    prob_better.loc[:, name2] = ((scen1 > scen2).sum(1) + 0.5 * (scen1 == scen2).sum(1)) / n_iter * 100

    # Plotting
    fig = plt.figure(facecolor='white')
    ax = plt.subplot(111)
    prob_better.plot.barh(ax=ax,
                          stacked=True,
                          color=sns.color_palette(palette),
                          edgecolor='k')

    # Make the x-axis stretch from 100% Scenario 1 to 100% Scenario 2
    ax.set_xlim(-100, 100)

    # Vertical line at 0%
    ax.axvline(color='k', linewidth=1)

    # Get rid of negative values in axis labels, turn into positive integers
    xticklabels = [str(abs(int(i))) for i in ax.get_xticks()]
    ax.set_xticklabels(xticklabels)

    # Label and legend
    ax.set_ylabel('')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2),  ncol=2, fancybox=True)

    fig.tight_layout() # Important to not have labels and legend extend beyond figure
    return ax, fig


def _normalize_impacts(df, ix_categories, ix_ref_level, ref=None, donotsumbutnormalize=('err_neg', 'err_pos')):
    """ Express the score of each entity as percentage of one specific entity

    Parameters
    ----------

    df: Multi-index Pandas DataFrame
        Indexes on categories (e.g. different environmental impacts) and on
        compared entities (e.g., technologies, scenarios). Columns are
        contributions to the total score of each category (e.g., lifecycle
        stages).

    ix_categories: string
        Name of index level containing the categories in terms of which the
        compared entities are quantified

    ix_ref_level: string
        Name of index levels containing the compared entities

    ref : None or string
        If None, normalize relative to the entity with the highest score in
        each category

        If string, should be the index of the entity against which to normalize
        all others

    donotsumbutnormalize: tuple
        All columns that do not contribute to the total but should also be
        normalized

    Returns
    -------

    df: Normalized dataframe

    """

    # Identify all non-error columns

    stages = list(set(df.columns) - set(donotsumbutnormalize))

    if ref:
        # Normalize values for all entities in all categories, relative to one
        # selected reference entity (ref)
        ref_imp = df.xs(ref, axis=0, level=ix_ref_level)[stages].sum(axis=1)

    else:
        # Normalize values for all entities based on the entity with the
        # highest row-sum for each category
        grouped_levels = list({i for i in df.index.names} - {ix_categories})
        ref_imp = df[stages].sum(axis=1).reset_index(grouped_levels, drop=True).groupby(ix_categories).max()

    # Reindex the resulting reference values, to allow for "broadcast" division
    ref_imp = ref_imp.reindex(df.index, level=ix_categories)

    # Divide the dataframe row-wise, for a normalized result
    return df.divide(ref_imp, axis=0) * 100


def _calc_cumsum_tidy_df(df, var_name='stages'):
    """ Prepares a dataframe for grouped stacked-bar plotting

    Turn rows into a cummulative sum, to cheat our way into plotting stacked
    bars

    To facilitate plotting in seaborn, `melt()` the dataframe such that it
    becomes a tidy dataframe.

    Parameters
    ----------

    df : Multi-index Pandas dataframe
        As generated by by `build_comparison_table()`

    var_name: string, optional
        Name to give to the new column in the tidy dataframe that holds all
        melted original columns

        For example, if the columns of the original `df` defined life-cycle
        stages, the newly formed column might be named 'stages'

    Return
    ------

    Tidy dataframe with values expressed as cummulative sums

    """

    # Turn each row in to a sequential cummulative sum
    df = df.cumsum(axis=1)

    # Save names of indexes, and reset
    ix_names = df.index.names
    df = df.reset_index()

    # Turn into a tidy format
    return df.melt(id_vars=ix_names, var_name=var_name)


def _plot_grouped_stackedbars_from_tidycumsum(cumsum_df, categories, stacked_portions, values, entities_compared,
                                              orient='h', palette_def=('pastel', 'deep', 'dark')):
    """ Plotting function behind `plot_grouped_stackedbar_comparison()`

      Mode 2) If the number of entities is greater than the number of defined palettes,
      a single palette is used to define the 'color' arguments of seaborn
      barplots, leaving seaborn to determine the lightness gradient. The first
      entity in the comparison is typically too light, but a large number of
      bars together makes it clear to interpret regardless.



    Parameters
    ----------

    cumsum_df : Pandas DataFrame, as generated from _calc_cumsum_tidy_df()

    categories : string
        The name of the column that holds the categories/criteria for the
        comparison. For example, types of life cycle impacts

    entities_compared : string
        The name of the column that holds the entities being compared,
        such as competing products, technologies, or scenarios

    stacked_portions : string
        the name of the column that holds the sections of the stacked bar

    values : float
        The name of the column with the values that determine the size of each
        section in stacked bars.

    orient : string {'h' | 'v'}
        Whether to have horizontal ('h') or vertical ('v') bar graph

    palette_def: tupple of matplotlib or seaborn "categorical" palette definitions
        These palettes should present the same colors, but with different
        lightness levels, forming a gradient from lightest to darkest.

    """

    # Alternative approach (maybe simpler for just two scenarios):
    # https://stackoverflow.com/questions/40121562/clustered-stacked-bar-in-python-pandas

    # Initializations
    fig = plt.figure(facecolor='white')
    ax = plt.subplot(111)
    legend_elements = []

    # Determine number of entities, portions, and colors
    n_entities_compared = len(set(cumsum_df[entities_compared]))
    n_stacked_portions = len(set(cumsum_df[stacked_portions]))
    n_palettes = len(palette_def)

    # Define colors, in case this function is run as "Mode 2"
    colors = sns.color_palette(palette_def[-1], n_colors=n_stacked_portions)

    # Define palettes if this function is run as "Mode 1"
    palettes = []
    if n_entities_compared <= n_palettes:
        for i in range(n_palettes - n_entities_compared, n_palettes):
            palettes += [sns.color_palette(palette_def[i], n_colors=n_stacked_portions)]
    else:
        palettes = None

    # Swap x and y axes, for vertical or horizontal bars, depending
    if orient == 'h':
        x = values
        y = categories
    else:
        x = categories
        y = values

    # Loop over all stacked proportions, to plot each in order, on over the
    # other, creating the illusion of stacked bars
    for i, j in enumerate(cumsum_df[stacked_portions].unique()):

        # Select the right data for this loop
        bo = cumsum_df[stacked_portions] == j
        g = cumsum_df.loc[bo]

        # Sort out the right color or palette, depending on number of entities
        # compared relative ot the number of predefined palettes
        if n_entities_compared > n_palettes:
            color = colors[i]
            palette = None
        else:
            color = None
            palette = [p[i] for p in palettes]

        ax = sns.barplot(data=g, x=x, y=y, hue=entities_compared, color=color, palette=palette,
                         zorder=n_stacked_portions - i, edgecolor="k", ci=None)

        if i == 0:
            legend_elements = _generate_legend(g[entities_compared].unique())
        try:
            legend_elements += [Patch(facecolor=palette[-1], label=j), ]
        except TypeError:
            legend_elements += [Patch(facecolor=color, label=j), ]

    # Remove context-dependent stuff
    ax.legend_.remove()  # remove the redundant legends
    ax.xaxis.set_label_text('')
    ax.yaxis.set_label_text('')

    legend_elements.reverse()
    plt.legend(handles=legend_elements,
               bbox_to_anchor=(1, 0.5),
               bbox_transform=fig.transFigure,
               loc="center left")

    return ax, fig


def _generate_legend(entities):
    """ Generate legend explaining shading in grouped_stackbar graphs, based on order and number of entities compared

    Handles either two entities (light & dark), three entities (light medium and dark), or more.
    In this last case, it generates a single entry stating the order of the gradient (lightest to darkest).

    Parameters
    ----------
    entities : list
        List of strings of names of the entities being compared, in the order that they are processed

    Returns
    -------
    legend_element : matplotlib legend
    """

    legend_elements = []

    if len(entities) > 3:
        legend_elements += [Patch(edgecolor='black',
                                  facecolor='white',
                                  label="Gradient: {} (lightest), {}, {} (darkest)".format(entities[0],
                                                                                           ', '.join(entities[1: -1]),
                                                                                           entities[-1]))]

    else:

        legend_elements += [Patch(edgecolor='black',
                                  facecolor='white',
                                  label='light colors: ' + entities[0])]
        if len(entities) == 3:
            legend_elements += [Patch(edgecolor='black',
                                      facecolor='white',
                                      label='medium colors: ' + entities[1])]

        legend_elements += [Patch(edgecolor='black',
                                  facecolor='white',
                                  label='dark colors: ' + entities[-1])]
    return legend_elements


# It might be pertinent to define and lighten/darken colormaps ourselves:
# https://scipy-cookbook.readthedocs.io/items/Matplotlib_ColormapTransformations.html
