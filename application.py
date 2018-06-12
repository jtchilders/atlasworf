import subprocess,logging,stat,os,shutil,glob,tarfile
from mpi4py import MPI
logger = logging.getLogger(__name__)


class Application(object):
   ''' run a templated application in a subprocess providing hooks for monitoring '''

   def __init__(self,name,settings,args,defaults=None,rundir=None):

      # app name
      self.name         = name

      self.rundir       = rundir

      self.settings     = settings
      self.args         = args
      self.defaults     = defaults


   def get_rundir(self):
      return self.rundir

   def make_cmdline_arg_string(self):
      # parse args
      outargs = ''
      for key in self.args:
         value = self.args[key]
         outargs += ' --{0} {1}'.format(key,value)

      return outargs

   def stage_files(self,stagedir):
      shutil.copy(self.stdout_filename,stagedir)
      shutil.copy(self.stderr_filename,stagedir)



   def start(self):

      # create command
      command = self.get_command()

      # add container command prefix
      if 'use_container' in self.settings and self.settings['use_container'] in ['true','True','1','yes']:
         command = self.settings['container_prefix_cmd'] + ' ' + command

      # launch process
      logger.info('launching command = "%s"',command)
      self.stdout_filename = ('%05d_%s.stdout' % (MPI.COMM_WORLD.Get_rank(),self.name))
      self.stderr_filename = ('%05d_%s.stderr' % (MPI.COMM_WORLD.Get_rank(),self.name))
      if self.rundir is not None:
         self.stdout_filename = os.path.join(self.rundir,self.stdout_filename)
         self.stderr_filename = os.path.join(self.rundir,self.stderr_filename)
      
      self.process = subprocess.Popen(command.split(),stdout=open(self.stdout_filename,'w'),
                                      stderr=open(self.stderr_filename,'w'),cwd=self.rundir)

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

   # def block_and_get_output(self,input=None):
   #   return self.process.communicate(input)

   def send_signal_to_process(self,signal):
      self.process.send_signal(signal)

   def get_returncode(self):
      return self.process.returncode

   def get_pid(self):
      return self.process.pid


