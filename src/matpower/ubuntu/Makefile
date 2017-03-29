INSTALL_PATH := /home/laurentiu/tespMATPOWER_install
MCR_PATH := /usr/local/matlab_2013a
FNCS_PATH := /home/laurentiu/ccsiFNCS_install
#JSONCPP_INCLUDE := /usr/local/include/jsoncpp/json
# JSONCPP_LIB := /usr/local/lib
CXX = g++-4.4

CXXFLAGS =
CXXFLAGS += -g
CXXFLAGS += -ansi
CXXFLAGS += -pthread
CXXFLAGS += -O0

CPPFLAGS =
CPPFLAGS += -I$(MCR_PATH)/extern/include/cpp
CPPFLAGS += -I$(MCR_PATH)/extern/include
CPPFLAGS += -I$(FNCS_PATH)/include
#CPPFLAGS += -I$(JSONCPP_INCLUDE)
CPPFLAGS += -D_GNU_SOURCE
CPPFLAGS += -DUNIX
CPPFLAGS += -DX11
CPPFLAGS += -DGLNXA64
CPPFLAGS += -DGCC
CPPFLAGS += -DNDEBUG

LDFLAGS =
LDFLAGS += -Wl,-rpath=.
LDFLAGS += -Wl,-rpath-link,$(MCR_PATH)/bin/glnxa64
LDFLAGS += -L$(MCR_PATH)/runtime/glnxa64
LDFLAGS += -L$(FNCS_PATH)/lib
#LDFLAGS += -L$(JSONCPP_LIB)
LDFLAGS += -Wl,-rpath=$(FNCS_PATH)/lib
LDFLAGS += -L.

LIBS =
LIBS += -lmwmclmcrrt
LIBS += -lm
LIBS += -lMATPOWER
LIBS += -lfncs
LIBS += -lczmq
LIBS += -lzmq
LIBS += -ljsoncpp

all: start_MATPOWER

start_MATPOWER.o: start_MATPOWER.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

matpowerintegrator.o: matpowerintegrator.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

read_load_profile.o: read_load_profile.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

read_model_dim.o: read_model_dim.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

read_model_data.o: read_model_data.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

matpowerLoadMetrics.o: matpowerLoadMetrics.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)

matpowerGeneratorMetrics.o: matpowerGeneratorMetrics.cpp
	$(CXX) -c $< -o $@ $(CXXFLAGS) $(CPPFLAGS)
	
start_MATPOWER: start_MATPOWER.o matpowerintegrator.o read_load_profile.o read_model_dim.o read_model_data.o matpowerLoadMetrics.o matpowerGeneratorMetrics.o
	$(CXX) -o $@ $^ $(CXXFLAGS) $(LDFLAGS) $(LIBS)

clean:
	rm -f *~
	rm -f *.o
	rm -f *.mod
	rm -f start_MATPOWER
	rm -f *.chk
	rm -f *.out

install:
	cp lib*.so $(INSTALL_PATH)
	cp lib*.h $(INSTALL_PATH)
	cp start_MATPOWER $(INSTALL_PATH)
