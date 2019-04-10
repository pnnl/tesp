Building on Windows
-------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1146 for GridLAB-D
- develop for FNCS
- fncs-v8.3.0 for EnergyPlus

The Windows build procedure is very similar to that for Linux and
Mac OSX, using MSYS2 tools that you'll execute from a MSYS2 command
window. However, some further adjustments are necessary as described below.

When you finish the build, try :ref:`RunExamples`.

Install Python Packages and Java
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download and install the 64-bit Miniconda installer, for Python 3.6 or later, from
https://conda.io/miniconda.html

Then from a command prompt:

::

	conda update conda
	conda install pandas
	# tesp_support, including verification of PYPOWER dependency
	pip install tesp_support --upgrade
	opf

Download and install the Java Development Kit (8u191 suggested, with Public JRE) from 
http://www.oracle.com/technetwork/java/javase/downloads/index.html

- for MSYS2, install to a folder without spaces, such as c:\Java\jdk1.8.0_191
- the Oracle javapath doesn't work for MSYS2, and it doesn't find javac in Windows
- c:\Java\jdk1.8.0_191\bin should be added to your path

Set Up the Build Environment and Code Repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These instructions are based on https://github.com/gridlab-d/gridlab-d/blob/develop/BuildingGridlabdOnWindowsWithMsys2.docx
For TESP, we're going to build with FNCS, but not with HELICS, MATLAB or MySQL.

- Install a 64-bit version of MSYS2 from https://www.msys2.org. Accept all of the defaults.
- Start the MSYS2 environment from the Start Menu shortcut for "MSYS2 MSYS"

::

 pacman -Syuu

- Enter y to continue
- When directed after a series of warnings, close the MSYS2 by clicking on the Close Window icon
- Restart the MSYS2 environment from the Start Menu shortcut for "MSYS2 MSYS"

::

 pacman -Su
 pacman -S --needed base-devel mingw-w64-x86_64-toolchain
 pacman -S --needed mingw-w64-x86_64-xerces-c
 pacman -S --needed mingw-w64-x86_64-dlfcn
 pacman -S --needed mingw-w64-x86_64-cmake
 pacman -S --needed git jsoncpp
 pacman -S --needed mingw64/mingw-w64-x86_64-zeromq
 pacman -S --needed mingw64/mingw-w64-x86_64-boost
 pacman -S --needed mingw64/mingw-w64-x86_64-swig

- Exit MSYS2 and restart from a different Start Menu shortcut for MSYS2 MinGW 64-bit
- You may wish to create a desktop shortcut for the 64-bit environment, as you will use it often

::

 cd /c/
 mkdir src
 cd src
 git config --global user.name "Your Name"
 git config --global user.email "YourEmailAddress@YourDomain.com"
 git clone -b feature/1146 https://github.com/gridlab-d/gridlab-d.git
 git clone -b develop https://github.com/FNCS/fncs.git
 git clone -b develop https://github.com/GMLC-TDC/HELICS-src.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b develop https://github.com/pnnl/tesp.git

We're going to build everything to /usr/local in the MSYS2 environment. If you accepted the
installation defaults, this corresponds to c:\msys64\usr\local in the Windows environment. 
The Windows PATH should be updated accordingly, and we'll also need a GLPATH environment variable.
This is done in the Windows Settings tool, choosing "Edit the system environment variables" or
"Edit environment variables for your account" from the Settings search field.

- append c:\\msys64\\usr\\local\\bin to PATH 
- append c:\\msys64\\usr\\local\\lib to PATH 
- create a new environment variable GLPATH
- append c:\\msys64\\usr\\local\\bin to GLPATH 
- append c:\\msys64\\usr\\local\\lib\\gridlabd to GLPATH 
- append c:\\msys64\\usr\\local\\share\\gridlabd to GLPATH 

Verify the correct paths to Java and Python for your installation, either 
by examining the PATH variable from a Windows (not MSYS) command prompt, 
or by using the Windows Settings tool.  Insert the following to 
.bash_profile in your MSYS2 environment, substituting your own paths to 
Java and Python.  

::

 PATH="/c/Java/jdk1.8.0_191/bin:${PATH}"
 PATH="/c/Users/Tom/Miniconda3:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Scripts:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Library/mingw-w64/bin:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Library/usr/bin:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Library/bin:${PATH}"

The next time you open MSYS2, verify the preceeding as follows:

::

 java -version
 javac -version
 python --version
 python3 --version

Build FNCS and HELICS Link with GridLAB-D
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ZeroMQ 4.2.5 and CZMQ 4.1.1 required from https://github.com/zeromq/libzmq/releases
and https://github.com/zeromq/czmq/releases

Build ZeroMQ first: 

::

 cd /c/src
 tar -xzf zeromq-4.2.5.tar.gz
 cd zeromq-4.2.5
 ./configure --prefix=/usr/local 'CXXFLAGS=-O2 -w' 'CFLAGS=-O2 -w'
 make
 make install

