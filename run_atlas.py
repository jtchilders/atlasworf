#!/usr/bin/env python
import os,sys,optparse,logging,shutil,socket,subprocess,time,glob,tarfile
if sys.version_info >= (3, 0, 0):
   import configparser as ConfigParser
else:
   import ConfigParser
import application as apps
from mpi4py import MPI
mpirank = MPI.COMM_WORLD.Get_rank()
mpisize = MPI.COMM_WORLD.Get_size()
logger = logging.getLogger(__name__)

workdir = os.getcwd()
stagedir = None

if sys.version_info > (2,7):
   xrange = range

def main():
   global workdir,stagedir
   ''' run the atlas workflow end-to-end '''
   logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:' + ('%05d' % mpirank) + ':%(name)s:%(message)s',filename='%05d_worfrank.log' % mpirank)

   parser = optparse.OptionParser(description='run the atlas workflow end-to-end')
   parser.add_option('-c','--config',dest='config',help='input config file in the ConfigParser format.')
   parser.add_option('-w','--workdir',dest='workdir',help='working directory for this job, a rank-wise subdirectory will also be made inside this directory in which sub-applications will run [default=%s' % workdir,default=workdir)
   # parser.add_option('-a','--appdir',dest='appdir',help='each application will be run')
   parser.add_option('-s','--stagedir',dest='stagedir',help='if set, output files with their stageout flag set will be moved from the workdir to this location.',default=None)
   parser.add_option('-e','--endtime',dest='endtime',help='time at which the job should end or else be killed, formatted in seconds since the epoch, in Cobalt just pass the COBALT_ENDTIME environment variable. setting to negative value disables this',default=-1,type='int')
   parser.add_option('--killtime',dest='killtime',help='determines when the job is killed. if endtime - time.time() < killtime then exit. value must be > 0',default=60,type='int')
   parser.add_option('--app-monitor-time',dest='appmontime',help='seconds between monitoring app run status',default=60,type='int')
   parser.add_option('-i','--input',dest='input',help='If specified, this comma separated list will be used as input to the first workflow step',default='')

   options,args = parser.parse_args()

   
   manditory_args = [
                     'config',
                     'workdir',
                     'endtime',
                     'killtime',
                     'appmontime',
                     'input',
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
   logger.info('input files:           %s',options.input)
   
   stagedir = options.stagedir
   # workdir  = options.workdir
   config,defaults = get_config(options)

   # startupdir = os.getcwd()

   # change to working directory
   os.chdir(options.workdir)
   logger.info('current working dir: %s',os.getcwd())

   rank_subdir = '%05d_worfrank' % mpirank
   logger.info('making directory %s',rank_subdir)
   workdir = os.path.join(options.workdir,rank_subdir)
   os.mkdir(rank_subdir)

   # logger.debug('config = %s',config)

   workflow = defaults['workflow'].split(',')
   logger.info('workflow: %s',workflow)
   if len(workflow) <= 0:
      raise Exception('workflow not specified correctly: %s' % workflow)
   logger.info('executing workflow: %s',defaults['workflow'])

   input_filenames = []
   outputs = {}
   if len(options.input) > 0:
      if 'root2numpy' in workflow[0]:
         # get input filenames
         input_filenames = glob.glob(options.input)

         # create run directory pre-emptively so I can place the input files
         rank_subdir_appdir = os.path.realpath(os.path.join(rank_subdir,workflow[0]))
         os.mkdir(rank_subdir_appdir)

         # looking for files starting with rank id
         rankstr = "%05d" % mpirank
         newfiles = []
         for file in input_filenames:
            if os.path.basename(file).startswith(rankstr):
               newfiles.append(file)

         logger.info('found input files: %s',newfiles)
         for file in newfiles:
            if 'hits' in file.lower():
               outputs['runrawdatahits'] = [file]
               os.system('cp %s %s/' % (file,rank_subdir_appdir))
            if 'calo' in file.lower():
               outputs['runrawdatacalo'] = [file]
               os.system('cp %s %s/' % (file,rank_subdir_appdir))

         logger.info('outputs: %s',outputs)
         if 'runrawdatahits' not in outputs:
            raise Exception(' no output file from runrawdatahits provided')
         if 'runrawdatacalo' not in outputs:
            raise Exception(' no output file from runrawdatacalo provided')
      elif 'rawdatahits' in workflow[0]:
         # inputs will be from reconstruction
         # that means a tarball with HITS & ESD inside

         # get the input list of tarballs
         tarballs = glob.glob(options.input)
         logger.info('found %s tarballs',len(tarballs))

         # create run directory pre-emptively so I can place the input files
         rank_subdir_appdir = os.path.realpath(os.path.join(rank_subdir,workflow[0]))
         os.mkdir(rank_subdir_appdir)

         if len(tarballs) == 1:
            tarfilename = tarballs[0]
         else:

            # find rankwise outputs and copy to the working directory
            filebase = "%05d_reco.pool.root.tgz" % mpirank
            tarfilename = ''
            for filename in tarballs:
               if filebase in filename:
                  tarfilename = filename
                  break
            if os.path.exists(tarfilename):
               logger.info('found input tarball: %s',tarfilename)
            else:
               logger.info('no tarball found, exiting')
               return

         # open tarball
         tfile = tarfile.open(tarfilename,'r|gz')
         filenames = tfile.getnames()
         strip_comps = len(filenames[0].split('/')) - 1
         os.system('cd %s;tar xf %s --strip-components %d' % (rank_subdir_appdir,tarfilename,strip_comps))

         esd_files = glob.glob(rank_subdir_appdir + '/*recoESD*root*')
         logger.info('found esd files: %d',len(esd_files))
         rdo_files = glob.glob(rank_subdir_appdir + '/*recoRDO*root*')
         logger.info('found rdo files: %d',len(rdo_files))

         input_filenames = (rdo_files,esd_files)
         outputs['reconstruct'] = input_filenames



   for app_name in workflow:
      settings = config[app_name + '_settings']
      args     = config[app_name + '_args']

      # directory in rank directory to run application
      # example: worfrank_00000/lhegun/
      rank_subdir_appdir = os.path.realpath(os.path.join(rank_subdir,app_name))
      logger.info('making directory %s',rank_subdir_appdir)
      if not os.path.exists(rank_subdir_appdir):
         os.mkdir(rank_subdir_appdir)

      logger.debug('app: %s',app_name)
      logger.debug('dir: %s',rank_subdir_appdir)
      logger.debug('settings: %s',settings)
      logger.debug('args: %s',args)
      if settings['enabled'] in ['true','True','1','yes']:
         logger.info('running %s',app_name)
         logger.info('command:      %s',settings['command'])

         app = apps.get_app(app_name,settings,args,defaults,rank_subdir_appdir)

         logger.info('input_filenames: %s',input_filenames)
         if 'runrawdatahits' in app_name:
            app.set_input(outputs['reconstruct'][0])
         elif 'runrawdatacalo' in app_name:
            app.set_input(outputs['reconstruct'][1])
         elif 'root2numpy' in app_name:
            app.set_input(outputs['runrawdatahits'][0],outputs['runrawdatacalo'][0])
            app.args['npz_filename'] = app.args['npz_filename'].format(rank_num=MPI.COMM_WORLD.Get_rank())
         else:
            if len(input_filenames) > 0:
               app.set_input(input_filenames)
         
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
            if options.stagedir is not None:
               from distutils.dir_util import copy_tree
               copy_tree(rank_subdir,options.stagedir)
            return -1
         # logger.info('stdout = %s\nstderr = %s',stdout,stderr)

         if options.stagedir is not None:
            app.stage_files(options.stagedir)

         input_filenames = app.get_output_filenames()
         outputs[app_name] = input_filenames
         logger.info('output files: %s',input_filenames)
         # Reco returns 2 output files RDO and ESDs
         if type(input_filenames) is tuple:
            rdo,esd = input_filenames
            for i in xrange(len(rdo)):
               rdo[i] = os.path.join(rank_subdir_appdir,rdo[i])
            for i in xrange(len(esd)):
               esd[i] = os.path.join(rank_subdir_appdir,esd[i])
            input_filenames = (rdo,esd)
         # Others only return 1 list
         elif type(input_filenames) is list:
            for i in xrange(len(input_filenames)):
               input_filenames[i] = os.path.join(rank_subdir_appdir,input_filenames[i])


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
   except Exception as e:
      print('received uncaught exception: %s' % str(e))
      import sys,traceback
      exc_type, exc_value, exc_traceback = sys.exc_info()
      print('\n'.join(x for x in traceback.format_exception(exc_type, exc_value,
                                          exc_traceback)))


      print('Copying out working directory and exiting')
      print('staging working directory "%s" to stage directory "%s"' % (workdir,stagedir))

      if workdir is not None and stagedir is not None:
         subprocess.call(['cp','-r',workdir,stagedir])
         print('done copying')
      else:
         print('copy cannot be performed')
