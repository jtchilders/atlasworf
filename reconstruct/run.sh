
INPUT_FILE=$1
OUTPUT_RDO_FILE=$2
OUTPUT_ESD_FILE=$3
WORKDIR=$4

echo [$SECONDS] INPUT_FILE=$INPUT_FILE
echo [$SECONDS] OUTPUT_RDO_FILE=$OUTPUT_RDO_FILE
echo [$SECONDS] OUTPUT_ESD_FILE=$OUTPUT_ESD_FILE
echo [$SECONDS] WORKDIR=$WORKDIR

mkdir -p $WORKDIR
cd $WORKDIR

echo [$SECONDS] Setting up Atlas Local Root Base
export PANDA_RESOURCE="ALCF_Theta_ES";
export FRONTIER_ID="[11829903_3550084207]";
export CMSSW_VERSION=$FRONTIER_ID;
export RUCIO_APPID="recon";
export RUCIO_ACCOUNT="pilot";
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
source ${AtlasSetup}/scripts/asetup.sh AtlasOffline,21.0.20,notest,here --platform x86_64-slc6-gcc62-opt --makeflags="$MAKEFLAGS" 

echo [$SECONDS] setting up DB config
export http_proxy=http://10.236.1.194:3128
export HTTP_PROXY=http://10.236.1.194:3128
#export DBBASEPATH=/cvmfs/atlas.cern.ch/repo/sw/database/DBRelease/current
#export CORAL_DBLOOKUP_PATH=$DBBASEPATH/XMLConfig
#export CORAL_AUTH_PATH=$DBBASEPATH/XMLConfig
#export DATAPATH=$DBBASEPATH:$DATAPATH
#export CALIBPATH=/cvmfs/atlas.cern.ch/repo/sw/database/GroupData:$CALIBPATH
#unset FRONTIER_SERVER
#export ATHENA_PROC_NUMBER=128
#export LHAPATH=/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPATH
#export LHAPDF_DATA_PATH=/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPDF_DATA_PATH
export FRONTIER_SERVER=${FRONTIER_SERVER}\(proxyurl=$HTTP_PROXY\)
export FRONTIER_LOG_LEVEL=info
echo [$SECONDS] FRONTIER_SERVER=$FRONTIER_SERVER
env | sort > env.txt

echo [$SECONDS] hostname=$(hostname)
echo [$SECONDS] ifconfig
/sbin/ifconfig

COND=default:OFLCOND-MC16-SDR-16
GEO=default:ATLAS-R2-2016-01-00-01

MINBIAS_HIGH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/mc16_13TeV.361239.Pythia8EvtGen_A3NNPDF23LO_minbias_inelastic_high.simul.HITS.e4981_s3087_s3111/HITS.10701335._002320.pool.root.1
MINBIAS_LOW=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/mc16_13TeV.361238.Pythia8EvtGen_A3NNPDF23LO_minbias_inelastic_low.simul.HITS.e4981_s3087_s3111/HITS.10701323._000269.pool.root.1


echo [$SECONDS] Running Transform
echo [$SECONDS] PWD=$PWD

Reco_tf.py --inputHITSFile=$INPUT_FILE --maxEvents=20 --postExec 'all:CfgMgr.MessageSvc().setError+=["HepMcParticleLink"]' 'ESDtoAOD:fixedAttrib=[s if "CONTAINER_SPLITLEVEL = '"'"'99'"'"'" not in s else "" for s in svcMgr.AthenaPoolCnvSvc.PoolAttributes];
svcMgr.AthenaPoolCnvSvc.PoolAttributes=fixedAttrib' 'RDOtoRDOTrigger:conddb.addOverride("/CALO/Ofl/Noise/PileUpNoiseLumi","CALOOflNoisePileUpNoiseLumi-mc15-mu30-dt25ns")' 'ESDtoAOD:CILMergeAOD.removeItem("xAOD::CaloClusterAuxContainer#CaloCalTopoClustersAux.LATERAL.LONGITUDINAL.SECOND_R.SECOND_LAMBDA.CENTER_MAG.CENTER_LAMBDA.FIRST_ENG_DENS.ENG_FRAC_MAX.ISOLATION.ENG_BAD_CELLS.N_BAD_CELLS.BADLARQ_FRAC.ENG_BAD_HV_CELLS.N_BAD_HV_CELLS.ENG_POS.SIGNIFICANCE.CELL_SIGNIFICANCE.CELL_SIG_SAMPLING.AVG_LAR_Q.AVG_TILE_Q.EM_PROBABILITY.PTD.BadChannelList");
CILMergeAOD.add("xAOD::CaloClusterAuxContainer#CaloCalTopoClustersAux.N_BAD_CELLS.ENG_BAD_CELLS.BADLARQ_FRAC.AVG_TILE_Q.AVG_LAR_Q.CENTER_MAG.ENG_POS.CENTER_LAMBDA.SECOND_LAMBDA.SECOND_R.ISOLATION.EM_PROBABILITY");
StreamAOD.ItemList=CILMergeAOD()' --postInclude default:PyJobTransforms/UseFrontier.py --preExec 'all:rec.Commissioning.set_Value_and_Lock(True);
from AthenaCommon.BeamFlags import jobproperties;
jobproperties.Beam.numberOfCollisions.set_Value_and_Lock(20.0);
from LArROD.LArRODFlags import larRODFlags;
larRODFlags.NumberOfCollisions.set_Value_and_Lock(20);
larRODFlags.nSamples.set_Value_and_Lock(4);
larRODFlags.doOFCPileupOptimization.set_Value_and_Lock(True);
larRODFlags.firstSample.set_Value_and_Lock(0);
larRODFlags.useHighestGainAutoCorr.set_Value_and_Lock(True)' 'all:from TriggerJobOpts.TriggerFlags import TriggerFlags as TF;
TF.run2Config='"'"'2016'"'"'' 'RAWtoESD:from InDetRecExample.InDetJobProperties import InDetFlags;
 InDetFlags.cutLevel.set_Value_and_Lock(14);
 from JetRec import JetRecUtils;
