UDIR="$1"
# echo $UDIR
rm -rf $UDIR
mkdir $UDIR
#echo $TESP_INSTALL
cp -r $TESP_INSTALL/share/examples $UDIR
cp -r $TESP_INSTALL/share/ercot $UDIR
cp $TESP_INSTALL/autotest.py $UDIR

