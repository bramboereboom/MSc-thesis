import agentpy as ap
import pandas as pd
from model import EtmEVsModel

profiles = pd.read_csv('../data/scenarios_1_sensitivity.csv').to_dict(orient='records')

exp = ap.Experiment(EtmEVsModel, profiles, record=True)
results = exp.run()

results.save(path='../data/experiment_sensitivity_results')