REM Process and load an sql file
REM You will need to change parameters to suit your setup
REM
REM run the conversion program
mstopsql3.py  example.sql debug > result.sql 2>&1
REM feed the resulting postgres sql to postgres
"c:\Program Files\PostgreSQL\8.3\bin\psql" -U postgres -h 192.168.1.106 mydata < result.sql
REM execute the msload() function that contains the new sql code
"c:\Program Files\PostgreSQL\8.3\bin\psql" -U postgres -h 192.168.1.106 mydata < msload.sql
pause
