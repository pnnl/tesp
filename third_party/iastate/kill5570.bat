rem FOR /F "tokens=5 delims= " %%P IN ('netstat -a -n -o | findstr :5570') DO TaskKill.exe /PID %%P /F /T
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5570" ') do taskkill /f /pid %%a

