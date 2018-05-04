#!/usr/bin/env python
import os,sys,optparse,logging,ConfigParser
from application import Application,AthenaApplication
from mpi4py import MPI
logger = logging.getLogger(__name__)


def main():
   ''' run the atlas workflow end-to-end '''
   logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

   parser = optparse.OptionParser(description='run the atlas workflow end-to-end')
   parser.add_option('-c','--config',dest='config',help='input config file in the ConfigParser format.')
   parser.add_option('-w','--workdir',dest='workdir',help='working directory for this job',default=os.getcwd())
   parser.add_option('-s','--stagedir',dest='stagedir',help='if set, output files with their stageout flag set will be moved from the workdir to this location.',default=None)

   options,args = parser.parse_args()

   
   manditory_args = [
                     'config',
                     'workdir',
                     'stagedir',
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


   for app,items in config.iteritems():

      enabled,binary,athena,args = parse_app_config(app,items)

      if enabled:
         logger.info('running %s',app)
         logger.info('    binary:      %s',binary)
         logger.info('    athena:      %s',athena)

         if athena:
            app = AthenaApplication()
         else:
            app = Application(binary,args)

         app.start()





def parse_app_config(app,items):

   binary = ''
   enabled = False
   athena = False
   args = []

   for value,key in items:
      if value.startswith(app):
         if 'binary' in value:
            binary = key
         elif 'enabled' in value:
            enabled = 'true' == key
         elif 'athena_app' in value:
            athena = 'true' == key
         else:
            args.append((value,key))

   return enabled,binary,athena,args


def get_config(options):

   config = None
   if MPI.COMM_WORLD.Get_rank() == 0:
      configfile = ConfigParser.ConfigParser()
      configfile.readfp(open(options.config))

      for section in config.sections():
         config[section] = config.items(section)

   MPI.COMM_WORLD.bcast(config,root=0)

   return config


   



if __name__ == "__main__":
   main()
