Development Roadmap
===================

To assist the development team and help TESP users where we see TESP
developing, the TESP development team has created a development roadmap.
The roadmap is expressed as a git graph where “main” is used to
represent completed work and each area of activity is shown as a named
branch in the graph. (Note that the names of the branches in this
roadmap do not necessarily correspond to the branches in the `TESP
Github repository <https://github.com/pnnl/tesp>`__.) As of summer of
2025, the TESP team is moving to planning on a quarterly basis with key
deliverables or milestones on this cadence. The deadline for any task is
shown by a merge back into the “main” branch prior to a
fiscal-year-and-quarter end-date (*e.g.* “Dec 31, 2025”). Note that
because this is a git graph and not a Gantt chart, we show only when the
activity is completed (the quarter it is due) and not when it began.

The activities for the upcoming quarters are most likely to be accurate
with the fidelity of the plan decreasing the further into the future of
the planned activities. Even for activities planned in the near future,
circumstances and changing priorities of the `Transactive Systems
Program <https://www.pnnl.gov/projects/transactive-systems-program>`__
as a whole may change planned activities even in the near future. Which
is to say, the published roadmap reflects the TESP’s development team’s
priorities as of the latest revision but nothing is ever set in stone.

Current Plan (Last updated Aug 2025)
------------------------------------

.. mermaid::

   %%{init: { 'logLevel': 'debug',  'gitGraph': {'rotateCommitLabel': 'false'}, 'themeVariables': {'commitLabelFontSize': '16px'}} }%%
   gitGraph TB:
     commit id: "FY25"
     commit id: "v1.3.6"
     branch maintenance
     branch comm_engagement
     branch use_case_support
     branch TESP_v2



     %% FY25Q4 activity and deliverable
     checkout use_case_support
       commit id: "Verify glm_dsot"
     checkout maintenance
       commit id: "Release prep v1.3.7"
     checkout main
       merge maintenance id: "v1.3.7"
       merge use_case_support id: "Sept 30, 2025"

     %% FY26Q1 activity and deliverable
     checkout use_case_support
       commit id: "Migrate DSOT to use-case repo"
     checkout main
       merge use_case_support id: "Dec 31, 2025"


     %% FY26Q2 activity and deliverable
     checkout use_case_support
       commit id: "Migrate consensus to use-case repo"
     checkout maintenance
       commit id: "Set up CI/CD on Github"
     checkout TESP_v2
       branch agents
       commit id: "Implement testing for HVAC agent"
       checkout TESP_v2
       merge agents
     branch arch_des
       commit id: "DSOT model review"
       commit id: "Develop and doc software arch"
     checkout maintenance
       commit id: "GH #156 - large memory"
     checkout main
       merge use_case_support
       merge maintenance
       merge TESP_v2
       merge arch_des id: "Mar 31, 2026"


     %% FY26Q3 activity and deliverable
     checkout use_case_support
         commit id: "migrate SGPI1 to use-case repo"
     checkout TESP_v2
         branch markets
           commit id: "Implement curve object"
           commit id: "Implement curve object testbed"
           commit id: "Implement curve object tests"
         checkout TESP_v2
         merge markets
     checkout main
       merge use_case_support
       merge TESP_v2 id: "June 30, 2026"


     %% FY26Q4 activity and deliverable
     checkout comm_engagement
       commit id: "TESP icon"
       commit id: "PNNL feeder generator report"
     checkout maintenance
       commit id: "Release prep v1.3.8"
     checkout main
     merge maintenance id: "v1.3.8"
     merge comm_engagement id: "Sept 30, 2026, "

     %% FY27 activity and deliverable
     checkout TESP_v2
       branch TENT
         commit id: "Common device models with TENT"
         commit id: "Common data service interface with TENT"
         commit id: "Design feeder generator validator"
       checkout TESP_v2
       merge TENT
       checkout main
       commit id: "Implement feeder generator validator"
       checkout main
       merge TESP_v2 id: "FY27"



