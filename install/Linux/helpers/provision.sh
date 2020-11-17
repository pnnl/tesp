# build tools
sudo apt-get -y install git
sudo apt-get -y install build-essential
sudo apt-get -y install autoconf
sudo apt-get -y install libtool
sudo apt-get -y install libjsoncpp-dev
sudo apt-get -y install gfortran
sudo apt-get -y install cmake
sudo apt-get -y install subversion
# Java support
sudo apt-get -y install openjdk-11-jre-headless
sudo apt-get -y install openjdk-11-jdk-headless
sudo ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java
# for HELICS and FNCS
sudo apt-get -y install libzmq5-dev
sudo apt-get -y install libczmq-dev
# for GridLAB-D
sudo apt-get -y install libxerces-c-dev
sudo apt-get -y install suitesparse-dev
# for AMES market simulator
sudo apt-get -y install coinor-cbc
# for TESP GUI and plotting
sudo apt-get -y install python3-pip
sudo apt-get -y install python3-tk

