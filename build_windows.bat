@call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

odin build %1.odin %2
if %errorlevel% neq 0 exit /b %errorlevel%

link -nologo %1.obj %3
%1.exe