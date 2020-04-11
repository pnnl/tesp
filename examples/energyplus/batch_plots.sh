#declare ROOT=WinterFullServiceRestaurant
#python3 plots.py $ROOT 'Full Service Restaurant, January 3-4' $ROOT.png
#ROOT=SummerFullServiceRestaurant
#python3 plots.py $ROOT 'Full Service Restaurant, August 1-2' $ROOT.png
#
#declare ROOT=WinterQuickServiceRestaurant
#python3 plots.py $ROOT 'Quick Service Restaurant, January 3-4' $ROOT.png
#ROOT=SummerQuickServiceRestaurant
#python3 plots.py $ROOT 'Quick Service Restaurant, August 1-2' $ROOT.png

declare ROOT=SchoolBase
declare TITLE="Secondary School (Base)"
python3 plots.py Winter$ROOT '${TITLE}, January 3-4' Winter$ROOT.png
python3 plots.py Summer$ROOT '${TITLE}, August 1-2' Summer$ROOT.png



