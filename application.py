import subprocess,logging,stat,os
logger = logging.getLogger(__name__)

class Application:
   ''' run a templated application in a subprocess providing hooks for monitoring '''
   def __init__(self,name,cmd,args):

      # name of the application (string expected)
      self.name         = name
      # command binary (string expected)
      self.cmd          = cmd
      # command line arguments (list of 2-value tuples expected)
      self.args         = args
      # place holder for process
      self.process      = None


   def start(self):

      # create command
      command = self.cmd

      # parse args
      for key,value in self.args:
         command += ' --{key} {value}'.format(key,value)

      # launch process
      self.process = subprocess.Popen(command.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)


   def terminate_process(self):
      self.process.terminate()

   def kill_process(self):
      self.process.kill()

   def process_running(self):
      if self.process.poll() is None:
         return True
      return False

   def wait_on_process(self):
      self.process.wait()

   def block_and_get_output(self,input=None):
      return self.process.communicate(input)

   def send_signal_to_process(self,signal):
      self.process.send_signal(signal)

   def get_returncode(self):
      self.process.returncode

   def get_pid(self):
      self.process.pid


class AthenaApplication(Application):
   ''' run an athena-based application in a subprocess, setting up ALRB and release '''
   ATHENA_CMDS=['athena','Generate_tf.py','Sim_tf.py','Reco_tf.py']

   athena_script_template = '''#!/bin/bash
echo [$SECONDS] Start inside Singularity
echo [$SECONDS] DATE=$(date)
WORKDIR=$1
echo [$SECONDS] WORKDIR=$WORKDIR

cd $WORKDIR

export ATHENA_PROC_NUMBER=128 # AthenaMP workers per node

echo [$SECONDS] ATHENA_PROC_NUMBER:   $ATHENA_PROC_NUMBER

echo [$SECONDS] Setting up Atlas Local Root Base
export ATLAS_LOCAL_ROOT_BASE={ATLAS_LOCAL_ROOT_BASE}
source $ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh --quiet

echo [$SECONDS] Setting up Atlas Software
RELEASE={release}
PACKAGE={package}
CMTCONFIG={cmtConfig}
echo [$SECONDS] RELEASE=$RELEASE
echo [$SECONDS] PACKAGE=$PACKAGE
echo [$SECONDS] CMTCONFIG=$CMTCONFIG

source $AtlasSetup/scripts/asetup.sh $RELEASE,$PACKAGE --cmtconfig=$CMTCONFIG --makeflags=\"$MAKEFLAGS\" --cmtextratags=ATLAS,useDBRelease {gcclocation}

DBBASEPATH=$ATLAS_DB_AREA/DBRelease/current
export CORAL_DBLOOKUP_PATH=$DBBASEPATH/XMLConfig
export CORAL_AUTH_PATH=$DBBASEPATH/XMLConfig
export DATAPATH=$DBBASEPATH:$DATAPATH
mkdir poolcond
export DBREL_LOCATION=$ATLAS_DB_AREA/DBRelease
cp $DBREL_LOCATION/current/poolcond/*.xml poolcond
export DATAPATH=$PWD:$DATAPATH


echo [$SECONDS] PYTHON Version:       $(python --version)
echo [$SECONDS] PYTHONPATH:           $PYTHONPATH
echo [$SECONDS] LD_LIBRARY_PATH:      $LD_LIBRARY_PATH
env | sort > env_dump.txt

echo [$SECONDS] Starting transformation
{transformation} {jobPars}
echo [$SECONDS] Transform exited with return code: $?
echo [$SECONDS] Exiting
"""


'''

   def __init__(self,name,cmd,args,
                release,package,
                cmtConfig,gcclocation,
                ATLAS_LOCAL_ROOT_BASE='/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase',
                output_script_name = 'runscript.sh'):
      super(AthenaApplication,self).__init__(name,cmd,args)

      # ensure user passed allowed application
      if cmd not in ATHENA_CMDS:
         raise Exception('Unsupported Athena Application: user specified %s which is not in %s',cmd,self.ATHENA_CMDS)

      # set custom variables in the script
      script_content = athena_script_template.format(
         ATLAS_LOCAL_ROOT_BASE = ATLAS_LOCAL_ROOT_BASE,
         release = release,
         package = package,
         cmtConfig = cmtConfig,
         gcclocation = gcclocation,
         transformation = self.cmd,
         jobPars = self.args)

      # write script 
      open(output_script_name,'w').write(script_content)
      # set executable
      os.chmod(output_script_name,stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)

      # set the command to be the script
      self.cmd = output_script_name
      self.args = []
      

