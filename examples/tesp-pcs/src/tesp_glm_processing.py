# -*- coding: utf-8 -*-
"""
**Important!!!**

This script needs to be run in tesp_support source repository, as the function called have the paths hard-coded in. Therefore, before running it, move the file to /src/tesp_support/tesp_support/, create a folder named Dummy in there, and then run the scripts. The ouput files will be saved into the Dummy folder, from where they can be moved to the /tesp-pcs/files/ fodler for the next step.

Process taxonomy feeder

.. module:: tesp_glm_processing

:synopsis: Populate a taxonomy feeder, and then extract a dictionary in JSON format. Using two of the tesp_support functionalities, this script will populate a taxonomy feeder (ProcessTaxonomyFeeder function in feederGenerator), and then extracts to a JSON file some of the nodes in the populated feeder file.

:platform: Unix

.. moduleauthor:: Laurentiu Marinovici (PNNL)

"""
__docformat__ = 'reStructuredText'
import tesp_support.glm_dict as glm_dict
import tesp_support.prep_substation as prep
import tesp_support.feederGenerator as fg
import os


def main(taxonomyRoot):
  """
  Processes a taxonomy feeder, populates it with end-use consumers, and then describes it in a JSON format

  Parameters
  ----------
  taxonomyRoot : str
    The name of the taxonomy feeder considered. The taxonomy feeder files are loaded from the tesp-support repository in the folder /support/feeders/

  Returns
  -------
  In a dummy output folder, the populated GridLAB-D model is saved under <taxonomyRoot>_processed.glm, and then <taxonomyRoot>_processed_glm_dict.json is created at the same location.

  """
  # Root Name, VLL, VLN, Avg House, Avg Commercial
  taxchoice = [['R1-12.47-1', 12470.0, 7200.0, 4000.0, 20000.0],
               ['R1-12.47-2', 12470.0, 7200.0, 4500.0, 30000.0],
               ['R1-12.47-3', 12470.0, 7200.0, 8000.0, 15000.0],
               ['R1-12.47-4', 12470.0, 7200.0, 4000.0, 15000.0],
               ['R1-25.00-1', 24900.0, 14400.0, 6000.0, 25000.0],
               ['R2-12.47-1', 12470.0, 7200.0, 7000.0, 20000.0],
               ['R2-12.47-2', 12470.0, 7200.0, 15000.0, 25000.0],
               ['R2-12.47-3', 12470.0, 7200.0, 5000.0, 30000.0],
               ['R2-25.00-1', 24900.0, 14400.0, 6000.0, 15000.0],
               ['R2-35.00-1', 34500.0, 19920.0, 15000.0, 30000.0],
               ['R3-12.47-1', 12470.0, 7200.0, 12000.0, 40000.0],
               ['R3-12.47-2', 12470.0, 7200.0, 14000.0, 30000.0],
               ['R3-12.47-3', 12470.0, 7200.0, 7000.0, 15000.0],
               ['R4-12.47-1', 13800.0, 7970.0, 9000.0, 30000.0],
               ['R4-12.47-2', 12470.0, 7200.0, 6000.0, 20000.0],
               ['R4-25.00-1', 24900.0, 14400.0, 6000.0, 20000.0],
               ['R5-12.47-1', 13800.0, 7970.0, 6500.0, 20000.0],
               ['R5-12.47-2', 12470.0, 7200.0, 4500.0, 15000.0],
               ['R5-12.47-3', 13800.0, 7970.0, 4000.0, 15000.0],
               ['R5-12.47-4', 12470.0, 7200.0, 6000.0, 30000.0],
               ['R5-12.47-5', 12470.0, 7200.0, 4500.0, 25000.0],
               ['R5-25.00-1', 22900.0, 13200.0, 3000.0, 20000.0],
               ['R5-35.00-1', 34500.0, 19920.0, 6000.0, 25000.0],
               ['GC-12.47-1', 12470.0, 7200.0, 8000.0, 13000.0],
               ['TE_Base',   12470.0, 7200.0, 8000.0, 13000.0]]
  casefiles = [[taxonomyRoot, 12470.0, 7200.0, 4000.0, 20000.0]]

  fg.ProcessTaxonomyFeeder('{0}_processed'.format(
      casefiles[0][0]), casefiles[0][0], casefiles[0][1], casefiles[0][2], casefiles[0][3], casefiles[0][4])
  glm_dict.glm_dict('./Dummy/{0}_processed'.format(casefiles[0][0]))


if __name__ == '__main__':
  main('R1-12.47-1')
