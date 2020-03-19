javac -classpath ".;java" loadshed.java
set FNCS_CONFIG_FILE=
set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=DEBUG2
set FNCS_TRACE=yes
start /b cmd /c fncs_broker 3 ^>broker.log 2^>^&1
set FNCS_LOG_LEVEL=
start /b cmd /c gridlabd -D WANT_FNCS=1 loadshed.glm ^>gridlabd.log 2^>^&1
start /b cmd /c fncs_player 6h loadshed.player ^>player.log 2^>^&1
set FNCS_CONFIG_FILE=loadshed.yaml
start /b cmd /c java -cp ".;java" -Djava.library.path="java" loadshed 21600 ^>java.log 2^>^&1

