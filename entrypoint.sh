#!/bin/bash
if [ $# -eq  0 ]
then
    args="-h"
else
    args=$@
fi
echo "apifuzzer args=$args"
./APIFuzzer $args
