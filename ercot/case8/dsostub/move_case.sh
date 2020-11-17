UDIR="$1"
# echo $UDIR
rm -rf $UDIR
mkdir $UDIR
mv *.log $UDIR
mv *.csv $UDIR
mv *dict.json $UDIR
mv *metrics.json $UDIR
cp ercot_8.json $UDIR

