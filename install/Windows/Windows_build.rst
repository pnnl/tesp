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

When you finish the build, try RunExamples_.

Install Python Packages and Java
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download and install the 64-bit Miniconda installer, for Python 3.6 or later, from
https://conda.io/miniconda.html

Then from a command prompt:

::

	conda update conda
	conda install pandas
	# tesp_support, including verification of PYPOWER dependency
	pip install tesp_support
	opf

Download and install the Java 8 JDK (1.8.0_192 suggested) from 
http://www.oracle.com/technetwork/java/javase/downloads/index.html

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
 pacman -S --needed base-devel mingw-w64-x86_64-toolchain git dlfcn xerces-c jsoncpp cmake
 pacman -S --needed mingw-w64-x86_64-xerces-c

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
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b master https://github.com/pnnl/tesp.git

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

Insert the following to .bash_profile in your MSYS2 environment.

::

 PATH="/c/ProgramData/Oracle/Java/javapath:${PATH}"
 PATH="/c/Program Files/Java/jdk-9.0.4/bin:${PATH}"
 PATH="/c/Users/Tom/Miniconda3:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Scripts:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Library/mingw-w64/bin:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Library/usr/bin:${PATH}"
 PATH="/c/Users/Tom/Miniconda3/Library/bin:${PATH}"


Build FNCS and Link with GridLAB-D
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ZeroMQ first, with a header file patch:

::

 cd /c/src
 wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.4.tar.gz
 tar -xzf zeromq-4.1.4.tar.gz
 cd zeromq-4.1.4
 ./configure --without-libsodium --prefix=/usr/local LDFLAGS="-static-libgcc -static-libstdc++"
 (insert #include<iphlpapi.h> into src/windows.hpp around line 57)
 make
 make install

CZMQ next, with a special Makefile:

::

 cd /c/src
 wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
 tar -xzf czmq-3.0.2.tar.gz
 cd czmq-3.0.2
 ./configure --prefix=/usr/local --with-libzmq=/usr/local
 mkdir builds
 mkdir builds/mingw32
 cd builds/mingw32
 (manually create a Makefile, as shown in the next code block)
 make
 make install

Here is the Windows Makefile for CZMQ:

::

 # replace the following with locations for libzmq and fncs
 PREFIX=c:/msys64/usr/local

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

Now build FNCS:

::

 cd /c/src
 cd fncs
 ./configure --prefix=/usr/local --with-zmq=/usr/local
 make
 make install

Use manual commands for the Java Binding on Windows, because the Linux/Mac CMake files
don't work on Windows yet. Also make sure that the JDK/bin directory is in your path.

::

 cd java
 javac fncs/JNIfncs.java
 jar cvf fncs.jar fncs/JNIfncs.class
 javah -classpath fncs.jar -jni fncs.JNIfncs
 g++ -DJNIfncs_EXPORTS -I"C:/Program Files/Java/jdk1.8.0_101/include" -I"C:/Program Files/Java/jdk1.8.0_101/include/win32" -IC:/MinGW/msys/1.0/home/tom/fncs-dev/java -IC:/MinGW/msys/1.0/home/tom/FNCS_install/include -o fncs/JNIfncs.cpp.o -c fncs/JNIfncs.cpp
 g++ -shared -o JNIfncs.dll fncs/JNIfncs.cpp.o "C:/Program Files/Java/jdk1.8.0_101/lib/jawt.lib" "C:/Program Files/Java/jdk1.8.0_101/lib/jvm.lib" /usr/local/bin/libfncs.dll -lkernel32 -luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32
 
(for Java 9)
g++ -DJNIfncs_EXPORTS -I"C:/Program Files/Java/jdk-9.0.4/include" -I"C:/Program Files/Java/jdk-9.0.4/include/win32" -IC:/MinGW/msys/1.0/home/tom/FNCS_install/include -I. -o fncs/JNIfncs.cpp.o -c fncs/JNIfncs.cpp
g++ -shared -o JNIfncs.dll fncs/JNIfncs.cpp.o "C:/Program Files/Java/jdk-9.0.4/lib/jawt.lib" "C:/Program Files/Java/jdk-9.0.4/lib/jvm.lib" /usr/local/bin/libfncs.dll -lkernel32 -luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32

Finally, build and test GridLAB-D with FNCS:

::

 autoreconf -if
 ./configure --build=x86_64-mingw32 --with-fncs=/usr/local --prefix=/usr/local --with-xerces=/mingw64 --enable-silent-rules 'CXXFLAGS=-g -O2 -w' 'CFLAGS=-g -O2 -w' 'LDFLAGS=-g -O2 -w -L/mingw64/bin'
 make
 make install
 gridlabd --validate

Build EnergyPlus
~~~~~~~~~~~~~~~~

Install the archived version 8.3 from https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0  
We need this for some critical support files that aren't part of the FNCS-EnergyPlus build
process. Copy the following from c:\\EnergyPlusV8-3-0 to c:\\msys64\\usr\\local\\bin:

- Energy+.idd
- parser.exe
- RunReadESO.bat
- ReadVarsESO.exe

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

 cd /c/
 cd tesp/src/energyplus
 cp Makefile.win Makefile
 cp config.h.win config.h
 make
 make install


 

