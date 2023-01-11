#!/usr/bin/env bash

set -x

cd ../Winamp2/
7z a ../avs.sh/avs.sh/files/vis_avs_builds/vis_avs_$(date +%Y%m%d_%H%M).zip \
    Plugins/vis_avs.dll \
    avcodec-59.dll \
    avformat-59.dll \
    avutil-57.dll \
    libbz2-1.dll \
    libgcc_s_dw2-1.dll \
    libiconv-2.dll \
    liblzma-5.dll \
    libssp-0.dll \
    libstdc++-6.dll \
    libwinpthread-1.dll \
    swresample-4.dll \
    swscale-6.dll \
    zlib1.dll \
    #

