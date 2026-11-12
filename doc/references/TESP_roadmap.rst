Development Roadmap
===================

To assist the development team and help TESP users where we see TESP
developing, the TESP development team has created a development roadmap.
The roadmap is expressed as a git graph where “main” is used to
represent completed work and each area of activity is shown as a named
branch in the graph. (Note that the names of the branches in this
roadmap do not necessarily correspond to the branches in the `TESP
Github repository <https://github.com/pnnl/tesp>`__.)The deadline for any task is
shown by a merge back into the “main” branch prior to a
calendar quarter end date (*e.g.* “Dec 31, 2026”). Note that
because this is a git graph and not a Gantt chart, we show only when the
activity is completed (the quarter it is due) and not when it began.

The activities for the upcoming quarters are most likely to be accurate
with the fidelity of the plan decreasing the further into the future of
the planned activities. Even for activities planned in the near future,
circumstances and changing priorities of the `Transactive Systems
Program <https://www.pnnl.gov/projects/transactive-systems-program>`__
as a whole may change planned activities. Which
is to say, the published roadmap reflects the TESP’s development team’s
priorities as of the latest revision but nothing is ever set in stone.

Current Plan (Last updated Oct 2026)
------------------------------------

.. mermaid::

   %%{init: { 'logLevel': 'debug',  'gitGraph': {'rotateCommitLabel': 'false'}, 'themeVariables': {'commitLabelFontSize': '16px'}} }%%
   gitGraph TB:
    %% Recent Activity
    checkout main
    commit id: "Previous work"
    branch agent
    checkout agent
      commit id: "Agent architecture and implementation"
      commit id: "d1"
    checkout main
    merge agent

    commit id: "FY27"
    commit id: "v1.3.8"
    branch TESP_v2


    
     

    %% FY27Q1 activity and deliverables
    checkout TESP_v2
    branch arch_des
    checkout arch_des
      commit id: "System operator and execution architecture"
    checkout TESP_v2
      merge arch_des
    checkout main
      merge TESP_v2 id: "Jan 4, 2027"


    %% FY27Q2 activity and deliverables
    checkout TESP_v2
    branch execution
    checkout execution
      commit id: "Execution framework implementation"
    checkout TESP_v2
      merge execution
    checkout main
      merge TESP_v2 id: "April 5, 2027"
    
    %% FY27Q3 activity and deliverables
    checkout TESP_v2
    branch system_operator
    checkout system_operator
      commit id: "TSO implementation"
      commit id: "DSO implementation"
    
    checkout agent
      commit id: "Grid asset agent implementation"
    checkout TESP_v2
      merge system_operator
      merge agent
    checkout main
      merge TESP_v2 id: "July 6, 2027"
  

    %% FY27Q4 activity and deliverables
    checkout TESP_v2
    commit id: "TSO+DSO demonstration"
    commit id: "d2"
    commit id: "d3"
    checkout main
      merge TESP_v2 id: "Sept 30, 2027"
    commit id: "v1.4"




     %% FY28 activity and deliverable
    merge TESP_v2 id: "FY28 or later"
    checkout main
    branch sim_tools
    checkout sim_tools
      commit id: "Add PySO+Egret support"
    checkout TESP_v2
      commit id: "Validate feeder generator"
      commit id: "Feeder generator publication"
    checkout main
    







