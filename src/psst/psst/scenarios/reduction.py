r"""
Scenario module

This module contains functions for operating on scenarios.

simulatenous_backward_reduction and fast_forward_selection can reduce a :math:`N` scenarios to
:math:`N_{red}`.

Algorithm based on

* http://www.mathematik.hu-berlin.de/~heitsch/ieee03ghr.pdf
* https://www.gams.com/presentations/present_IEEE03.pdf

Fast forward selection
----------------------

Compute the distances of scenario pairs:

.. math::

   c^{[1]}_{ku} := c_{T}(\xi^{k}, \xi^{u}), k, u = 1, ..., S.

Compute

.. math::

    z^{[1]}_{u} := \underset{k=1\\k \neq u}\sum{p_{k} c_{ku}^{[1]}}, u = 1, ..., S.

Choose :math:`u_{1} \in arg \underset{u \in {1, ..., S}}{\text{min }} z_{u}^{[1]}.`

Set :math:`J^{[1]} := \{ 1, ..., S \} \backslash \{ u_{1} \}`

Compute

.. math::

    c_{ku}^{[1]} := \text{min } \{ c^{[i-1]}_{ku}, c^{[i-1]}_{ku_{i-1}} \}, k, u \in J^{[i-1]}

and

.. math::

    z_{u}^{[i]} := \underset{k \in J^{[i-1] \backslash \{ u \} }}{\sum} p_{k} c_{ku}^{[i]}, u \in J^{[i-1]}.

Choose :math:`u_{i} \in arg \underset{u \in J^{[i-1]}}{\text{min }} z_{u}^{[1]}.`

Set :math:`J^{[i]} := J^{[i-1]} \backslash \{u_{i}\}.`

:math:`J := J^{[S-s]}` is the index set of deleted scenarios

Calculate probabilities as below

:math:`q_{j} := p_{j} + \underset{i \in J(j)}{\sum} p_{i}` where

:math:`J(j) := \{ i \in J : j = j(i) \}, j(i) \in arg \underset{j \notin J }{\text{min }} c_{T}(\xi^{i}, \xi^{j})`

Simultaneous backward reduction
-------------------------------

Compute the distances of scenario pairs:

.. math::

   c_{kj} := c_{T}(\xi^{k}, \xi^{j}), k, j = 1, ..., S.

Sort the records :math:`\{c_{kj} : j = 1, ..., S\}, k = 1, ..., S`

Compute

.. math::

    c^{[1]}_{ll} := \underset{j \neq l}{\text{min }} c_{lj} , l = 1, ... ,S

    z^{[1]}_{l} := p_{l}c_{ll}^{[1]}, l = 1, ..., S.

Choose :math:`l_{1} \in arg \underset{l \in {1, ..., S}}{\text{min }} z_{l}^{[1]}`

Set :math:`J^{[1]} := \{l_{1}\}`

Compute

.. math::

    c_{kj}^{i} := \underset{j \notin J^{[i-1]} \cup \{l\}}{\text{min }} c_{kj} \quad \forall l \notin J^{[i-1]}, k \in J^{[i-1]} \cup \{l\}

    z_{l}^{[i]} := \underset{k \in J^{[i-1]} \cup \{l\}}{\sum} p_{k} c_{kj}^{[i]}, \quad l \notin J^{[i-1]}
    
Choose :math:`l_{i} \in arg \underset{l \notin J^{[i-1]} }{\text{min }} z_{l}^{[i]}`

:math:`J := J^{[S-s]}` is the index set of deleted scenarios

Calculate probabilities as below

:math:`q_{j} := p_{j} + \underset{i \in J(j)}{\sum} p_{i}` where

:math:`J(j) := \{ i \in J : j = j(i) \}, j(i) \in arg \underset{j \notin J }{\text{min }} c_{T}(\xi^{i}, \xi^{j})`

"""

from __future__ import division
from __future__ import print_function

