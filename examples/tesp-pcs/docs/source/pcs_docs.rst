Prototypical Communication System (PCS)
***************************************

To build an ns-3 PCS, the ns-3 code requires a configuration file in JSON format to provide the node names and locations together with the links between. The JSON configuration files follows the current format and structure provided by the ``networkx Version 2.5`` Python module, e.g.:

.. code::
 
  object {5}
    directed : false
    multigraph : false
    graph {0}
    nodes [7089]
      0 {3}
        id : R1_12_47_1_tn_1
        nclass : node
        ndata {2}
          x : 1258.9
          y : 3153.5
      [..........]
    links [6491]
      0 {4}
        ename : line_tn_1_mtr_1
        source : R1_12_47_1_tn_1
        target : R1_12_47_1_tn_1_mtr_1
        edata {3}
          from : R1_12_47_1_tn_1
          to : R1_12_47_1_tn_1_mtr_1
          length : 0
      [...........]

This configuration file is to describe the location of and links between all the houses and DERs in a populated feeder derived from a prototypical taxonomy feeder. The edge nodes are to be placed based on the node locations extracted from the prototypical feeder visualization/graphs in ``.dot`` format at `GridLAB-D Taxonomy Feeder Graphs`_.

GridLAB-D Prototypical Taxonomy Feeder Graph VS GridLAB-D Populated Feeder
==========================================================================

The ``.dot`` graph of the GridLAB-D Prototypical Taxonomy Feeder (element 4 in :numref:`dot2feeder`) places the nodes at certain positions, which have to be translated into location coordinates for the populated feeder houses and DERs in element 2 in :numref:`dot2feeder`. Element 2 in :numref:`dot2feeder` has been obtained by populating the feeder using the ``populateFeeder`` function provided by ``tesp_support`` module to get a fully populated ``GLM`` model, after which certain objects are extracted in a JSON dictionary (element 3 in :numref:`dot2feeder`). 

.. _dot2feeder:
.. figure:: ../images/dot2feeder.png
  :scale: 30 %
  :align: center

  From graph to populated feeder dictionary

After converting the ``.dot`` graph into a JSON structure (element 5 in :numref:`dot2feeder`), the connection between the feeder population and their geographical placements (elements 3 and 5 in :numref:`dot2feeder`) is done according to :numref:`dotVSfeeder`.

.. _dotVSfeeder:
.. figure:: ../images/dotVSpopulatedFeeder.png
  :scale: 30 %
  :align: center

  Edge nodes connection to taxonomy feeder

.. important::

  - ``R1-25.00-1`` feeder, and later others, throws errors as one of the node had name '762' rather than the correct 'node762', which lead to one id being empty in the ``analyzeDOT`` function

  .. note::

    FIXED !!!!! (I think)

  - ``R3-12.47-2`` and ``GC-12.47-1`` feeders turn out to have no triplex nodes or meters, that is ``tn`` or ``tm`` IDs, which threw error because ``analyzeDOT`` cannot return ``tnNodes`` and ``tmNodes``

  .. note::

    Not fixed. Is it worth it?????

.. _GridLAB-D Taxonomy Feeder Graphs: http://emac.berkeley.edu/gridlabd/taxonomy_graphs/