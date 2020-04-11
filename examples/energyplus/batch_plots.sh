declare ROOT=WinterFullServiceRestaurant
python3 plots.py $ROOT 'Full Service Restaurant, January 3-4' $ROOT.png
ROOT=SummerFullServiceRestaurant
python3 plots.py $ROOT 'Full Service Restaurant, August 1-2' $ROOT.png

declare ROOT=WinterSchoolBase
python3 plots.py $ROOT 'Secondary School (Base), January 3-4' $ROOT.png
ROOT=SummerSchoolBase
python3 plots.py $ROOT 'Secondary School (Base), August 1-2' $ROOT.png



