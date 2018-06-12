
echo [$SECONDS] Setting up Atlas Local Root Base
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh --quiet

echo [$SECONDS] Setting up Atlas Software
RELEASE=21.0.20
PACKAGE=AtlasOffline
CMTCONFIG=x86_64-slc6-gcc62-opt
echo [$SECONDS] RELEASE=$RELEASE
echo [$SECONDS] PACKAGE=$PACKAGE
echo [$SECONDS] CMTCONFIG=$CMTCONFIG

source $AtlasSetup/scripts/asetup.sh $RELEASE,$PACKAGE,here,notest --cmtconfig=$CMTCONFIG --makeflags="$MAKEFLAGS" --cmtextratags=ATLAS,useDBRelease