class AthenaApplication(Application):
   ''' run an athena-based application in a subprocess, setting up ALRB and release '''
   ATHENA_CMDS = ['athena','Generate_tf.py','Sim_tf.py','Reco_tf.py']

   athena_script_template = '''#!/bin/bash
echo [$SECONDS] Start inside Singularity
echo [$SECONDS] DATE=$(date)
WORKDIR=$1
echo [$SECONDS] WORKDIR=$WORKDIR
USE_MP={use_mp}

cd $WORKDIR

if [ "$USE_MP" = "TRUE" ] || [ "$USE_MP" = "true" ] || [ "$USE_MP" = "True" ]; then
   export ATHENA_PROC_NUMBER={ATHENA_PROC_NUMBER}
fi

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

source $AtlasSetup/scripts/asetup.sh $RELEASE,$PACKAGE,here,notest --cmtconfig=$CMTCONFIG --makeflags=\"$MAKEFLAGS\" --cmtextratags=ATLAS,useDBRelease {gcclocation}

if [ "{transformation}" = "Sim_tf.py" ]; then
   echo [$SECONDS] Setting up database for local copy: ATLAS_DB_AREA=$ATLAS_DB_AREA
   DBBASEPATH=$ATLAS_DB_AREA/DBRelease/current
   export CORAL_DBLOOKUP_PATH=$DBBASEPATH/XMLConfig
   export CORAL_AUTH_PATH=$DBBASEPATH/XMLConfig
   export DATAPATH=$DBBASEPATH:$DATAPATH
   mkdir poolcond
   export DBREL_LOCATION=$ATLAS_DB_AREA/DBRelease
   cp $DBREL_LOCATION/current/poolcond/*.xml poolcond
   export DATAPATH=$PWD:$DATAPATH
   unset FRONTIER_SERVER

   # tell transform to skip file validation
   export G4ATLAS_SKIPFILEPEEK=1
else
   echo [$SECONDS] Setting up Frontier
   export http_proxy=http://10.236.1.194:3128
   export HTTP_PROXY=http://10.236.1.194:3128
   export FRONTIER_SERVER=$FRONTIER_SERVER\(proxyurl=$HTTP_PROXY\)
   export FRONTIER_LOG_LEVEL=info
fi

# setup for Generate_tf.py
if [ "{transformation}" = "Generate_tf.py" ]; then
   echo [$SECONDS] setting up LHAPDF
   export LHAPATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPATH
   export LHAPDF_DATA_PATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPDF_DATA_PATH
fi

echo [$SECONDS] PYTHON Version:       $(python --version)
echo [$SECONDS] PYTHONPATH:           $PYTHONPATH
echo [$SECONDS] LD_LIBRARY_PATH:      $LD_LIBRARY_PATH
env | sort > env_dump.txt

echo [$SECONDS] Starting transformation
{transformation} {jobPars}
EXIT_CODE=$?
echo [$SECONDS] Transform exited with return code: $EXIT_CODE
echo [$SECONDS] Exiting
exit $EXIT_CODE
'''

   def __init__(self,name,settings,args,defaults,rundir):
      super(AthenaApplication,self).__init__(name,settings,args,defaults,rundir)

      # ensure user passed allowed application
      if settings['command'] not in self.ATHENA_CMDS:
         raise Exception('Unsupported Athena Application: user specified %s which is not in %s',settings['command'],self.ATHENA_CMDS)

   def get_command(self):
      command = self.make_athena_script() + ' ' + self.rundir
      return command

   def make_athena_script(self):
      # set custom variables in the script
      script_content = self.athena_script_template.format(
         ATLAS_LOCAL_ROOT_BASE = self.defaults['atlas_local_root_base'],
         release = self.settings['release'],
         package = self.settings['package'],
         cmtConfig = self.settings['cmtConfig'],
         gcclocation = self.settings['gcclocation'],
         use_mp = self.settings['use_mp'],
         ATHENA_PROC_NUMBER = self.defaults['athena_proc_number'],
         transformation = self.settings['command'],
         jobPars = self.make_cmdline_arg_string())

      logger.debug('run script content: \n%s',script_content)

      # write script
      script_filename = self.settings['output_script_name']
      if self.rundir is not None:
         script_filename = os.path.join(self.rundir,script_filename)
      open(script_filename,'w').write(script_content)
      # set executable
      os.chmod(script_filename,stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)

      return script_filename


class LHEGun(Application):
   ''' run lhe_gun.py '''
   def __init__(self,name,settings,args,defaults,rundir):
      super(LHEGun,self).__init__(name,settings,args,defaults,rundir)

      self.output_filename = ('%05d_lhe' % MPI.COMM_WORLD.Get_rank()) + '.lhe'
      self.args['outfile-base'] = '%05d_lhe' % MPI.COMM_WORLD.Get_rank()
      self.args['numpy-seed'] = int(self.settings['numpy_seed_offset']) + MPI.COMM_WORLD.Get_rank()

   def get_output_filename(self):
      return self.output_filename


