#!/usr/bin/env python
import os,sys,optparse,logging
if sys.version_info >= (3, 0, 0):
   import configparser as ConfigParser
else:
   import ConfigParser
import application as apps
from mpi4py import MPI
mpirank = MPI.COMM_WORLD.Get_rank()
mpisize = MPI.COMM_WORLD.Get_size()
logger = logging.getLogger(__name__)


def main():
   ''' run the atlas workflow end-to-end '''
   logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:' + ('%05d' % mpirank) + ':%(name)s:%(message)s',filename='worfrank_%05d.log' % mpirank)

   parser = optparse.OptionParser(description='run the atlas workflow end-to-end')
   parser.add_option('-c','--config',dest='config',help='input config file in the ConfigParser format.')
   parser.add_option('-w','--workdir',dest='workdir',help='working directory for this job, a rank-wise subdirectory will also be made inside this directory in which sub-applications will run',default=os.getcwd())
   parser.add_option('-s','--stagedir',dest='stagedir',help='if set, output files with their stageout flag set will be moved from the workdir to this location.',default=None)

   options,args = parser.parse_args()

   
   manditory_args = [
                     'config',
                     'workdir',
                  ]

   for man in manditory_args:
      if man not in options.__dict__ or options.__dict__[man] is None:
         logger.error('Must specify option: ' + man)
         parser.print_help()
         sys.exit(-1)
   
   logger.info('config:          %s',options.config)
   logger.info('workdir:         %s',options.workdir)
   logger.info('stagedir:        %s',options.stagedir)
   
   config,defaults = get_config(options)


   # change to working directory
   os.chdir(options.workdir)
   logger.info('current working dir: %s',os.getcwd())

   if mpirank == 0:
      for i in range(mpisize):
         os.mkdir('worfrank_%05d' % mpirank)
   MPI.COMM_WORLD.Barrier()

   rank_subdir = 'worfrank_%05d' % mpirank
   
   logger.debug('config = %s',config)

   logger.info('executing workflow: %s',defaults['workflow'])

   for app_name in defaults['workflow'].split(','):
      settings = config[app_name + '_settings']
      args     = config[app_name + '_args']

      # directory in rank directory to run application
      # example: worfrank_00000/lhegun/
      rank_subdir_appdir = os.path.join(rank_subdir,app_name)
      os.mkdir(rank_subdir_appdir)

      logger.debug('app: %s',app_name)
      logger.debug('settings: %s',settings)
      logger.debug('args: %s',args)
      if settings['enabled'] in ['true','True','1','yes']:
         logger.info('running %s',app_name)
         logger.info('    command:      %s',settings['command'])
         logger.info('    athena_app:   %s',settings['athena_app'])

         if settings['command'] in apps.AthenaApplication.ATHENA_CMDS:
            app = apps.get_athena_app(app_name,settings,args,defaults,rank_subdir_appdir)
         else:
            app = apps.Application(app_name,settings,args,defaults)
         
         logger.debug('   starting app %s ',app_name)
         #app.start()
         
         #stdout,stderr = app.block_and_get_output()
         #logger.info('%s exited with code %s',app_name,app.get_returncode())
         #logger.info('stdout = %s\nstderr = %s',stdout,stderr)


def get_config(options):

   config = {}
   default = {}
   if MPI.COMM_WORLD.Get_rank() == 0:
      configfile = ConfigParser.ConfigParser()
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
   logger.debug('at bcast %s',config)
   config = MPI.COMM_WORLD.bcast(config,root=0)
   default = MPI.COMM_WORLD.bcast(default,root=0)
   logger.debug('after bcast %s',config)

   return config,default


   



if __name__ == "__main__":
   main()
