autoheader
# mkdir m4
aclocal
automake --add-missing
autoconf
./configure --prefix=$TESP_INSTALL --with-zmq=$TESP_INSTALL 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
make
sudo make install
