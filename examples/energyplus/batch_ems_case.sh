declare -r WINTER_START="2013-01-03 00:00:00"
declare -r WINTER_END="2013-01-05 00:00:00"
declare -r SUMMER_START="2013-08-01 00:00:00"
declare -r SUMMER_END="2013-08-03 00:00:00"

./run_ems_case.sh "FullServiceRestaurant" "$WINTER_START" "$WINTER_END" "WinterFullServiceRestaurant"
./run_ems_case.sh "FullServiceRestaurant" "$SUMMER_START" "$SUMMER_END" "SummerFullServiceRestaurant"

./run_ems_case.sh "SchoolBase" "$WINTER_START" "$WINTER_END" "WinterSchoolBase"
./run_ems_case.sh "SchoolBase" "$SUMMER_START" "$SUMMER_END" "SummerSchoolBase"

