#!/usr/bin/env python
import os,sys,optparse,logging,shutil,socket,subprocess,time
if sys.version_info >= (3, 0, 0):
   import configparser as ConfigParser
else:
   import ConfigParser
import application as apps
from mpi4py import MPI
mpirank = MPI.COMM_WORLD.Get_rank()
mpisize = MPI.COMM_WORLD.Get_size()
logger = logging.getLogger(__name__)

workdir = None
stagedir = None


def main():
   global workdir,stagedir
   ''' run the atlas workflow end-to-end '''
   logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:' + ('%05d' % mpirank) + ':%(name)s:%(message)s',filename='%05d_worfrank.log' % mpirank)

   parser = optparse.OptionParser(description='run the atlas workflow end-to-end')
   parser.add_option('-c','--config',dest='config',help='input config file in the ConfigParser format.')
   parser.add_option('-w','--workdir',dest='workdir',help='working directory for this job, a rank-wise subdirectory will also be made inside this directory in which sub-applications will run',default=os.getcwd())
   # parser.add_option('-a','--appdir',dest='appdir',help='each application will be run')
   parser.add_option('-s','--stagedir',dest='stagedir',help='if set, output files with their stageout flag set will be moved from the workdir to this location.',default=None)
   parser.add_option('-e','--endtime',dest='endtime',help='time at which the job should end or else be killed, formatted in seconds since the epoch, in Cobalt just pass the COBALT_ENDTIME environment variable. setting to negative value disables this',default=-1,type='int')
   parser.add_option('--killtime',dest='killtime',help='determines when the job is killed. if endtime - time.time() < killtime then exit. value must be > 0',default=60,type='int')
   parser.add_option('--app-monitor-time',dest='appmontime',help='seconds between monitoring app run status',default=60,type='int')

   options,args = parser.parse_args()

   
   manditory_args = [
                     'config',
                     'workdir',
                     'endtime',
                     'killtime',
                     'appmontime',
                  ]

   for man in manditory_args:
      if man not in options.__dict__ or options.__dict__[man] is None:
         logger.error('Must specify option: ' + man)
         parser.print_help()
         sys.exit(-1)
   
   logger.info('config:                %s',options.config)
   logger.info('workdir:               %s',options.workdir)
   logger.info('stagedir:              %s',options.stagedir)
   logger.info('endtime:               %s',options.endtime)
   logger.info('killtime:              %s',options.killtime)
   logger.info('running on hostname:   %s',socket.gethostname())
   
   stagedir = options.stagedir
   workdir  = options.workdir
   config,defaults = get_config(options)

   # startupdir = os.getcwd()

   # change to working directory
   os.chdir(options.workdir)
   logger.info('current working dir: %s',os.getcwd())

   rank_subdir = '%05d_worfrank' % mpirank
   logger.info('making directory %s',rank_subdir)
   workdir = os.path.join(workdir,rank_subdir)
   os.mkdir(rank_subdir)

   # logger.debug('config = %s',config)

   logger.info('executing workflow: %s',defaults['workflow'])

   input_filename = None

   for app_name in defaults['workflow'].split(','):
      settings = config[app_name + '_settings']
      args     = config[app_name + '_args']

      # directory in rank directory to run application
      # example: worfrank_00000/lhegun/
      rank_subdir_appdir = os.path.realpath(os.path.join(rank_subdir,app_name))
      logger.info('making directory %s',rank_subdir_appdir)
      os.mkdir(rank_subdir_appdir)

      logger.debug('app: %s',app_name)
      logger.debug('dir: %s',rank_subdir_appdir)
      logger.debug('settings: %s',settings)
      logger.debug('args: %s',args)
      if settings['enabled'] in ['true','True','1','yes']:
         logger.info('running %s',app_name)
         logger.info('    command:      %s',settings['command'])
         logger.info('    athena_app:   %s',settings['athena_app'])

         app = apps.get_app(app_name,settings,args,defaults,rank_subdir_appdir)

         if input_filename is not None:
            app.set_input_filename(input_filename)
         
         logger.debug('   starting app %s ',app_name)
         app.start()
         
         logger.info('process is running...')
         while(app.process_running()):
            if options.endtime > 0 and options.killtime > 0 and options.endtime - time.time() < options.killtime:
               logger.info('reached kill time for app.')
               app.kill_process()
               raise Exception('killtime reached')

            time.sleep(options.appmontime)

         logger.info('%s exited with code %s',app_name,app.get_returncode())
         if app.get_returncode() != 0:
            shutil.copytree(rank_subdir,options.workdir)
            return -1
         # logger.info('stdout = %s\nstderr = %s',stdout,stderr)

         input_filename = app.get_output_filename()
         if input_filename is not None:
            input_filename = os.path.join(rank_subdir_appdir,input_filename)

         if options.stagedir is not None:
            app.stage_files(options.stagedir)


   return 0


def get_config(options):

   config = {}
   default = {}
   if MPI.COMM_WORLD.Get_rank() == 0:
      configfile = ConfigParser.ConfigParser()
      # make config options case sensitive (insensitive by default)
      configfile.optionxform = str
      logger.debug('reading config file: %s',options.config)
      with open(options.config) as fp:
         configfile.readfp(fp)
         for section in configfile.sections():
            config[section] = {}
            for key,value in configfile.items(section):
               # exclude DEFAULT keys
               if key not in configfile.defaults().keys():
                  config[section][key] = value
               else:
                  default[key] = value
   # logger.debug('at bcast %s',config)
   config = MPI.COMM_WORLD.bcast(config,root=0)
   default = MPI.COMM_WORLD.bcast(default,root=0)
   # logger.debug('after bcast %s',config)

   return config,default


   



if __name__ == "__main__":
   try:
      sys.exit(main())
   except Exception:
      logger.exception('received uncaught exception. Copying out working directory and exiting')
      logger.info('staging working directory "%s" to stage directory "%s"',workdir,stagedir)
      if workdir is not None and stagedir is not None:
         subprocess.call(['cp','-r',workdir,stagedir])
         logger.info('done copying')
      else:
         logger.info('copy cannot be performed')
