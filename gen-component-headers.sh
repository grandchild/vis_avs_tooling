#!/usr/bin/env bash

# git checkout avs/vis_avs/r_*.cpp

CPPS=$(ls avs/vis_avs/r_*.cpp | grep -v avsres)

# ls avs/vis_avs/c_*.h \
#     | grep -v c__base \
#     | grep -v defs \
#     | grep -v colormap \
#     | grep -v list \
#     | grep -v stack \
#     | grep -v transition \
#     | grep -v unkn \
#     | while read -r hpp ; do
#         rm $hpp
#     done

# DEFINES="MOD_NAME|C_THISCLASS|C_DELAY|SET_BEAT|CLR_BEAT|REFFECT_|MD_|HORIZ|VERT|D_|M_|ADDBORDERS_"

# for cpp in ${CPPS[@]} ; do
#     export HPP=${cpp/r_/c_}
#     export HPP=${HPP/.cpp/.h}
#     echo "==== $HPP ===="
#     echo -e '#include "c__base.h"' | tee $HPP
#     echo | tee -a $HPP
#     grep -E "#define ($DEFINES)" ${cpp}_ | tee -a $HPP
#     echo | tee -a $HPP
#     echo | tee -a $HPP
#     sed -r -n '/^class C_/,/};/p' ${cpp}_ | tee -a $HPP
#     echo '------------------------------'
#     sed -ri \
#         -e '/^class C_/,/};/d' \
#         -e "/#define ($DEFINES)/d" \
#         -e '/\/\/ this will be the directory/d' \
#         -e "s/#include <windows.h>/#include \"$(basename $HPP)\"\n&/" \
#         $cpp
#     echo
# done

DEFINES="RGB_TO_BGR|BGR_TO_RGB|TRANSLATE_|CLAMP\\(|TEXERII_EXAMPLES_FIRST_ID"
STATIC_VARS="g_cust_colors|g_ColorSetValue|g_currently_selected_color_id"
FUNC_DECLS="void (save|load)_map_file"
NEED_COMMCTRL=(
    r_addborders.cpp
    r_avi.cpp
    r_blit.cpp
    r_bpm.cpp
    r_bright.cpp
    r_bump.cpp
    r_colorfade.cpp
    r_colormap.cpp
    r_colorreduction.cpp
    r_contrast.cpp
    r_dotfnt.cpp
    r_dotgrid.cpp
    r_dotpln.cpp
    r_fadeout.cpp
    r_grain.cpp
    r_interf.cpp
    r_interleave.cpp
    r_linemode.cpp
    r_list.cpp
    r_mirror.cpp
    r_mosaic.cpp
    r_nfclr.cpp
    r_oscring.cpp
    r_oscstar.cpp
    r_parts.cpp
    r_picture.cpp
    r_rotblit.cpp
    r_stack.cpp
    r_stars.cpp
    r_text.cpp
    r_timescope.cpp
    r_transition.cpp
    r_waterbump.cpp
)
NEED_CDEFS=(
    r_bump.cpp
    r_colormap.cpp
    r_dmove.cpp
    r_stack.cpp
    r_texer2.cpp
)
NEED_RENDERH_CFGWNDH=(
    r_transition.cpp
)

for cpp in ${CPPS[@]} ; do
    export HPP=${cpp/r_/c_}
    export HPP=${HPP/.cpp/.h}
    export GCPP=${cpp/r_/g_}
    echo "==== $GCPP ===="
    rm $GCPP ; touch $GCPP
    if [[ " ${NEED_CDEFS[@]} " =~ " $(basename $cpp) " ]]; then
        echo -e "#include \"c__defs.h\"" | tee -a $GCPP
    fi
    echo -e "#include \"g__lib.h\"" | tee -a $GCPP
    echo -e "#include \"g__defs.h\"" | tee -a $GCPP
    echo -e "#include \"$(basename $HPP)\"" | tee -a $GCPP
    echo -e "#include \"resource.h\"" | tee -a $GCPP
    echo -e "#include <windows.h>" | tee -a $GCPP
    if [[ " ${NEED_COMMCTRL[@]} " =~ " $(basename $cpp) " ]]; then
        echo -e "#include <commctrl.h>" | tee -a $GCPP
    fi
    if [[ " ${NEED_RENDERH_CFGWNDH[@]} " =~ " $(basename $cpp) " ]]; then
        echo -e "#include \"render.h\"" | tee -a $GCPP
        echo -e "#include \"cfgwnd.h\"" | tee -a $GCPP
    fi
    echo | tee -a $GCPP
    (rg --pcre2 -U "^#define ($DEFINES)[^\\n\\\\]*(?!:\\\\\\n)(\\\\\\n.*)?" $cpp && echo) | tee -a $GCPP
    echo | tee -a $GCPP
    (grep -E "^static .* ($STATIC_VARS)" ${cpp} && echo) | tee -a $GCPP
    (grep -E "^($FUNC_DECLS).*;$" ${cpp} && echo) | tee -a $GCPP
    (sed -r -n '/^static void EnableWindows/,/^}$/p' $cpp | tee >( grep -q . && echo ) ) | tee -a $GCPP
    (sed -r -n '/^int getMode/,/^}$/p' $cpp | tee >( grep -q . && echo ) ) | tee -a $GCPP
    sed -r -n '/^(static )?(int|void) win32_(dlgproc|uiprep)_/,/^}$/{/^}$/G;p}' $cpp | tee -a $GCPP
    (sed -r -n '/^bool endswithn/,/^}$/p' $cpp | tee >( grep -q . && echo ) ) | tee -a $GCPP
    (sed -r -n '/^void ((save|load)_map_file|load_examples).*\{$/,/^}$/{/^}$/G;p}' $cpp | tee >( grep -q . && echo ) ) | tee -a $GCPP
    echo '------------------------------'
    sed -ri \
        -e '/^static void EnableWindows/,/^}$/d' \
        -e '/^int getMode/,/^}$/d' \
        -e '/^bool endswithn/,/^}$/d' \
        -e '/^void ((save|load)_map_file|load_examples)/,/^}$/d' \
        -e '/^(static )?(int|void) win32_(dlgproc|uiprep)_/,/^}$/d' \
        -e "/^($FUNC_DECLS)/d" \
        -e "/^static .* ($STATIC_VARS)/d" \
        -e "/#define ($DEFINES)/d" \
        -e "/b_max/d" \
        -e "/this is where we deal with the configuration screen/d" \
        -e "/configuration dialog stuff/d" \
        $cpp
    sed -ri '/^#include <(windows|commctrl|vfw).h>/d' $cpp
    sed -ri '/^#include "resource.h"/d' $cpp
    echo
done
