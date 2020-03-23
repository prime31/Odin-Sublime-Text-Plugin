@call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
odin build %1.odin
if %errorlevel% neq 0 exit /b %errorlevel%
set PATH=%PATH%;%2
%1.exe