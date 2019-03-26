javac -classpath ".:helics.jar" helicshed.java
(exec helics_broker -f 2 --loglevel=3 --name=mainbroker &> broker.log &)
(exec gridlabd loadshed.glm &> gridlabd.log &)
(exec java -classpath ".:helics.jar" -Djava.library.path="/usr/local/java" helicshed &> java.log &)

