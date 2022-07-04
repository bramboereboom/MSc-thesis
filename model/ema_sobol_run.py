from ema_workbench import (MultiprocessingEvaluator,SequentialEvaluator, ema_logging, save_results, load_results)
from SALib.analyze import sobol
from ema_workbench.em_framework.evaluators import SOBOL
from ema_workbench.em_framework.salib_samplers import get_SALib_problem
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from ema_problem_definitions import ema_problem

ema_logging.LOG_FORMAT = '%(message)s'
ema_logging.log_to_stderr(ema_logging.INFO)

# import problem definition
model = ema_problem(2)

with MultiprocessingEvaluator(model) as evaluator:
    experiment_SOBOL, outcomes_SOBOL = evaluator.perform_experiments(scenarios = 650, uncertainty_sampling=SOBOL)

sobol_results = save_results((experiment_SOBOL, outcomes_SOBOL), '../data/ema/sobol_results.tar.gz')
