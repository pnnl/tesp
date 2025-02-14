#  Copyright (c) 2017-2024 Battelle Memorial Institute
#  See LICENSE file at https://github.com/pnnl/tesp
#  file: go.sh


autoheader
# mkdir m4
aclocal
automake --add-missing
autoconf
./configure --prefix=$TESP_INSTALL --with-zmq=$TESP_INSTALL 'CXXFLAGS=-w -O2' 'CFLAGS=std=c++14 -w -O2'
make
sudo make install
