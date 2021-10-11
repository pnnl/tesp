INSTALL_PATH := ${INSTDIR}
CXX = g++

CXXFLAGS =
#CXXFLAGS += -g
#CXXFLAGS += -O2
#CXXFLAGS += -std=c++0x

CPPFLAGS =
CPPFLAGS += -I$(INSTALL_PATH)/include
CPPFLAGS += -I$(INSTALL_PATH)/include/ns3-dev
#CPPFLAGS += -pthread

LDFLAGS =
LDFLAGS += -L$(INSTALL_PATH)/lib

LIBS =
LIBS += -lns3-dev-helics-optimized
LIBS += -lns3-dev-internet-optimized
LIBS += -lns3-dev-network-optimized
LIBS += -lns3-dev-core-optimized
LIBS += -lns3-dev-point-to-point-optimized
#LIBS += -lns3-dev-helics-debug
#LIBS += -lns3-dev-internet-debug
#LIBS += -lns3-dev-network-debug
#LIBS += -lns3-dev-core-debug
#LIBS += -lns3-dev-point-to-point-debug
LIBS += -lhelics-shared

all: loadshedCommNetwork

loadshedCommNetwork.o: loadshedCommNetwork.cc
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

loadshedCommNetwork: loadshedCommNetwork.o
	$(CXX) -o $@ $^ $(CXXFLAGS) $(LDFLAGS) $(LIBS)

clean:
	rm -f *.o
	rm -f loadshedCommNetwork

install:
	cp loadshedCommNetwork $(INSTALL_PATH)/bin

