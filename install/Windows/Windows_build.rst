Building on Windows
-------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1048 for GridLAB-D
- feature/transactiveEnergyApi for FNCS
- fncs-v8.3.0 for EnergyPlus

The Windows build procedure is very similar to that for Linux and
Mac OSX, using MingW tools that you'll execute from a MSYS command
window. However, some further adjustments are necessary as described below.

When you finish the build, try RunExamples_.

Install Python, PYPOWER and Java
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download and install the 64-bit Miniconda installer, for Python 3.6 or later, from
https://conda.io/miniconda.html

Then from a command prompt:

::

	conda update conda
	conda install matplotlib
	conda install scipy
	conda install pandas
	# verify up-to-date PYPOWER
	pip install pypower
	opf

Download and install the Java 8 JDK from 
http://www.oracle.com/technetwork/java/javase/downloads/index.html

Initial Build of GridLAB-D
~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow http://gridlab-d.shoutwiki.com/wiki/MinGW/Eclipse_Installation,
except for:

- Install a GIT command-line version instead of SVN
- Clone the "feature/1048" branch from https://github.com/gridlab-d/gridlab-d 

Eclipse is optional. If not using it:

- append (for example) c:\gridlab-d\install64\bin to PATH 
- create a new environment variable GLPATH=c:\gridlab-d\install64\lib\gridlabd;c:\gridlab-d\install64\share\gridlabd

At this point, you should have GridLAB-D built without FNCS.

Build FNCS and Link with GridLAB-D
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ZeroMQ first, with a header file patch:

