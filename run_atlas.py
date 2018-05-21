#!/usr/bin/env python
import os,sys,optparse,logging
if sys.version_info >= (3, 0, 0):
   import configparser as ConfigParser
else:
   import ConfigParser
from application import Application,AthenaApplication
from mpi4py import MPI
logger = logging.getLogger(__name__)


def main():
   ''' run the atlas workflow end-to-end '''
   logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:' + ('%05d' % MPI.COMM_WORLD.Get_rank()) + ':%(name)s:%(message)s')

   parser = optparse.OptionParser(description='run the atlas workflow end-to-end')
   parser.add_option('-c','--config',dest='config',help='input config file in the ConfigParser format.')
   parser.add_option('-w','--workdir',dest='workdir',help='working directory for this job',default=os.getcwd())
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
   
   config = get_config(options)

   logger.info('config:          %s',options.config)
   logger.info('workdir:         %s',options.workdir)
   logger.info('stagedir:        %s',options.stagedir)

   # change to working directory
   os.chdir(options.workdir)
   logger.info('current working dir: %s',os.getcwd())
   
   logger.debug('config = %s',config)

   for app_name in config:
      items = config[app_name]

      enabled,binary,athena,args = parse_app_config(app_name,items)

      logger.debug('app: %s',app_name)
      logger.debug('binary: %s',binary)
      logger.debug('athena: %s',athena)
      logger.debug('args: %s',args)

      if enabled:
         logger.info('running %s',app_name)
         logger.info('    binary:      %s',binary)
         logger.info('    athena:      %s',athena)

         if athena:
            app = AthenaApplication(app_name,binary,args)
         else:
            app = Application(app_name,binary,args)
         
         logger.debug('   starting app %s ',app_name)
         app.start()
         
         stdout,stderr = app.block_and_get_output()
         logger.info('%s exited with code %s',app_name,app.get_returncode())
         logger.info('stdout = %s\nstderr = %s',stdout,stderr)





def parse_app_config(app,items):

   binary = ''
   enabled = False
   athena = False
   args = []
   app = app.lower()
   logger.debug('parsing app %s items %s',app,items)
   for key,value in items:
      logger.debug(' app: %s   key: %s   value: %s',app,key,value)
      if key.startswith(app):
         
         if ('%s_binary' % app) in key:
            logger.debug('binary: %s',value)
            binary = value
         elif ('%s_enabled' % app) in key:
            logger.debug('enabed: %s',value)
            enabled = 'true' == value
         elif ('%s_athena_app' % app) in key:
            logger.debug('athena: %s',value)
            athena = 'true' == value
         else:
            logger.error('app specific attribute not found, app="%s", key="%s", value="%s"',app,key,value)
      else:
         logger.debug('key: %s value: %s',key,value)
         args.append((key,value))

   return enabled,binary,athena,args


def get_config(options):

   config = {}
   if MPI.COMM_WORLD.Get_rank() == 0:
      configfile = ConfigParser.ConfigParser()
      logger.debug('reading config file: %s',options.config)
      configfile.read(options.config)
      
      for section in configfile.sections():
         config[section] = []
         for key,value in configfile.items(section):
            # exclude DEFAULT keys
            if key not in configfile['DEFAULT'].keys():
               config[section].append((key,value))
   logger.debug('at bcast %s',config)
   config = MPI.COMM_WORLD.bcast(config,root=0)
   logger.debug('after bcast %s',config)

   return config


   



if __name__ == "__main__":
   main()
