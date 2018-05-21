
INPUT_FILE=$1
OUTPUT_FILE=$2
WORKDIR=$3

echo [$SECONDS] INPUT_FILE=$INPUT_FILE
echo [$SECONDS] OUTPUT_FILE=$OUTPUT_FILE
echo [$SECONDS] WORKDIR=$WORKDIR

mkdir -p $WORKDIR
cd $WORKDIR

echo [$SECONDS] Setting up Atlas Local Root Base
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
source ${AtlasSetup}/scripts/asetup.sh 21.0.15,AtlasOffline,slc6,gcc49,here

echo [$SECONDS] setting up DB config
export http_proxy=http://10.236.1.194:3128
export HTTP_PROXY=http://10.236.1.194:3128
export DBBASEPATH=/cvmfs/atlas.cern.ch/repo/sw/database/DBRelease/current
export CORAL_DBLOOKUP_PATH=$DBBASEPATH/XMLConfig
export CORAL_AUTH_PATH=$DBBASEPATH/XMLConfig
export DATAPATH=$DBBASEPATH:$DATAPATH
#export CALIBPATH=/cvmfs/atlas.cern.ch/repo/sw/database/GroupData:$CALIBPATH
#unset FRONTIER_SERVER
export ATHENA_PROC_NUMBER=64
#export LHAPATH=/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPATH
#export LHAPDF_DATA_PATH=/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPDF_DATA_PATH
export FRONTIER_SERVER=${FRONTIER_SERVER}\(proxyurl=$HTTP_PROXY\)
export FRONTIER_LOG_LEVEL=info
echo [$SECONDS] FRONTIER_SERVER=$FRONTIER_SERVER
env | sort > env.txt

echo [$SECONDS] test Frontier
/lus/theta-fs0/projects/AtlasADSP/atlas/squid/frontier-squid-3.5.27-4/install/fnget.py --url=http://cmsfrontier.cern.ch:8000/FrontierProd/Frontier --sql="select 1 from dual"

echo [$SECONDS] hostname=$(hostname)
echo [$SECONDS] ifconfig
/sbin/ifconfig

COND=default:OFLCOND-MC16-SDR-14
GEO=default:ATLAS-R2-2016-01-00-01_VALIDATION

echo [$SECONDS] Running Transform
echo [$SECONDS] PWD=$PWD
Sim_tf.py --inputEVNTFile=$INPUT_FILE --outputHITSFile=$OUTPUT_FILE --conditionsTag=$COND --geometryVersion=$GEO --maxEvents=128 --postInclude="default:RecJobTransforms/UseFrontier.py" --preInclude="EVNTtoHITS:SimulationJobOptions/preInclude.BeamPipeKill.py,SimulationJobOptions/preInclude.FrozenShowersFCalOnly.py" --DBRelease="all:current" --preExec="EVNTtoHITS:simFlags.SimBarcodeOffset.set_Value_and_Lock(200000);simFlags.TRTRangeCut=30.0;simFlags.TightMuonStepping=True" --physicsList=FTFP_BERT_ATL_VALIDATION --DataRunNumber=284500 --simulator=FullG4 --truthStrategy=MC15aPlus

# Reco_tf

# athena

# numpy convert