::

 cd
 wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.4.tar.gz
 tar -xzf zeromq-4.1.4.tar.gz
 cd zeromq-4.1.4
 ./configure --without-libsodium --prefix=$HOME/FNCS_install LDFLAGS="-static-libgcc -static-libstdc++"
 (insert #include<iphlpapi.h> into src/windows.hpp around line 57)
 make
 make install

CZMQ next, with a special Makefile:

::

 cd
 wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
 tar -xzf czmq-3.0.2.tar.gz
 cd czmq-3.0.2
 ./configure --prefix=$HOME/FNCS_install --with-libzmq=$HOME/FNCS_install
 mkdir builds
 mkdir builds/mingw32
 cd builds/mingw32
 (manually create a Makefile, as shown in the next code block)
 make
 make install

Here is the Windows Makefile for CZMQ:

::

 # replace the following with locations for libzmq and fncs
 PREFIX=c:/mingw/msys/1.0/home/tom/fncs_install

 INCDIR=-I$(PREFIX)/include -I.
 LIBDIR=-L$(PREFIX)/lib

 CC=gcc
 CFLAGS=-Wall -Os -g -std=c99 -DLIBCZMQ_EXPORTS $(INCDIR)

 HEADERS = ../../include/*.h ../../src/zgossip_msg.h

 OBJS = zactor.o \
	 zarmour.o \
	 zauth.o \
	 zauth_v2.o \
	 zbeacon.o \
	 zbeacon_v2.o \
	 zcert.o \
	 zcertstore.o \
	 zchunk.o \
	 zclock.o \
	 zconfig.o \
	 zctx.o \
	 zdigest.o \
	 zdir.o \
	 zdir_patch.o \
	 zfile.o \
	 zframe.o \
	 zgossip.o \
	 zgossip_msg.o \
	 zhash.o \
	 zhashx.o \
	 ziflist.o \
	 zlist.o \
	 zlistx.o \
	 zloop.o \
	 zmonitor.o \
	 zmonitor_v2.o \
	 zmsg.o \
	 zmutex.o \
	 zpoller.o \
	 zproxy.o \
	 zproxy_v2.o \
	 zrex.o \
	 zsock.o \
	 zsock_option.o \
	 zsocket.o \
	 zsockopt.o \
	 zstr.o \
	 zsys.o \
	 zthread.o \
	 zuuid.o

 %.o: ../../src/%.c
	 $(CC) -c -o $@ $< $(CFLAGS)

 all: libczmq.dll czmq_selftest.exe

 install:
	 cp libczmq.dll $(PREFIX)/bin
	 cp libczmq.dll.a $(PREFIX)/lib
	 cp czmq_selftest.exe $(PREFIX)/bin
	 cp $(HEADERS) $(PREFIX)/include

 libczmq.dll: $(OBJS)
	 $(CC) -shared -o $@ $(OBJS) -Wl,--out-implib,$@.a $(LIBDIR) -lzmq -lws2_32 -liphlpapi -lrpcrt4

 # the test functions are not exported into the DLL
 czmq_selftest.exe: czmq_selftest.o $(OBJS)
	 $(CC) -o $@ $^ $(LIBDIR) -lzmq -lws2_32 -liphlpapi -lrpcrt4

 clean:
	 rm *.o *.a *.dll *.exe

Now build FNCS, with manual adjustment of the required autoconf version:

::

 cd
 git clone https://github.com/FNCS/fncs.git --branch feature/transactiveEnergyApi
 cd fncs
 (manually edit line 7 of configure.ac for version number 2.68) 
 ./configure --prefix=$HOME/FNCS_install --with-zmq=$HOME/FNCS_install
 make
 make install

Use manual commands for the Java Binding on Windows, because the Linux/Mac CMake files
don't work on Windows yet:

::

 cd java
 javac fncs/JNIfncs.java
 jar cvf fncs.jar fncs/JNIfncs.class
 javah -classpath fncs.jar -jni fncs.JNIfncs
 g++ -DJNIfncs_EXPORTS -I"C:/Program Files/Java/jdk1.8.0_101/include" -I"C:/Program Files/Java/jdk1.8.0_101/include/win32" -IC:/MinGW/msys/1.0/home/tom/fncs-dev/java -IC:/MinGW/msys/1.0/home/tom/FNCS_install/include -o fncs/JNIfncs.cpp.o -c fncs/JNIfncs.cpp
 g++ -shared -o JNIfncs.dll fncs/JNIfncs.cpp.o "C:/Program Files/Java/jdk1.8.0_101/lib/jawt.lib" "C:/Program Files/Java/jdk1.8.0_101/lib/jvm.lib" C:/gridlab-d/install64/bin/libfncs.dll -lkernel32 -luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32

Finally, rebuild GridLAB-D with FNCS:

::

 autoreconf -if
 ./configure --build=x86_64-w64-mingw32 --with-fncs=$HOME/FNCS_install --prefix=$PWD/install64 --with-xerces=/opt/windows_64/mingw 'CXXFLAGS=-w' 'CFFLAGS=-w'
 make
 make install
 gridlabd --validate

Build JsonCPP for EnergyPlus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the master branch from https://github.com/open-source-parsers/jsoncpp

Install cmake from https://cmake.org/download/ into c:\cmake so it's easy to start from the MSYS terminal.

The GridLAB-D setup requires CMake to use MSYS makefiles, not MinGW makefiles.
In addition, CMake may find conflicting versions of "cc" and "make" from other
development tools, e.g. FPC and Delphi. To mitigate these issues:

- from the MSYS terminal "/c/cmake/bin/cmake-gui &" 
- follow the Cmake build instructions on jsoncpp's GitHub page, using MSYS Makefiles generator
- change CMAKE_INSTALL_PREFIX to match your FNCS_install, e.g. C:/MinGW/msys/1.0/home/tom/FNCS_install
- generate the makefiles from CMake
- from the MSYS terminal cd /c/jsoncpp/build
- make
- make install

Build EnergyPlus
~~~~~~~~~~~~~~~~

Install the archived version 8.3 from https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0  
We need this for some critical support files that aren't part of the FNCS-EnergyPlus build
process.

Start Cmake from the MSYS terminal, as you did for jsoncpp, and configure it as follows:

- source code at c:\energyplus
- binaries at c:\energyplus\build
- set the Grouped and Advanced check boxes
- press Configure and choose MSYS Makefiles
- press Generate
- set, for example, CMAKE_INSTALL_PREFIX=C:/MinGW/msys/1.0/home/tom/FNCS_install
- press Configure again; CMake should now find FNCS, CZMQ and ZeroMQ
- press Generate again, then exit CMake

From the MSYS terminal 

- cd /c/energyplus/build
- make
- make install
- the Makefiles put energyplus.exe and its DLL into $HOME/FNCS_install; you have to manually copy these files to $HOME/FNCS_install/bin


