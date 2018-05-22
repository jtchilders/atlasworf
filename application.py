import subprocess,logging,stat,os
logger = logging.getLogger(__name__)
from mpi4py import MPI

class Application(object):
   ''' run a templated application in a subprocess providing hooks for monitoring '''

   def __init__(self,name,settings,args,defaults=None):

      # app name
      self.name         = name

      self.settings     = settings
      self.args         = args
      self.defaults     = defaults


   def make_cmdline_arg_string(self):
      # parse args
      outargs = ''
      for key in self.args:
         value = self.args[key]
         command += ' --{0} {1}'.format(key,value)

      return outargs


   def start(self,rundir=None):

      # create command
      command = self.get_command()

      # add container command prefix
      if self.settings['use_container'] in ['true','True','1','yes']:
         command = self.settings['container_prefix_cmd'] + ' ' + command

      # launch process
      logger.info('launching command = "%s"',command)
      self.process = subprocess.Popen(command.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=rundir)

   def get_command(self):
      ''' may need to override this function '''
      command = self.settings['command']
      command += self.make_cmdline_arg_string()
      return command


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
      return self.process.returncode

   def get_pid(self):
      return self.process.pid


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

# setup for Generate_tf.py
export LHAPATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPATH
export LHAPDF_DATA_PATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPDF_DATA_PATH


echo [$SECONDS] PYTHON Version:       $(python --version)
echo [$SECONDS] PYTHONPATH:           $PYTHONPATH
echo [$SECONDS] LD_LIBRARY_PATH:      $LD_LIBRARY_PATH
env | sort > env_dump.txt

echo [$SECONDS] Starting transformation
{transformation} {jobPars}
echo [$SECONDS] Transform exited with return code: $?
echo [$SECONDS] Exiting
'''

   def __init__(self,name,settings,args,defaults,rundir):
      super(AthenaApplication,self).__init__(name,settings,args,defaults)

      # ensure user passed allowed application
      if settings['command'] not in self.ATHENA_CMDS:
         raise Exception('Unsupported Athena Application: user specified %s which is not in %s',settings['command'],self.ATHENA_CMDS)

      self.rundir = rundir


   def get_command(self):
      command = self.make_athena_script()
      return command


   def make_athena_script(self):
      # set custom variables in the script
      script_content = self.athena_script_template.format(
         ATLAS_LOCAL_ROOT_BASE = self.defaults['atlas_local_root_base'],
         release = self.settings['release'],
         package = self.settings['package'],
         cmtConfig = self.settings['cmtConfig'],
         gcclocation = self.settings['gcclocation'],
         transformation = self.settings['command'],
         jobPars = self.make_cmdline_arg_string())

      # write script
      script_filename = os.path.join(self.rundir,self.settings['output_script_name'])
      open(script_filename,'w').write(script_content)
      # set executable
      os.chmod(script_filename,stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)

      return script_filename

      

class GenerateTF(AthenaApplication):
   ''' run a Generate_tf.py job '''

   def __init__(self,name,settings,args,defaults,rundir):
      super(GenerateTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['firstEvent'] = str(int(self.settings['event_counter_offset']) + MPI.COMM_WORLD.Get_rank() * int(self.defaults['events_per_rank']))


def get_athena_app(name,settings,args,defaults,rundir):

   if 'Generate_tf.py' in settings['command']:
      return GenerateTF(name,settings,args,defaults,rundir)

