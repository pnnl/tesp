
from pyomo.environ import SolverFactory
import warnings
import os
import click
from .results import PSSTResults
from pyutilib.services import TempfileManager

PSST_WARNING = os.getenv('PSST_WARNING', 'ignore')
#TempfileManager.tempdir = "./DataFiles/TempFiles"
#TempfileManager.tempdir = "C:\\Users\\swathi\\Dropbox\\AMESLatestVersion\\TESAgents\\PyomoTempFiles"
#TempfileManager.tempdir = "C:\\Users\\huan289\\Qiuhua\\FY2016_Project_Transactive_system\\ERCOTTestSystem\\AMES-V5.0\\DataFiles\\logfiles"


def solve_model(model, solver='glpk', solver_io=None, keepfiles=True, verbose=True, symbolic_solver_labels=True, is_mip=True, mipgap=0.01):
    #click.echo("solver  "+str(solver))
    if solver == 'xpress':
        solver = SolverFactory(solver, solver_io=solver_io, is_mip=is_mip)
    else:
        solver = SolverFactory(solver, solver_io=solver_io)
    model.preprocess()
    if is_mip:
        solver.options['mipgap'] = mipgap
    #solver.options['seconds'] = 10 # Maximum Time Limit

    with warnings.catch_warnings():
        warnings.simplefilter(PSST_WARNING)
        resultsPSST = solver.solve(model, suffixes=['dual'], tee=verbose, keepfiles=True, symbolic_solver_labels=symbolic_solver_labels)
        #click.echo("solver msg 1 " + str(resultsPSST.solver))
        #click.echo("solver msg 2 " + str(resultsPSST.solver.status))
        #click.echo("solver msg 3 " + str(resultsPSST.solver.termination_condition))
        #click.echo("solver msg 4 " + str(resultsPSST))

    #click.echo("End")
    return model
