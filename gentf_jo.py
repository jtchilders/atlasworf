

evgenConfig.description = "bjet particle gun"
evgenConfig.contact = ['jchilders@anl.gov']
evgenConfig.keywords = ["bottom", "jets"]

#### include Common file



###include Pythia8_Base_Fragment.py
## Base config for Pythia8
from Pythia8_i.Pythia8_iConf import Pythia8_i
pythia8_i =  Pythia8_i("Pythia8")
genSeq += pythia8_i
evgenConfig.generators += ["Pythia8"]

genSeq.Pythia8.Commands += [
    "Main:timesAllowErrors = 500",
    "6:m0 = 172.5",
    "23:m0 = 91.1876",
    "23:mWidth = 2.4952",
    "24:m0 = 80.399",
    "24:mWidth = 2.085",
    "StandardModel:sin2thetaW = 0.23113",
    "StandardModel:sin2thetaWbar = 0.23146",
    "ParticleDecays:limitTau0 = on",
    "ParticleDecays:tau0Max = 10.0",
    "PartonLevel:ISR = off",
    "PartonLevel:MPI = off"]

#pythia8_i.CollisionEnergy = 6500
print('input_lhe_filename = %s' % input_lhe_filename)
pythia8_i.LHEFile = input_lhe_filename

from EvgenProdTools.EvgenProdToolsConf import TestHepMC
pythia8_i += TestHepMC()
pythia8_i.TestHepMC.EffFailThreshold = 0.5

evgenConfig.minevents = minevents

