autoheader
# mkdir m4
aclocal
automake --add-missing
autoconf
./configure --prefix=$FNCS_INSTALL --with-zmq=$FNCS_INSTALL
make
sudo make install
