autoheader
# mkdir m4
aclocal
automake --add-missing
autoconf
./configure # --prefix=$HOME/FNCS_install --with-zmq=$HOME/FNCS_install
make
sudo make install
