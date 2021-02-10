declare -r JAVAPATH=$TESP_INSTALL/java
javac -classpath ".:$JAVAPATH/helics.jar" helicstest.java
java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" helicstest
