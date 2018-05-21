
INPUT_FILE=$1
OUTPUT_FILE=$2
WORKING_DIR=$3
FIRST_EVENT=$4

echo [$SECONDS] INPUT_FILE=$INPUT_FILE
echo [$SECONDS] OUTPUT_FILE=$OUTPUT_FILE
echo [$SECONDS] WORKING_DIR=$WORKING_DIR
echo [$SECONDS] FIRST_EVENT=$FIRST_EVENT

mkdir -p $WORKING_DIR
cd $WORKING_DIR

echo [$SECONDS] Setting up Atlas Local Root Base
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
source ${AtlasSetup}/scripts/asetup.sh 19.2.5.32.2,MCProd,slc6,gcc47,here

echo [$SECONDS] setting up DB config
export DBBASEPATH=/cvmfs/atlas.cern.ch/repo/sw/database/DBRelease/31.8.1
export CORAL_DBLOOKUP_PATH=$DBBASEPATH/XMLConfig
export CORAL_AUTH_PATH=$DBBASEPATH/XMLConfig
export DATAPATH=$DBBASEPATH:$DATAPATH
export CALIBPATH=/cvmfs/atlas.cern.ch/repo/sw/database/GroupData:$CALIBPATH
unset FRONTIER_SERVER

export LHAPATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPATH
export LHAPDF_DATA_PATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPDF_DATA_PATH
env | sort > env.txt

echo [$SECONDS] Running Transform

cp /lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/evnt_prod/MC15JobOpts-00-04-24_v0.tar.gz ./
find $PWD -maxdepth 1 -mindepth 1 -type d -exec cp -r {} ./ \;

Generate_tf.py --jobConfig=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/evnt_prod/gentf_jo.py --preExec="input_lhe_filename='$INPUT_FILE'" --outputEVNTFile=$OUTPUT_FILE --runNumber=1 --ecmEnergy=13000 --evgenJobOpts=MC15JobOpts-00-04-24_v0.tar.gz --firstEvent=$FIRST_EVENT

# AtlasProduction_19.2.3.7
# Sim_tf --inputEVNTFile=input --outputHITSFile=output --conditionsTag=default:OFLCOND-RUN12-SDR-19 --geometryVersion=default:ATLAS-R2-2015-03-01-00_VALIDATION

# Reco_tf

# athena

# numpy convert

