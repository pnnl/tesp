javac -classpath ".:$JAVAPATH/helics.jar" helicshed.java
(exec helics_broker -f 2 --loglevel=3 --name=mainbroker &> broker.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
(exec java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" helicshed &> java.log &)