f=lambda s:["xAOD::JetContainer#AntiKt4%sJets"%(s,),"xAOD::JetAuxContainer#AntiKt4%sJetsAux."%(s,),"xAOD::EventShape#Kt4%sEventShape"%(s,),"xAOD::EventShapeAuxInfo#Kt4%sEventShapeAux."%(s,),"xAOD::EventShape#Kt4%sOriginEventShape"%(s,),"xAOD::EventShapeAuxInfo#Kt4%sOriginEventShapeAux."%(s,)];
 JetRecUtils.retrieveAODList = lambda : f("EMPFlow")+f("LCTopo")+f("EMTopo")+["xAOD::EventShape#NeutralParticleFlowIsoCentralEventShape","xAOD::EventShapeAuxInfo#NeutralParticleFlowIsoCentralEventShapeAux.", "xAOD::EventShape#NeutralParticleFlowIsoForwardEventShape","xAOD::EventShapeAuxInfo#NeutralParticleFlowIsoForwardEventShapeAux.", "xAOD::EventShape#ParticleFlowIsoCentralEventShape","xAOD::EventShapeAuxInfo#ParticleFlowIsoCentralEventShapeAux.", "xAOD::EventShape#ParticleFlowIsoForwardEventShape","xAOD::EventShapeAuxInfo#ParticleFlowIsoForwardEventShapeAux.", "xAOD::EventShape#TopoClusterIsoCentralEventShape","xAOD::EventShapeAuxInfo#TopoClusterIsoCentralEventShapeAux.", "xAOD::EventShape#TopoClusterIsoForwardEventShape","xAOD::EventShapeAuxInfo#TopoClusterIsoForwardEventShapeAux.","xAOD::CaloClusterContainer#EMOriginTopoClusters","xAOD::ShallowAuxContainer#EMOriginTopoClustersAux.","xAOD::CaloClusterContainer#LCOriginTopoClusters","xAOD::ShallowAuxContainer#LCOriginTopoClustersAux."];
 from eflowRec.eflowRecFlags import jobproperties;
 jobproperties.eflowRecFlags.useAODReductionClusterMomentList.set_Value_and_Lock(True);
 from TriggerJobOpts.TriggerFlags import TriggerFlags;
TriggerFlags.AODEDMSet.set_Value_and_Lock("AODSLIM");
' 'all:from BTagging.BTaggingFlags import BTaggingFlags;
   BTaggingFlags.btaggingAODList=["xAOD::BTaggingContainer#BTagging_AntiKt4EMTopo","xAOD::BTaggingAuxContainer#BTagging_AntiKt4EMTopoAux.","xAOD::BTagVertexContainer#BTagging_AntiKt4EMTopoJFVtx","xAOD::BTagVertexAuxContainer#BTagging_AntiKt4EMTopoJFVtxAux.","xAOD::VertexContainer#BTagging_AntiKt4EMTopoSecVtx","xAOD::VertexAuxContainer#BTagging_AntiKt4EMTopoSecVtxAux.-vxTrackAtVertex"];
   ' 'ESDtoAOD:from ParticleBuilderOptions.AODFlags import AODFlags;
    AODFlags.ThinGeantTruth.set_Value_and_Lock(True);
     AODFlags.ThinNegativeEnergyCaloClusters.set_Value_and_Lock(True);
    AODFlags.ThinNegativeEnergyNeutralPFOs.set_Value_and_Lock(True);
    from JetRec import JetRecUtils;
    aodlist = JetRecUtils.retrieveAODList();
    JetRecUtils.retrieveAODList = lambda : [item for item in aodlist if not "OriginTopoClusters" in item];
   '  --skipEvents=0 --autoConfiguration=everything --conditionsTag $COND --geometryVersion=$GEO --runNumber=344710 --digiSeedOffset1=9 --digiSeedOffset2=9 --digiSteeringConf=StandardSignalOnlyTruth --AMITag=r9364  --outputRDOFile=$OUTPUT_RDO_FILE --outputESDFile=$OUTPUT_ESD_FILE --jobNumber=9 --DBRelease=current


echo [$SECONDS] reco exit code $?
