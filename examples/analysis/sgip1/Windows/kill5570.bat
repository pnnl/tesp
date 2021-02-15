rem FOR /F "tokens=5 delims= " %%P IN ('netstat -a -n -o | findstr :5570') DO TaskKill.exe /PID %%P /F /T

@Echo Off
SetLocal
Set "PID="
For /F "Tokens=*" %%a In ('NetStat -a -n -o^|Find ":5570 "') Do (
    For %%b In (%%a) Do Set PID=%%b
)
If Defined PID TaskKill /F /PID %PID%
