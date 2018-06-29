# GridLAB-D Feeder Model Modification Scripts
 
This repository contains python scripts that can convert GridLAB-D power flow models (like the [Taxonomy of Prototypical Feeders]( https://github.com/gridlab-d/Taxonomy_Feeders)) to add different technologies.

The repository is structured in the following way:
* modelDependency folder holds any dependencies for the model being created (weather profiles, shedules, etc.)
* modificationScripts folder holds the main script functions for adding technology along with a folder for support function

The code is designed such that nearly all settings can be redefined in the main scripts located in ```./modificationScripts```. For ease of use and example called ```populateFeeders.py``` is present in this folder that creates a user defined number of feeder. Wihtout modification this script will create the new feeders and any support files needed in ```./experiments/<experiment name>```


## Code dependencies
The code is dependant on the following packages: 
* [GridLAB-D](http://gridlab-d.shoutwiki.com/wiki/Index)
* [Python 3.X.X](https://www.python.org/downloads/)
  * [numpy](http://www.numpy.org/)
  * [scipy](https://www.scipy.org/)
  * [tqdm](https://pypi.python.org/pypi/tqdm)
  * [subprocess](https://docs.python.org/3/library/subprocess.html)
  * [os](https://docs.python.org/3/library/os.html)
  * [random](https://docs.python.org/3/library/random.html)
  * [math](https://docs.python.org/3/library/math.html)
  * [copy](https://docs.python.org/3/library/copy.html)
  * [__future__](https://docs.python.org/3/library/__future__.html)
  * [re](https://docs.python.org/3/library/re.html)
  * [warnings](https://docs.python.org/3/library/warnings.html)
  * [time](https://docs.python.org/3/library/time.html)
  * [shutil](https://docs.python.org/3/library/shutil.html)
  * [multiprocessing](https://docs.python.org/3/library/multiprocessing.html)
  * [datetime](https://docs.python.org/3/library/datetime.html)