class GenerateTF(AthenaApplication):
   ''' run a Generate_tf.py job '''

   def __init__(self,name,settings,args,defaults,rundir):
      super(GenerateTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['firstEvent'] = str(int(self.settings['event_counter_offset']) + MPI.COMM_WORLD.Get_rank() * int(self.defaults['events_per_rank']))

      self.args['outputEVNTFile'] = '%05d_genEVNT.pool.root' % MPI.COMM_WORLD.Get_rank()
      # self.files_to_stage.append(self.args['outputEVNTFile'])

   def stage_files(self,stagedir):
      super(GenerateTF,self).stage_files(stagedir)
      srcfile = 'log.generate'
      dstfile = os.path.join(stagedir,('%05d_' % MPI.COMM_WORLD.Get_rank()) + srcfile)
      if self.rundir is not None:
         srcfile = os.path.join(self.rundir,srcfile)

      shutil.copyfile(srcfile,dstfile)

   def get_output_filename(self):
      return self.args['outputEVNTFile']

   def set_input_filename(self,input_filename):
      # set input file name
      self.args['preExec'] = self.args['preExec'].format(input_filename=input_filename)


class SimulateTF(AthenaApplication):
   ''' run Sim_tf.py job '''
   def __init__(self,name,settings,args,defaults,rundir):
      super(SimulateTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['outputHITSFile'] = '%05d_simHITS.pool.root' % MPI.COMM_WORLD.Get_rank()


   def stage_files(self,stagedir):
      super(SimulateTF,self).stage_files(stagedir)
      srcfile = 'log.EVNTtoHITS'
      dstfile = os.path.join(stagedir,('%05d_' % MPI.COMM_WORLD.Get_rank()) + srcfile)

      if self.rundir is not None:
         srcfile = os.path.join(self.rundir,srcfile)

      shutil.copyfile(srcfile,dstfile)

      athena_log_glob = 'athenaMP-workers*/*/AthenaMP.log'
      if self.rundir is not None:
         athena_log_glob = os.path.join(self.rundir,athena_log_glob)

      logs = glob.glob(athena_log_glob)

      # cat files
      tarfilename = '%05d_simulate_workers.tar' % MPI.COMM_WORLD.Get_rank()
      dstfile = os.path.join(stagedir,tarfilename)
      if self.rundir is not None:
         tarfilename = os.path.join(self.rundir,tarfilename)
      tf = tarfile.open(tarfilename,'w')
      for log in logs:
         tf.add(log)
      tf.close()
      # now copy tar to stagedir
      shutil.copyfile(tarfilename,dstfile)

   def get_output_filename(self):
      return self.args['outputHITSFile']

   def set_input_filename(self,input_filename):
      # set input file name
      self.args['inputEVNTFile'] = input_filename


class ReconstructTF(AthenaApplication):
   ''' run Sim_tf.py job '''
   def __init__(self,name,settings,args,defaults,rundir):
      super(ReconstructTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['outputRDOFile'] = '%05d_recoRDO.pool.root' % MPI.COMM_WORLD.Get_rank()
      self.args['outputESDFile'] = '%05d_recoESD.pool.root' % MPI.COMM_WORLD.Get_rank()

   def stage_files(self,stagedir):
      super(ReconstructTF,self).stage_files(stagedir)
      srcfiles = [self.args['outputRDOFile'],self.args['outputESDFile']]
      for srcfile in srcfiles:
         dstfile = os.path.join(stagedir,('%05d_' % MPI.COMM_WORLD.Get_rank()) + srcfile)
         
         if self.rundir is not None:
            srcfile = os.path.join(self.rundir,srcfile)

         shutil.copyfile(srcfile,dstfile)


   def get_output_filename(self):
      return None

   def get_output_rdo_filename(self):
      return self.args['outputRDOFile']

   def get_output_esd_filename(self):
      return self.args['outputESDFile']

   def set_input_filename(self,input_filename):
      # set input file name
      self.args['inputHITSFile'] = input_filename

   # def get_files_to_stage(self):
   #   return [self.args['outputESDFile'],self.args['outputRDOFile']]


def get_app(name,settings,args,defaults,rundir):

   if 'lhe' in settings['command']:
      return LHEGun(name,settings,args,defaults,rundir)
   elif 'Generate_tf.py' in settings['command']:
      return GenerateTF(name,settings,args,defaults,rundir)
   elif 'Sim_tf.py' in settings['command']:
      return SimulateTF(name,settings,args,defaults,rundir)
   elif 'Reco_tf.py' in settings['command']:
      return ReconstructTF(name,settings,args,defaults,rundir)

