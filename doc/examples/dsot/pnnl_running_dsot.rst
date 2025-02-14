Running DSO+T or Rates Cases
----------------------------
These are Jessica Kerby's notes/outline; consult her with any questions.


Installing Tools 
................
* `Python 3` - `Windows needs to install manually <https://www.python.org/downloads/windows/>`_, Linux and macOS generally include it.
*  An IDE (integrated development environment), `VS Code <https://code.visualstudio.com/download>`_ and `PyCharm CE <https://www.jetbrains.com/pycharm/download/?section=windows>`_ are popular but there are others.
* Package manager - `Anaconda <https://www.anaconda.com/download>`_ or `pip <https://pip.pypa.io/en/stable/installation/>`_ (macOS and Linux generally come with pip already installed).
* Terminal (Windows users like `mobaxterm <https://mobaxterm.mobatek.net/>`_, macOS and Linux built-in terminals are generally sufficient.

Setup an environment and install TESP on a remote server
........................................................

-  mobaxterm

   -  Connect using ssh session of mobaxterm into a linux computing resources

      -  Note that you need to request access individually
      -  Session -> new session -> user@resource.company.com
      -  Enter password

-  vscode (code)

   -  Install from the command line in mobaxterm:
      ::

         sudo apt install snapd
         sudo snap install --classic code

   -  Here is how to start the environment and pycharm and capture pycharm log for any errors from the terminal:
      ::

         source ~/grid/tesp/tesp.env
         code &> ~/code.log&

   -  To kill sessions from the terminal: ``killall code``

-  pycharm (pycharm-community)

   -  Install from the command line in mobaxterm:
      ::

         sudo apt install snapd
         sudo snap install pycharm-community --classic

   -  Here is how to start the environment and pycharm and capture pycharm log for any errors from the terminal:
      ::

         source ~/grid/tesp/tesp.env
         pycharm-community &> ~/charm.log&

   -  To kill sessions from the terminal: ``killall pycharm-community``