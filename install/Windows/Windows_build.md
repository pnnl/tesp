=====================================
Start with a PC that builds GridLAB-D
=====================================
Follow http://gridlab-d.shoutwiki.com/wiki/MinGW/Eclipse_Installation,
except for:
a. Install a GIT command-line version instead of SVN
b. Clone the "feature/1048" branch from https://github.com/gridlab-d/gridlab-d 

autoreconf -if
./configure --build=x86_64-w64-mingw32 --with-fncs=$HOME/FNCS_install --prefix=$PWD/install64 --with-xerces=/opt/windows_64/mingw 'CXXFLAGS=-w' 'CFFLAGS=-w'
make
make install

Eclipse is optional. If not using it:
a. append (for example) c:\gridlab-d\install64\bin to PATH 
b. create a new environment variable 
GLPATH=c:\gridlab-d\install64\lib\gridlabd;c:\gridlab-d\install64\share\gridlabd

===========================================================
ZeroMQ
===========================================================
cd
wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.4.tar.gz
tar -xzf zeromq-4.1.4.tar.gz
cd zeromq-4.1.4
./configure --without-libsodium --prefix=$HOME/FNCS_install LDFLAGS="-static-libgcc -static-libstdc++"
(insert #include<iphlpapi.h> into src/windows.hpp around line 57)
make
make install

===========================================================
CZMQ
===========================================================
cd
wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
tar -xzf czmq-3.0.2.tar.gz
cd czmq-3.0.2
./configure --prefix=$HOME/FNCS_install --with-libzmq=$HOME/FNCS_install
mkdir builds
mkdir builds/mingw32
cd builds/mingw32
(manually create a Makefile, as appended to these instructions)
make
make install

===========================================================
FNCS
===========================================================
cd
git clone https://github.com/FNCS/fncs.git --branch feature/transactiveEnergyApi
cd fncs
(manually edit line 7 of configure.ac for version number 2.68) 
./configure --prefix=$HOME/FNCS_install --with-zmq=$HOME/FNCS_install
make
make install

Java Binding on Windows (cmake process not working yet):

cd java
javac fncs/JNIfncs.java
jar cvf fncs.jar fncs/JNIfncs.class
javah -classpath fncs.jar -jni fncs.JNIfncs
g++ -DJNIfncs_EXPORTS -I"C:/Program Files/Java/jdk1.8.0_101/include" -I"C:/Program Files/Java/jdk1.8.0_101/include/win32" -IC:/MinGW/msys/1.0/home/tom/fncs-dev/java -IC:/MinGW/msys/1.0/home/tom/FNCS_install/include -o fncs/JNIfncs.cpp.o -c fncs/JNIfncs.cpp
g++ -shared -o JNIfncs.dll fncs/JNIfncs.cpp.o "C:/Program Files/Java/jdk1.8.0_101/lib/jawt.lib" "C:/Program Files/Java/jdk1.8.0_101/lib/jvm.lib" C:/gridlab-d/install64/bin/libfncs.dll -lkernel32 -luser32 -lgdi32 -lwinspool -lshell32 -lole32 -loleaut32 -luuid -lcomdlg32 -ladvapi32

===========================
Rebuild GridLAB-D with FNCS
===========================


autoreconf -if
./configure --build=x86_64-w64-mingw32 --with-fncs=$HOME/FNCS_install --prefix=$PWD/install64 --with-xerces=/opt/windows_64/mingw 'CXXFLAGS=-w' 'CFFLAGS=-w'
make
make install

===========================================================
jsoncpp - build the static library for EnergyPlus
===========================================================
Clone the master branch from https://github.com/open-source-parsers/jsoncpp
Install cmake from https://cmake.org/download/ into c:\cmake so it's easy to start from the MSYS terminal.
The GridLAB-D setup requires CMake to use MSYS makefiles, not MinGW makefiles.
In addition, CMake may find conflicting versions of "cc" and "make" from other
development tools, e.g. FPC and Delphi. To mitigate these issues:
a. from the MSYS terminal "/c/cmake/bin/cmake-gui &" 
b. follow the Cmake build instructions on jsoncpp's GitHub page, using MSYS Makefiles generator
c. change CMAKE_INSTALL_PREFIX to match your FNCS_install, e.g. C:/MinGW/msys/1.0/home/tom/FNCS_install
d. generate the makefiles from CMake
e. from the MSYS terminal cd /c/jsoncpp/build
f. make
g. make install


===========================================================
EnergyPlus
===========================================================
clone the fncs-v8.3.0 branch from https://github.com/FNCS/EnergyPlus
start Cmake from the MSYS terminal, as for jsoncpp
a: source code at c:\energyplus
b. binaries at c:\energyplus\build
c. set the Grouped and Advanced check boxes
d. press Configure and choose MSYS Makefiles
e. press Generate
f. set, for example, CMAKE_INSTALL_PREFIX=C:/MinGW/msys/1.0/home/tom/FNCS_install
g. press Configure again; CMake should now find FNCS, CZMQ and ZeroMQ
h. press Generate again, then exit CMake
i. from the MSYS terminal cd /c/energyplus/build
j. make
k. make install
l. the Makefiles put energyplus.exe and its DLL into $HOME/FNCS_install; you have
to manually copy these files to $HOME/FNCS_install/bin


https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0

===========================================================
czmq-3.0.2/builds/mingw32/Makefile begins
===========================================================
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

===========================================================
czmq-3.0.2/builds/mingw32/Makefile ends
===========================================================



Xterm setup for Mac OS X (XQuartz) and Windows (MobaXterm)
==========================================================

# This may be necessary for XQuartz
sudo apt-get install xauth

# This is what works for Mac OS X via XQuartz, (i.e. -X fails)
# the MobaXterm connection is similar.
ssh -Y admsuser@tesp-ubuntu.pnl.gov

