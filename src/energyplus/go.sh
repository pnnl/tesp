#  Copyright (C) 2017-2022 Battelle Memorial Institute 
#  file: go.sh


autoheader
# mkdir m4
aclocal
automake --add-missing
autoconf
./configure --prefix=$TESP_INSTALL --with-zmq=$TESP_INSTALL 'CXXFLAGS=-w -O2' 'CFLAGS=std=c++14 -w -O2'
make
sudo make install
