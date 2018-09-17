import subprocess,logging,stat,os,shutil,glob,tarfile,time
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

      self.stagedir     = None


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
      self.stagedir = stagedir
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


class LHEGun(Application):
   ''' run lhe_gun.py '''
   def __init__(self,name,settings,args,defaults,rundir):
      super(LHEGun,self).__init__(name,settings,args,defaults,rundir)

      self.output_filename = ('%05d_lhe' % MPI.COMM_WORLD.Get_rank()) + '.lhe'
      self.args['outfile-base'] = '%05d_lhe' % MPI.COMM_WORLD.Get_rank()
      self.args['numpy-seed'] = int(time.time()) + MPI.COMM_WORLD.Get_rank()

   def get_output_filenames(self):
      return [self.output_filename]


class AthenaApplication(Application):
   ''' run an athena-based application in a subprocess, setting up ALRB and release '''
   ATHENA_CMDS = ['athena','Generate_tf.py','Sim_tf.py','Reco_tf.py','python']

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

LOCAL_WORKAREA={workarea}
echo [$SECONDS] WORKAREA=$LOCAL_WORKAREA

source $AtlasSetup/scripts/asetup.sh --cmtconfig=$CMTCONFIG --makeflags=\"$MAKEFLAGS\" --cmtextratags=ATLAS,useDBRelease --workarea=$LOCAL_WORKAREA {gcclocation} $RELEASE,$PACKAGE,notest

{package_setup_script}

