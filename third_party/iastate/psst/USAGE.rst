=====
Usage
=====

To use psst in a project::

    import psst


Instantiate a model
----------------

First, choose a name for your model, create a model::

    >>> from psst import Model
    >>> model = Model(name='test_model')

A psst.Model can be created with any name as a string.
A model will contain a graph attribute that
contains a `NetworkX <http://pypi.python.org/pypi/NetworkX>`_
graph allows the user to access any element.

You can create a GeneratorCompany, LoadServingEntity
and a TransmissionLine as shown below::

    >>> from psst import GeneratorCompany
    >>> from psst import LoadServingEntity
    >>> from psst import DayAheadMarket
    >>> from psst import TransmissionLine
    >>> from psst import IndependentSystemOperator
    >>> from psst import Model

    >>> test_generator1 = GeneratorCompany(name='GenCo1', location='1', c='1600', b='14', a='0.0050', minimum_capacity='0', maximum_capacity='500')

    >>> load_data1 = {1: 350.0000, 2: 322.9300, 3: 305.0400, 4: 296.0200, 5: 287.1600, 6: 291.5900, 7: 296.0200, 8: 314.0700, 9: 358.8600, 10: 394.8000, 11: 403.8200, 12: 408.2500, 13: 403.8200, 14: 394.8000, 15: 390.3700, 16: 390.3700, 17: 408.2500, 18: 448.6200, 19: 430.7300, 20: 426.1400, 21: 421.7100, 22: 412.6900, 23: 390.3700, 24: 363.4600}

    >>> test_lse1 = LoadServingEntity(name='LSE1', location='2', load_data=load_data1)

    >>> test_line1 = TransmissionLine(name='Branch1',
    >>>                               from_location=1,
    >>>                               to_location=2,
    >>>                               maximum_capacity=250,
    >>>                               reactance=0.0281)

    >>> test_model = Model(name='simpletestcase')

    >>> test_model.add_transmission_line(test_line1)

    >>> test_model.add_genco_agent(test_generator1)

    >>> test_model.add_lse_agent(test_lse1)

    >>> test_iso = IndependentSystemOperator(name='test_iso')
    >>> test_model.add_iso(test_iso)

A model can be run by calling the `run` method.::

    >>> test_model.run()

Results
-----------------

Results can be obtained by calling the `plot` function::

    >>> test_model.plot_results()

A detailed report can be generated
by looking at the `results` attribute::

    >>> test_model.results


