#! /usr/bin/env python

"""
Generate dummy LHE events designed to be showered and make one visible jet in the detector.
"""
import argparse,numpy,logging
logger = logging.getLogger(__name__)


def main():
   logging.basicConfig(level=logging.INFO)
   ap = argparse.ArgumentParser(description=__doc__)
   ap.add_argument("-n",'--numevents', dest="nevts", default=1000, type=int, help="number of events to generate")
   ap.add_argument('-N','--numfiles',dest='nfiles',default=1,type=int,help='number of files to produce, each with nevts inside.')
   ap.add_argument("-o",'--outfile-base', dest="output_base", default="events", help="base filename for output event files")
   ap.add_argument('-e','--ecm',dest='ecm',type=float,default=13000.,help='Center of Mass energy: Units are GeV')
   ap.add_argument('-a','--eta-max',dest='eta_max',type=float,default=1.5,help='particles are generated within -eta_max and eta_max.')
   ap.add_argument('-b','--min-e',dest='min_e',type=float,default=100.,help='particles are generated within energy min_e and max_e: Units are GeV')
   ap.add_argument('-c','--max-e',dest='max_e',type=float,default=1000.,help='particles are generated within energy min_e and max_e: Units are GeV')
   ap.add_argument('-r','--numpy-seed',dest='numpy_seed',type=int,default=0,help='random number seed to start with')
   args = ap.parse_args()


   logger.info('nevts:        %s',args.nevts)
   logger.info('nfiles:       %s',args.nfiles)
   logger.info('output_base:  %s',args.output_base)
   logger.info('ecm:          %s',args.ecm)
   logger.info('eta_max:      %s',args.eta_max)
   logger.info('min_e:        %s',args.min_e)
   logger.info('max_e:        %s',args.max_e)
   logger.info('numpy_seed:   %s',args.numpy_seed)
   
   numpy.random.seed(args.numpy_seed)

   head = """\
<LesHouchesEvents version="1.0">
   <!-- File generated with lhegun by andy.buckley@cern.ch -->
   <init>
    2212     2212  {energy:.8E}  {energy:.8E}     -1     -1     -1     -1     3      1
    1E+09  0.0  0.0  12345
   </init>
""".format(energy=args.ecm/2.)

   for i in range(args.nfiles):
      # make a filenames
      if args.nfiles > 1:
         outputfilename = args.output_base + ('_%08d.lhe' % i)
      else:
         outputfilename = args.output_base + '.lhe'

      with open(outputfilename, "w") as f:
         f.write(head)

         import random, math
         for i in range(args.nevts):
            ## Set up for flat sampling of eta and
            eta = numpy.random.uniform(-args.eta_max, args.eta_max)
            phi = numpy.random.uniform(0, 2*numpy.pi)
            energy = numpy.random.uniform(args.min_e, args.max_e)
            ## Translate coords to x,y,z,t
            theta = 2*numpy.arctan(numpy.exp(-eta))
            pz = energy * numpy.cos(theta)
            pperp = energy * numpy.sin(theta)
            px = pperp * numpy.cos(phi)
            py = pperp * numpy.sin(phi)
            ## Assemble convenience tuples
            mom = (px, py, pz, energy)
            amom = (-px, -py, -pz, -energy)
            s = """\
   <event>
     4  12345  1.00E+00  {p[3]:.8E} -1.00E+00  -1.00E-01
     21    -1     0     0   511   514  0.00E+00       0.00E+00  {p[3]:.8E}  {p[3]:.8E}  0.00E+00  0.00E+00  9.00E+00
     5    -1      0     0   514   0    0.00E+00       0.00E+00  {q[3]:.8E}  {p[3]:.8E}  0.00E+00  0.00E+00  9.00E+00
     5     1      1     2   511   0    {p[0]:.8E}  {p[1]:.8E}  {p[2]:.8E}  {p[3]:.8E}  0.00E+00  0.00E+00  9.00E+00
     12     1     1     2   0     0    {q[0]:.8E}  {q[1]:.8E}  {q[2]:.8E}  {p[3]:.8E}  0.00E+00  0.00E+00  9.00E+00
   </event>""".format(p=mom, q=amom)
            f.write(s + "\n")
         f.write("</LesHouchesEvents>\n")


if __name__ == '__main__':
   main()