if [ "{command}" = "Sim_tf.py" ]; then
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
   echo [$SECONDS] Setting up database for local copy: ATLAS_DB_AREA=$ATLAS_DB_AREA
   DBBASEPATH=$ATLAS_DB_AREA/DBRelease/current
   export CORAL_DBLOOKUP_PATH=$DBBASEPATH/XMLConfig
   export CORAL_AUTH_PATH=$DBBASEPATH/XMLConfig
   export DATAPATH=$DBBASEPATH:$DATAPATH
   mkdir poolcond
   export DBREL_LOCATION=$ATLAS_DB_AREA/DBRelease
   cp $DBREL_LOCATION/current/poolcond/*.xml poolcond
   export DATAPATH=$PWD:$DATAPATH

   echo [$SECONDS] Setting up Frontier
   export http_proxy=http://10.236.1.194:3128
   export HTTP_PROXY=http://10.236.1.194:3128
   export FRONTIER_SERVER=$FRONTIER_SERVER\(proxyurl=$HTTP_PROXY\)
   export FRONTIER_LOG_LEVEL=info
fi

# setup for Generate_tf.py
if [ "{command}" = "Generate_tf.py" ]; then
   echo [$SECONDS] setting up LHAPDF
   export LHAPATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPATH
   export LHAPDF_DATA_PATH=/lus/theta-fs0/projects/AtlasADSP/machinelearning/bjet_prod/lhapdfsets/current:$LHAPDF_DATA_PATH
fi

echo [$SECONDS] PYTHON Version:       $(python --version)
echo [$SECONDS] PYTHONPATH:           $PYTHONPATH
echo [$SECONDS] LD_LIBRARY_PATH:      $LD_LIBRARY_PATH
env | sort > env_dump.txt

echo [$SECONDS] Starting command
{command} {jobPars}
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

      if 'job_opts' not in self.settings:
         self.settings['job_opts'] = ''
         self.output_filename = '%05d_athena_output.root' % MPI.COMM_WORLD.Get_rank()
      else:
         self.output_filename = '%05d_%s_output.root' % (MPI.COMM_WORLD.Get_rank(),os.path.basename(self.settings['job_opts']).replace('.py',''))

      if 'workarea' not in self.settings:
         self.settings['workarea'] = 'here'

      if 'use_mp' not in self.settings:
         self.settings['use_mp'] = False

      self.input_filelist = []
      # place holder for Transforms if they have command line input file strings
      self.input_file_arg = ''

      if 'package_setup_script' not in self.settings:
         self.settings['package_setup_script'] = ''
   
   def get_command(self):
      command = self.make_athena_script() + ' ' + self.rundir
      return command

   def make_athena_script(self):

      # parse input files
      if len(self.input_file_arg) > 0 and len(self.input_filelist) > 0:
         self.args[self.input_file_arg] = ','.join(x for x in self.input_filelist)

      # get cmd line args
      jobPars = self.make_cmdline_arg_string()
      if len(self.settings['job_opts']) > 0:
         jobPars += ' ' + self.settings['job_opts']

      # set custom variables in the script
      script_content = self.athena_script_template.format(
         ATLAS_LOCAL_ROOT_BASE = self.defaults['atlas_local_root_base'],
         release = self.settings['release'],
         package = self.settings['package'],
         cmtConfig = self.settings['cmtConfig'],
         gcclocation = self.settings['gcclocation'],
         use_mp = self.settings['use_mp'],
         ATHENA_PROC_NUMBER = self.defaults['athena_proc_number'],
         command = self.settings['command'],
         jobPars = jobPars,
         package_setup_script = self.settings['package_setup_script'],
         workarea = self.settings['workarea'])

      logger.debug('run script content: \n%s',script_content)

      # write script
      script_filename = self.settings['output_script_name']
      if self.rundir is not None:
         script_filename = os.path.join(self.rundir,script_filename)
      open(script_filename,'w').write(script_content)
      # set executable
      os.chmod(script_filename,stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)

      return script_filename

   def set_input(self,input_filelist):
      self.input_filelist = input_filelist

      # if command set, look for input_filelist
      if 'command' in self.args:
         try:
            self.args['command'] = self.args['command'].format(input_filelist=str(self.input_filelist),output_filename=self.output_filename)
         except Exception:
            logger.exception('athena command %s does not contain "{{input_filelist}}" or "{{output_filename}}" format string so not parsing it.',self.args['command'])

   def stage_files(self,stagedir):
      super(AthenaApplication,self).stage_files(stagedir)
      if len(self.output_filename) > 0:
         srcfile = self.rundir + '/' + self.output_filename
         dstfile = self.stagedir + '/' + os.path.basename(self.output_filename)
         shutil.copyfile(srcfile,dstfile)

   def get_output_filenames(self):
      return [self.output_filename]


class AtlasPython(AthenaApplication):
   ''' run a python script inside an atlas environment '''

   def __init__(self,name,settings,args,defaults,rundir):
      super(AtlasPython,self).__init__(name,settings,args,defaults,rundir)
      self.output_filename = ''
      
   def make_athena_script(self):

      # get cmd line args
      jobPars = self.make_cmdline_arg_string()
      if len(self.settings['job_opts']) > 0:
         jobPars = self.settings['job_opts'] + ' ' + jobPars

      # set custom variables in the script
      script_content = self.athena_script_template.format(
         ATLAS_LOCAL_ROOT_BASE = self.defaults['atlas_local_root_base'],
         release = self.settings['release'],
         package = self.settings['package'],
         cmtConfig = self.settings['cmtConfig'],
         gcclocation = self.settings['gcclocation'],
         use_mp = 'false',
         ATHENA_PROC_NUMBER = self.defaults['athena_proc_number'],
         command = self.settings['command'],
         jobPars = jobPars,
         package_setup_script = self.settings['package_setup_script'],
         workarea = self.settings['workarea'])

      logger.debug('run script content: \n%s',script_content)

      # write script
      script_filename = self.settings['output_script_name']
      if self.rundir is not None:
         script_filename = os.path.join(self.rundir,script_filename)
      open(script_filename,'w').write(script_content)
      # set executable
      os.chmod(script_filename,stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)

      return script_filename

   def set_input(self,hits,calo):
      self.args['inputhits'] = hits
      self.args['inputcalo'] = calo

   def get_output_filenames(self):
      return glob.glob(os.path.join(self.rundir,self.args['output_path'] + '/*'))

   def stage_files(self,stagedir):
      super(AtlasPython,self).stage_files(stagedir)
      
      # copy output files
      for filename in glob.glob(os.path.join(self.rundir,self.args['output_path'] + '/*')):
         shutil.move(filename,stagedir + '/' + os.path.basename(filename))



class GenerateTF(AthenaApplication):
   ''' run a Generate_tf.py job '''

   def __init__(self,name,settings,args,defaults,rundir):
      super(GenerateTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['firstEvent'] = str(int(self.settings['event_counter_offset']) + MPI.COMM_WORLD.Get_rank() * int(self.defaults['events_per_rank']))
      
      # copy tarball to working path
      shutil.copyfile(self.settings['evgenopts_path'],rundir + '/' + os.path.basename(self.settings['evgenopts_path']))

      self.args['outputEVNTFile'] = '%05d_genEVNT.pool.root' % MPI.COMM_WORLD.Get_rank()
      self.output_filename = ''
      # self.files_to_stage.append(self.args['outputEVNTFile'])


   def stage_files(self,stagedir):
      super(GenerateTF,self).stage_files(stagedir)
      srcfile = 'log.generate'
      dstfile = os.path.join(stagedir,('%05d_' % MPI.COMM_WORLD.Get_rank()) + srcfile)
      if self.rundir is not None:
         srcfile = os.path.join(self.rundir,srcfile)

      shutil.copyfile(srcfile,dstfile)

   def get_output_filenames(self):
      return [self.args['outputEVNTFile']]

   def set_input(self,input_filename):
      # set input file name
      if type(input_filename) is list:
         if len(input_filename) == 1:
            input_filename = input_filename[0]
         else:
            raise Exception('passed many input files to Generate_tf but should only be one file.')
      self.args['preExec'] = self.args['preExec'].format(input_filename=input_filename)


class SimulateTF(AthenaApplication):
   ''' run Sim_tf.py job '''
   def __init__(self,name,settings,args,defaults,rundir):
      super(SimulateTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['outputHITSFile'] = '%05d_simHITS.pool.root' % MPI.COMM_WORLD.Get_rank()
      self.output_filename = ''

      # set input arg name
      self.input_file_arg = 'inputEVNTFile'

      # set arg for input
      self.args[self.input_file_arg] = ''


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

   def get_output_filenames(self):
      return [self.args['outputHITSFile']]



class ReconstructTF(AthenaApplication):
   ''' run Sim_tf.py job '''
   def __init__(self,name,settings,args,defaults,rundir):
      super(ReconstructTF,self).__init__(name,settings,args,defaults,rundir)

      # determine event number starting counter
      self.args['outputRDOFile'] = '%05d_recoRDO.pool.root' % MPI.COMM_WORLD.Get_rank()
      self.args['outputESDFile'] = '%05d_recoESD.pool.root' % MPI.COMM_WORLD.Get_rank()
      self.output_filename = ''

      self.tarballname = '%05d_reco.pool.root.tgz' % MPI.COMM_WORLD.Get_rank()

      # set input arg name
      self.input_file_arg = 'inputHITSFile'

   def stage_files(self,stagedir):
      super(ReconstructTF,self).stage_files(stagedir)
      
      srcfiles = [self.args['outputRDOFile'],self.args['outputESDFile']]
      # if this setting is set, the merge steps will be skipped so
      # we must copy out one output file per AthenaMP worker
      if 'athenaMPMergeTargetSize' in self.args:
         logger.info('handling non-merged outputs')
         
         # glob all the RDO files
         glob_str = self.rundir + '/athenaMP-workers-HITtoRDO-h2r/worker_*/' + self.args['outputRDOFile'] + '_*'
         rdofiles = glob.glob(glob_str)
         # glob all the ESD files
         glob_str = self.rundir + '/athenaMP-workers-RAWtoESD-r2e/worker_*/' + self.args['outputESDFile'] + '_*'
         esdfiles = glob.glob(glob_str)
         # what I've seen is that all the filenames are the same down inside the
         # worker directories so we cannot just copy them to the stage out directory
         # we have to rename them to include the worker number for uniqueness
         # we'll rename them in the run directory because if this is a node-local SSD
         # or RAM-disk, performance will be better.
         logger.info('found %s source files',len(srcfiles))
         tarball_filename = os.path.join(stagedir,self.tarballname)
         tf = tarfile.open(tarball_filename,'w:gz')

         new_rdofiles = []
         for filename in rdofiles:
            newfn = os.path.basename(filename) + '.' + self.get_worker_num(filename)
            newfn = os.path.dirname(filename) + '/' + newfn

            logger.debug('renaming %100s to %100s',filename,newfn)
            os.rename(filename,newfn)

            tf.add(newfn)
            new_rdofiles.append(newfn)
         
         new_esdfiles = []
         for filename in esdfiles:
            newfn = os.path.basename(filename) + '.' + self.get_worker_num(filename)
            newfn = os.path.dirname(filename) + '/' + newfn

            logger.debug('renaming %100s to %100s',filename,newfn)
            os.rename(filename,newfn)

            tf.add(newfn)
            new_esdfiles.append(newfn)

         self.args['outputRDOFile'] = new_rdofiles
         self.args['outputESDFile'] = new_esdfiles

         tf.close()

         srcfiles = []
         logger.info('%s tarball created',tarball_filename)

      logger.info('staging %s reco output files',len(srcfiles))
      for srcfile in srcfiles:
         dstfile = os.path.join(stagedir,('%05d_' % MPI.COMM_WORLD.Get_rank()) + os.path.basename(srcfile))
         
         if self.rundir is not None:
            srcfile = os.path.join(self.rundir,srcfile)

         shutil.copyfile(srcfile,dstfile)

   def get_output_filenames(self):
      # glob all the RDO files
      
      return (self.args['outputRDOFile'],self.args['outputESDFile'])

   def get_output_rdo_filename(self):
      if self.stagedir is None:
         return self.args['outputRDOFile']
      else:
         outfiles = []
         glob_str = self.stagedir + '/athenaMP-workers-HITtoRDO-h2r/worker_*/' + self.args['outputRDOFile'] + '_*'
         outfiles += glob.glob(glob_str)
         return outfiles

   def get_output_esd_filename(self):
      if self.stagedir is None:
         return self.args['outputESDFile']
      else:
         outfiles = []
         # glob all the ESD files
         glob_str = self.stagedir + '/athenaMP-workers-RAWtoESD-r2e/worker_*/' + self.args['outputESDFile'] + '_*'
         outfiles += glob.glob(glob_str)
         return outfiles

   def get_worker_num(self,filename):
      start = filename.find('worker_') + len('worker_')
      end = filename.find('/',start)
      return ('%05d' % int(filename[start:end]))


def get_app(name,settings,args,defaults,rundir):

   if 'lhe' in settings['command']:
      return LHEGun(name,settings,args,defaults,rundir)
   elif 'Generate_tf.py' in settings['command']:
      return GenerateTF(name,settings,args,defaults,rundir)
   elif 'Sim_tf.py' in settings['command']:
      return SimulateTF(name,settings,args,defaults,rundir)
   elif 'Reco_tf.py' in settings['command']:
      return ReconstructTF(name,settings,args,defaults,rundir)
   elif 'athena' in settings['command']:
      return AthenaApplication(name,settings,args,defaults,rundir)
   elif 'python' in settings['command']:
      return AtlasPython(name,settings,args,defaults,rundir)
   else:
      raise Exception('app %s not found' % name)

