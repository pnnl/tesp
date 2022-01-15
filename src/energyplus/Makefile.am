ACLOCAL_AMFLAGS = -I m4

AM_CXXFLAGS =

#HELICS_LIBS = -lhelics
#HELICS_LIBS = -lhelicscpp-apps
HELICS_LIBS = -lhelicscpp

AM_CPPFLAGS = -std=c++17
#AM_CPPFLAGS = -std=c++0x
AM_CPPFLAGS += $(HELICS_CPPFLAGS)
AM_CPPFLAGS += $(FNCS_CPPFLAGS)
AM_CPPFLAGS += $(CZMQ_CPPFLAGS)
AM_CPPFLAGS += $(ZMQ_CPPFLAGS)

AM_LDFLAGS =
AM_LDFLAGS += $(HELICS_LDFLAGS)
AM_LDFLAGS += $(FNCS_LDFLAGS)
AM_LDFLAGS += $(CZMQ_LDFLAGS)
AM_LDFLAGS += $(ZMQ_LDFLAGS)

LDADD =
LDADD += $(HELICS_LIBS)
LDADD += $(FNCS_LIBS)
LDADD += $(CZMQ_LIBS)
LDADD += $(ZMQ_LIBS)

bin_PROGRAMS = eplus_agent eplus_agent_helics test_comm
eplus_agent_SOURCES = eplus_agent.cpp jsoncpp.cpp
eplus_agent_helics_SOURCES = eplus_agent_helics.cpp consensus.cpp jsoncpp.cpp
test_comm_SOURCES = test_comm.cpp consensus.cpp jsoncpp.cpp
