#!/usr/bin/env bash

NAME=texer
DIR="$HOME/dev/avs/vis_avs/avs/vis_avs"
FILES=(
    c_$NAME.h
    r_$NAME.cpp
    g_$NAME.cpp
)

cat << EOF > "$DIR/c_$NAME.h"
#pragma once

#include "c__base.h"

#include <windows.h>

#define MOD_NAME "--- FILL IN MOD NAME FOR $NAME HERE"

class C_$NAME : public C_RBASE {
   public:
    C_$NAME();
    virtual ~C_$NAME();
    virtual int render(char visdata[2][2][576],
                       int isBeat,
                       int* framebuffer,
                       int* fbout,
                       int w,
                       int h);
    virtual char* get_desc();
    virtual void load_config(unsigned char* data, int len);
    virtual int save_config(unsigned char* data);
};
EOF

cat << EOF > "$DIR/r_$NAME.cpp"
#include "c_$NAME.h"
EOF

cat << EOF > "$DIR/g_$NAME.cpp"
#include "c_$NAME.h"

#include "c__defs.h"
#include "g__defs.h"
#include "g__lib.h"
#include "resource.h"

#include <commctrl.h>
#include <windows.h>
EOF

for file in ${FILES[@]} ; do
    subl "$DIR/$file"
done
