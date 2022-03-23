INSTALL_PATH := ${INSTDIR}

##############################################################################
# Application-specific variables
# Specifically, extracting all the ns-3 libraries to link against later,
# such that I do not have to speciffy each of them.
##############################################################################
LIBDIRS = $(wildcard $(INSTALL_PATH)/lib*)
$(info <<<<<<<<<< lib directory >>>>>>>>>>)
$(info $(LIBDIRS))
NS3_LIBFILES = $(patsubst $(LIBDIRS)/libns3%.so,-lns3%,$(wildcard $(LIBDIRS)/libns3*))
$(info <<<<<<<<<< ns-3 lib files >>>>>>>>>>)
$(info $(NS3_LIBFILES))
HELICS_LIBFILES = $(patsubst $(LIBDIRS)/libhelics%.so,-lhelics%,$(wildcard $(LIBDIRS)/libhelics*))
$(info <<<<<<<<<< HELICS lib files >>>>>>>>>>)
$(info $(HELICS_LIBFILES))

##############################################################################
# Compiler specifications
# These match the variable names given in /usr/share/lib/make/make.rules
# so that make's generic rules work to compile our files.
# gmake prefers CXX and CXXFLAGS for c++ programs
##############################################################################
CXX = g++
CC = $(CXX)

CXXFLAGS =
CXXFLAGS += -std=c++17
SRC = $(wildcard *.cc)
OBJ = $(SRC:.cc=.o)
BIN = $(OBJ:.o=) # my binary

##############################################################################
# What flags should be passed to the C pre-processor
#   In other words, where should we look for files to include - note,
#   you should never need to include compiler specific directories here
#   because each compiler already knows where to look for its system
#   files (unless you want to override the defaults)
##############################################################################
CPPFLAGS =
CPPFLAGS += -I$(INSTALL_PATH)/include
CPPFLAGS += -I$(wildcard $(INSTALL_PATH)/include/ns3*)
$(info <<<<<<<<<< CPPFLAGS >>>>>>>>>>)
$(info $(CPPFLAGS))

##############################################################################
# What flags should be passed to the linker
#   In other words, where should we look for libraries to link with - note,
#   you should never need to include compiler specific directories here
#   because each compiler already knows where to look for its system files.
##############################################################################
LDFLAGS = -L. \
          -L$(INSTALL_PATH)/lib
# What libraries should be linked with.
LDLIBS =
LDLIBS += $(NS3_LIBFILES)
LDLIBS += -lhelicscpp
LDLIBS += -lhelicscpp-apps
$(info <<<<<<<<<< LDLIBS >>>>>>>>>>)
$(info $(LDLIBS))

$(BIN): $(OBJ)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $^ $(LDFLAGS) $(LDLIBS)

.PHONY: clean
clean:
	rm -f *.o
	rm -f $(BIN)