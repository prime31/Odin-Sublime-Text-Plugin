echo --------------- building ----------------

rem echo odin build %1.odin %~2
odin build %1.odin %~2
@rem if %errorlevel% neq 0 exit /b %errorlevel%

echo --------------- linking -----------------

rem echo link -nologo %1.obj %~3
link -nologo %1.obj /NODEFAULTLIB:LIBCMT %~3
@del *.bc
@del *.ll
@del *.exp
%1.exe