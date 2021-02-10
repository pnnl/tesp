ACLOCAL_AMFLAGS = -I m4

AM_CXXFLAGS =

AM_CPPFLAGS =
AM_CPPFLAGS += -std=c++14
AM_CPPFLAGS += -I$(HELICS_INSTALL)/include
AM_CPPFLAGS += -I$(CZMQ_CPPFLAGS)
AM_CPPFLAGS += -I$(ZMQ_CPPFLAGS)

AM_LDFLAGS =
AM_LDFLAGS += -L$(HELICS_INSTALL)/lib
AM_LDFLAGS += -L$(CZMQ_LDFLAGS)
AM_LDFLAGS += -L$(ZMQ_LDFLAGS)

LDADD =
LDADD += -lhelics-shared
LDADD += $(CZMQ_LIBS)
LDADD += $(ZMQ_LIBS)

bin_PROGRAMS = eplus_agent_helics
eplus_agent_helics_SOURCES = eplus_agent_helics.cpp consensus.cpp jsoncpp.cpp