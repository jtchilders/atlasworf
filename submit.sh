#!/bin/bash
#COBALT -n 128
#COBALT -t 180
#COBALT -q default
#COBALT -A EnergyFEC_3

module load miniconda-3.6/conda-4.4.10

ATLASWORF=/home/parton/git/atlasworf
export PYTHONPATH=$ATLASWORF:$PYTHONPATH
aprun -n $COBALT_JOBSIZE -N 1 $ATLASWORF/run_atlas.py --config $ATLASWORF/atlasworf.cfg -w /tmp -s $PWD
