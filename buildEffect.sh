#!/bin/bash
# buildEffects

cd $1
for file in `find ./** -name "$2"` ;
do
    # Hush, wine...
    export WINEDEBUG=fixme-all,err-all

    # Build the effect
    wine64 ~/.wine/drive_c/Program\ Files\ \(x86\)/Microsoft\ DirectX\ SDK\ \(June\ 2010\)/Utilities/bin/x64/fxc.exe\
     /T fx_2_0 $file /Fo "`dirname $file`/`basename $file .fx`.fxb"

    echo ""

done