autoheader
aclocal
automake --add-missing
autoconf
./configure --prefix=$HOME/FNCS_install --with-zmq=$HOME/FNCS_install
make
make install