import copy
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def fast_forward_selection(scenarios, number_of_reduced_scenarios, probability=None):
    """Fast forward selection algorithm

    Parameters
    ----------
    scenarios : numpy.array
        Contain the input scenarios.
        The columns representing the individual scenarios
        The rows are the vector of values in each scenario
    number_of_reduced_scenarios : int
        final number of scenarios that
        the reduced scenarios contain.
        If number of scenarios is equal to or greater than the input scenarios,
        then the original input scenario set is returned as the reduced set
    probability : numpy.array (default=None)
        probability is a numpy.array with length equal to number of scenarios.
        if probability is not defined, all scenarios get equal probabilities

    Returns
    -------
    reduced_scenarios : numpy.array
        reduced set of scenarios
    reduced_probability : numpy.array
        probability of reduced set of scenarios
    reduced_scenario_set : list
        scenario numbers of reduced set of scenarios

    Example
    -------
    Scenario reduction can be performed as shown below::

        >>> import numpy as np
        >>> import random
        >>> scenarios = np.array([[random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)]])
        >>> import psst.scenario
        >>> reduced_scenarios, reduced_probability, reduced_scenario_numbers = psst.scenario.fast_forward_selection(scenarios, probability, 2)
    """
    print("Running fast forward selection algorithm")

    number_of_scenarios = scenarios.shape[1]
    logger.debug("Input number of scenarios = %d", number_of_scenarios)

    # if probability is not defined assign equal probability to all scenarios
    if probability is None:
        probability = np.array([1/number_of_scenarios for i in range(0, number_of_scenarios)])

    # initialize z, c and J
    z = np.array([np.inf for i in range(0, number_of_scenarios)])
    c = np.zeros((number_of_scenarios, number_of_scenarios))
    J = range(0, number_of_scenarios)

    # no reduction necessary
    if number_of_reduced_scenarios >= number_of_scenarios:
        return(scenarios, probability, J)

    for scenario_k in range(0, number_of_scenarios):
        for scenario_u in range(0, number_of_scenarios):
            c[scenario_k, scenario_u] = distance(scenarios[:, scenario_k], scenarios[:, scenario_u])

    for scenario_u in range(0, number_of_scenarios):
        summation = 0
        for scenario_k in range(0, number_of_scenarios):
            if scenario_k != scenario_u:
                summation = summation + probability[scenario_k]*c[scenario_k, scenario_u]

        z[scenario_u] = summation

    U = [np.argmin(z)]

    for u in U:
        J.remove(u)

    for _ in range(0, number_of_scenarios - number_of_reduced_scenarios - 1):
        print("Running {}".format(_))

        for scenario_u in J:
            for scenario_k in J:
                lowest_value = np.inf

                for scenario_number in U:
                    lowest_value = min(c[scenario_k, scenario_u], c[scenario_k, scenario_number])

            c[scenario_k, scenario_u] = lowest_value

        for scenario_u in J:
            summation = 0
            for scenario_k in J:
                if scenario_k not in U:
                    summation = summation + probability[scenario_k]*c[scenario_k, scenario_u]

            z[scenario_u] = summation

        u_i = np.argmin([item if i in J else np.inf for i, item in enumerate(z)])

        J.remove(u_i)
        U.append(u_i)

    reduced_scenario_set = U
    reduced_probability = []

    reduced_probability = copy.deepcopy(probability)
    for deleted_scenario_number in J:
        lowest_value = np.inf

        # find closest scenario_number
        for scenario_j in reduced_scenario_set:
            if c[deleted_scenario_number, scenario_j] < lowest_value:
                closest_scenario_number = scenario_j
                lowest_value = c[deleted_scenario_number, scenario_j]

        reduced_probability[closest_scenario_number] = reduced_probability[closest_scenario_number] + reduced_probability[deleted_scenario_number]

    reduced_scenarios = copy.deepcopy(scenarios[:, reduced_scenario_set])
    reduced_probability = reduced_probability[reduced_scenario_set]



    return reduced_scenarios, reduced_probability, reduced_scenario_set

r"""

"""


