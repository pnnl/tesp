javac -classpath ".:$JAVAPATH/helics.jar" helicstest.java
java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" helicstest
