REM load a test sql file
REM
mstest.py 
"c:\Program Files\PostgreSQL\8.3\bin\psql" -U postgres -h 192.168.1.107 ccmdata < mstest.sql > testlog.log 2>&1
msrep.py
pause