CZMQ next, with customized libraries to link: 

::

 cd /c/src
 tar -xzf czmq-4.1.1.tar.gz
 cd czmq-4.1.1
 // edit /usr/local/lib/pkgconfig/libzmq.pc to read Libs: -L${libdir} -lzmq -lws2_32 -liphlpapi -lrpcrt4
 ./configure --prefix=/usr/local --with-libzmq=/usr/local 'CXXFLAGS=-O2 -w' 'CFLAGS=-O2 -w' 'PKG_CONFIG_PATH=/usr/local/lib/pkgconfig'
 make
 make install

Now build FNCS:

::

 cd /c/src
 cd fncs
 ./configure --prefix=/usr/local --with-zmq=/usr/local 'CXXFLAGS=-O2 -w' 'CFLAGS=-O2 -w'
 make
 make install

Use manual commands for the Java FNCS Binding on Windows, because the Linux/Mac CMake files
don't work on Windows yet. Also make sure that the JDK/bin directory is in your path.

Your Java version may have removed *javah*.  If that's the case, use *javac -h* instead.

::

 cd /c/src/fncs/java
 javac fncs/JNIfncs.java
 jar cvf fncs.jar fncs/JNIfncs.class
 javah -classpath fncs.jar -jni fncs.JNIfncs
 (for Java 8)
 g++ -DJNIfncs_EXPORTS -I"C:/Java/jdk1.8.0_191/include" -I"C:/Java/jdk1.8.0_191/include/win32" -I/c/src/fncs/java -I/usr/local/include -o fncs/JNIfncs.cpp.o -c fncs/JNIfncs.cpp
 g++ -shared -o JNIfncs.dll fncs/JNIfncs.cpp.o "C:/Java/jdk1.8.0_191/lib/jawt.lib" "C:/Java/jdk1.8.0_191/lib/jvm.lib" /usr/local/bin/libfncs.dll -lkernel32 -luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32
 (for Java 9)
 g++ -DJNIfncs_EXPORTS -I"C:/Java/jdk-9.0.4/include" -I"C:/Java/jdk-9.0.4/include/win32" -I/usr/local/include -I. -o fncs/JNIfncs.cpp.o -c fncs/JNIfncs.cpp
 g++ -shared -o JNIfncs.dll fncs/JNIfncs.cpp.o "C:/Java/jdk-9.0.4/lib/jawt.lib" "C:/Java/jdk-9.0.4/lib/jvm.lib" /usr/local/bin/libfncs.dll -lkernel32 -luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32
 
To build HELICS 2.0 with Python and Java bindings:

::

 cd ~/src/HELICS-src
 mkdir build
 cd build
 cmake -G "MSYS Makefiles" -DBUILD_PYTHON_INTERFACE=ON -DBUILD_JAVA_INTERFACE=ON -DCMAKE_BUILD_TYPE=Release ..
 make
 make install

Finally, build and test GridLAB-D with FNCS. If you encounter build errors with GridLAB-D, please try
adding *-std=c++11* to *CXXFLAGS*.

::

 cd /c/src/gridlab-d
 autoreconf -if
 ./configure --build=x86_64-mingw32 --with-fncs=/usr/local --with-helics=/usr/local --prefix=/usr/local --with-xerces=/mingw64 --enable-silent-rules 'CXXFLAGS=-O2 -w' 'CFLAGS=-O2 -w' 'LDFLAGS=-O2 -w -L/mingw64/bin'
 make
 make install
 gridlabd --validate

In order to run GridLAB-D from a regular Windows terminal, you have to copy some additional
libraries from c:\\msys64\\mingw64\\bin to c:\\msys64\\usr\\local\\bin

- libdl.dll
- libgcc_s_seh-1.dll
- libstdc++-6.dll
- libwinpthread-1.dll

Build EnergyPlus
~~~~~~~~~~~~~~~~

Install the archived version 8.3 from https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0  
We need this for some critical support files that aren't part of the FNCS-EnergyPlus build
process. Copy the following from c:\\EnergyPlusV8-3-0 to c:\\msys64\\usr\\local\\bin:

- Energy+.idd
- PostProcess\\ReadVarsESO.exe

From the MSYS2 terminal:

::

 cd /c/src/energyplus
 mkdir build
 cd build
 cmake -G "MSYS Makefiles" -DCMAKE_INSTALL_PREFIX=/usr/local ..
 make
 make install

The Makefiles put energyplus.exe and its DLL into /usr/local. You have to manually 
copy the following build products from /usr/local to /usr/local/bin:

- energyplus.exe
- energyplusapi.dll

Build eplus_json
~~~~~~~~~~~~~~~~

From the MSYS2 terminal

::

 cd /c/src/tesp/src/energyplus
 cp Makefile.win Makefile
 cp config.h.win config.h
 make
 make install


 

