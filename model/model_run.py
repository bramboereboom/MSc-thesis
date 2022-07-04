import json
import agentpy as ap
import pandas as pd
from model import EtmEVsModel
from timeit import default_timer as timer
import itertools


start = timer()
# load model parameters
with open('params.json') as file:
    params = json.load(file)
    #print(params)
    
def sensitivity_analysis():
    n_evs_change = [0.9,1,1.1]
    eprice_change = [1] #[0.9,1,1.1]
    repetitions = 1

    Scenario_values = []
    scenarios_counter = 0
    for combination in itertools.product(n_evs_change,eprice_change):
        print(combination)
        Scenario_values.append(combination)
        scenarios_counter += 1

    for i in range(scenarios_counter):
        for j in range(repetitions):
            print('Total runs: {}'.format(scenarios_counter*repetitions))
            print('Running scenario {} (repetition {}) of {} with n_evs_sens: {}, eprice_sens = {}, '.format(i+1,j+1,scenarios_counter,Scenario_values[i][0],Scenario_values[i][1]))
            params["n_evs_sensitivity"] = Scenario_values[i][0]
            params["electricity_price_sensitivity"] = Scenario_values[i][1]

            #print(params)

            model = EtmEVsModel(params)
            print('starting simulation')
            results = model.run()
            #results.variables.EtmEVsModel.plot()
            #results.variables.EtmEVsModel['average_battery_percentage'].plot()

            end = timer()

            print("---Run Completed---")
            print("Completed run in {} seconds".format(end - start))

            results_name = 'Price_disagg_16_scen{}_rep{}_evs{}_price{}.csv'.format(i+1,j+1,Scenario_values[i][0],Scenario_values[i][1])
            results.variables.EtmEVsModel.to_csv(results_name)

            print('Exporting to {}'.format(results_name))
            print('\n\n')
 
#sensitivity_analysis()

# run simulation
model = EtmEVsModel(params)
print('starting simulation')
results = model.run()
results.variables.EtmEVsModel.plot()
results.variables.EtmEVsModel['average_battery_percentage'].plot()

end = timer()

print("---Run Completed---")
print("Completed run in {} seconds".format(end - start))

#results.variables.EtmEVsModel.to_csv('sensitivity_results.csv')
results.variables.Municipality.loc['GM0363',:]\
    [['current_power_demand','current_vtg_capacity']].to_csv('between45-64_1_Mun.csv')