def simultaneous_backward_reduction(scenarios, number_of_reduced_scenarios, probability=None):
    """Simultaneous backward reduction algorithm

    Parameters
    ----------
    scenarios : numpy.array
        Contain the input scenarios.
        The columns representing the individual scenarios
        The rows are the vector of values in each scenario
    number_of_reduced_scenarios : int
        final number of scenarios that
        the reduced scenarios contain.
        If number of scenarios is equal to or greater than the input scenarios,
        then the original input scenario set is returned as the reduced set
    probability : numpy.array (default=None)
        probability is a numpy.array with length equal to number of scenarios.
        if probability is not defined, all scenarios get equal probabilities

    Returns
    -------
    reduced_scenarios : numpy.array
        reduced set of scenarios
    reduced_probability : numpy.array
        probability of reduced set of scenarios
    reduced_scenario_set : list
        scenario numbers of reduced set of scenarios

    Example
    -------

    Scenario reduction can be performed as shown below::

        >>> import numpy as np
        >>> import random
        >>> scenarios = np.array([[random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)],
        >>>         [random.randint(500,1000) for i in range(0,24)]])
        >>> import psst.scenario
        >>> reduced_scenarios, reduced_probability, reduced_scenario_numbers = psst.scenario.simultaneous_backward_reduction(scenarios, probability, 2)
    """

    print("Running simultaneous backward reduction algorithm")

    number_of_scenarios = scenarios.shape[1]
    logger.debug("Input number of scenarios = %d", number_of_scenarios)
    # if probability is not defined assign equal probability to all scenarios
    if probability is None:
        probability = np.array([1/number_of_scenarios for i in range(0, number_of_scenarios)])

    # initialize z, c and J
    z = np.array([np.inf for i in range(0, number_of_scenarios)])
    c = np.zeros((number_of_scenarios, number_of_scenarios))
    J = []

    # no reduction necessary
    if number_of_reduced_scenarios >= number_of_scenarios:
        return(scenarios, probability, J)

    """compute the distance of scenario pairs"""

    for scenario_k in range(0, number_of_scenarios):
        for scenario_j in range(0, number_of_scenarios):
            c[scenario_k, scenario_j] = distance(scenarios[:, scenario_k], scenarios[:, scenario_j])

    for scenario_l in range(0, number_of_scenarios):
        lowest_value = np.inf
        for scenario_j in range(0, number_of_scenarios):
            if scenario_l == scenario_j:
                continue
            lowest_value = min(lowest_value, c[scenario_l, scenario_j])

        c[scenario_l, scenario_l] = lowest_value
        z[scenario_l] = probability[scenario_l]*c[scenario_l, scenario_l]

    J.append(np.argmin(z))

    for _ in range(0, number_of_scenarios - number_of_reduced_scenarios - 1):

        for scenario_l in range(0, number_of_scenarios):
            for scenario_k in range(0, number_of_scenarios):
                if scenario_k in J or scenario_k == scenario_l:
                    if scenario_l not in J:
                        lowest_value = np.inf
                        for scenario_j in range(0, number_of_scenarios):
                            if scenario_j not in J and scenario_j != scenario_l:
                                lowest_value = min(lowest_value, c[scenario_k, scenario_j])

                        c[scenario_k, scenario_l] = lowest_value

        for scenario_l in range(0, number_of_scenarios):
            if scenario_l not in J:
                summation = 0

                for scenario_k in range(0, number_of_scenarios):
                    if scenario_k in J or scenario_k == scenario_l:
                        summation = summation + probability[scenario_k]*c[scenario_k, scenario_l]

                z[scenario_l] = summation

        J.append(np.argmin([item if i not in J else np.inf for i, item in enumerate(z)]))

    reduced_scenario_set = []
    for scenario_number in range(0, number_of_scenarios):
        if scenario_number not in J:
            reduced_scenario_set.append(scenario_number)

    reduced_probability = []

    reduced_probability = copy.deepcopy(probability)
    for deleted_scenario_number in J:
        lowest_value = np.inf

        # find closest scenario_number
        for scenario_j in reduced_scenario_set:
            if c[deleted_scenario_number, scenario_j] < lowest_value:
                closest_scenario_number = scenario_j
                lowest_value = c[deleted_scenario_number, scenario_j]

        reduced_probability[closest_scenario_number] = reduced_probability[closest_scenario_number] + reduced_probability[deleted_scenario_number]

    reduced_scenarios = copy.deepcopy(scenarios[:, reduced_scenario_set])
    reduced_probability = reduced_probability[reduced_scenario_set]
    return(reduced_scenarios, reduced_probability, reduced_scenario_set)

def distance(a, b):
    """Euclidean distance between two vectors"""
    # from scipy.spatial import distance
    # return(distance.euclidean(a, b))
    return(np.linalg.norm(a-b))



