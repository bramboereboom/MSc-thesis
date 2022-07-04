import agentpy as ap
import pandas as pd
import networkx as nx
from components import *
from OD_matrix import (generate_OD)
import math
import logging
import numpy as np
from timeit import default_timer as timer

"""
Main model block
"""

def check_not_none(value):
    """check if value is not None and not np.nan"""

    if value is not None and not np.isnan(value):
        return True
    else:
        return False

class EtmEVsModel(ap.Model):
    """Main model that simulates electric vehicles."""

    def setup(self):

        # start timer for log
        start = timer()
        # configure model log
        logging.basicConfig(filename='model.log', filemode='w',
                            format='%(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
        # model properties
        self.price_history = [[0] for i in range(96)]
        self.ma_price_history = []
        self.Electricity_price = pd.read_csv(
            #'../data/price_disagg_16.csv') * self.p.electricity_price_sensitivity
            '../data/prizes_electricity_365_days_per_15_minutes.csv') * self.p.electricity_price_sensitivity######################################
        self.average_battery_percentage = 100
        self.total_current_power_demand = None
        self.total_VTG_capacity = None
        self.mean_charging = None
        self.list_average_battery_percentage = []
        self.list_total_current_power_demand = []
        self.list_total_VTG_capacity = []
        self.list_mean_charging = []

        # generate the manicipalities according to data prep file
        self.OD = generate_OD(self.p.g, self.p.m)
        self.municipalities_data = pd.read_csv(
            '../data/gemeenten.csv').set_index('GM_CODE')

        # generate all manucipality agents
        self.municipalities = ap.AgentList(self, 0, Municipality)
        

        #######!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #import disagg dataset for EV values
        self.disagg_data = pd.read_csv('../data/population_disagg.csv').set_index('GM_CODE')
        print('first pop data values : ')
        for i in range(5):
            print(self.disagg_data['between_45_64'][i])
        #######!!!!!!!!!!!!!!!!!!!!!!II!!!!!!!!!!!!!!
        #                            II
        #                            V
        # calculate percentage evs compared to total residents
        ############################################################added sensitivity
        percentage_ev = (self.p.n_evs) / \
            sum(self.disagg_data['between_45_64'])
        print(percentage_ev,sum(self.disagg_data['between_45_64']))

        # give the right properties to every municipality according to data prep file

        


        for index, (key, value) in enumerate(self.OD.items()):
            
            new_mun = Municipality(self)
            new_mun.id = key
            #print(new_mun.id)
            new_mun.name = self.municipalities_data.loc[key, 'GM_NAAM']
            new_mun.OD = value

            #new_mun.inhabitants = self.municipalities_data.loc[key, 'AANT_INW']
            new_mun.inhabitants = self.disagg_data.loc[key, 'between_45_64']
            
            ######disaggregate original
            new_mun.number_EVs = round(
                percentage_ev * new_mun.inhabitants * self.p.n_evs_sensitivity)

            ######disaggregate
            #new_mun.number_EVs = self.p.n_evs * self.disagg_data.loc[key,'EV_spatial_distribution_mean']
            


            self.municipalities.append(new_mun)
        self.weekend = False
        self.t_weekend = 480

        # correct rounding in number evs due to percentage inaccuracies
        number_evs = sum(self.municipalities.number_EVs)
        print('number_evs: {}'.format(number_evs))

        #if number_evs > self.p.n_evs:
        #    n = number_evs - self.p.n_evs
        #    for i in range(n):
        #        self.municipalities.random().number_EVs -= 1
        #elif number_evs < self.p.n_evs:
        #    n = self.p.n_evs - number_evs
        #    for i in range(n):
        #        self.municipalities.random().number_EVs += 1
        #self.number_evs = sum(self.municipalities.number_EVs)

        if number_evs > (self.p.n_evs * self.p.n_evs_sensitivity):
            n = number_evs - math.ceil(self.p.n_evs * self.p.n_evs_sensitivity)
            for i in range(n):
                self.municipalities.random().number_EVs -= 1
        elif number_evs < (self.p.n_evs * self.p.n_evs_sensitivity):
            n = math.ceil(self.p.n_evs * self.p.n_evs_sensitivity) - number_evs
            for i in range(n):
                self.municipalities.random().number_EVs += 1
        self.number_evs = sum(self.municipalities.number_EVs)

        print('number_evs after adjustment: {}'.format(number_evs))

        # generate EV's
        # generate EV agentlist
        self.EVs = ap.AgentList(self, 0, EV)
        index = 0  # keeps track of the EV index
        # give the right properties to every EV according to the data prep file
        for mun in self.municipalities:
            mun_start = timer()
            if mun.number_EVs > 0:
                # for experimentation reasons set seed used by pandas \
                # to random value if no parameter for model seed is provided
                if 'seed' not in self.p:
                    pandas_seed = self.random.randint(0, 1000000)
                else:
                    pandas_seed = self.p.seed
                sampled_dest = mun.OD.sample(
                    mun.number_EVs, weights='p_flow', random_state=pandas_seed, replace=True)
            for ev in range(mun.number_EVs):
                # generate ev and add to agentlist
                new_ev = EV(self)
                # set home location
                new_ev.home_location = mun.name
                new_ev.home_id = mun.id
                # pick destination, higher p_flow gives higher chance to be picked
                mapped_dest = sampled_dest.iloc[[ev]]
                new_ev.work_location_id = mapped_dest['destination_id'].iloc[0]
                new_ev.work_location_name = self.municipalities_data.loc[
                    new_ev.work_location_id, 'GM_NAAM']
                new_ev.commute_distance = mapped_dest['distance'].iloc[0]
                # travel times in 15 minutes units
                new_ev.travel_time = max(1, round(
                    new_ev.commute_distance/self.p.average_driving_speed))  # give at least 1 time step
                # give a enery required for trip memory
                new_ev.energy_required = new_ev.energy_rate * \
                    new_ev.commute_distance
                # check if maximum battery volume in model is enough to reach destination, if not, give the value needed to reach destination
                if self.model.p.h_vol < new_ev.energy_required:
                    new_ev.battery_volume = new_ev.energy_required
                    logging.warning(
                        'vehicle created with extended volume outside max volume range')
                # check if battery volume is enough to reach destination, if not draw triangular going down from energy required
                if new_ev.battery_volume < new_ev.energy_required:
                    new_ev.battery_volume = self.random.triangular(
                        new_ev.energy_required, new_ev.energy_required + 1, self.model.p.h_vol)
                    # self.EVs.battery_volume[index] = self.random.triangular(
                    #     self.model.p.l_vol, self.model.p.m_vol, self.model.p.h_vol)
                # set current volume to final max volume
                new_ev.current_battery_volume = new_ev.battery_volume * 0.9
                # set VTG percentage
                new_ev.allowed_VTG_percentage = self.model.p.VTG_percentage
                mun.current_EVs.append(new_ev)
                self.EVs.append(new_ev)
                index += 1
            mun_end = timer()
            logging.debug("mun {} complete, create {} evs, total {} evs created, create time {}, time now {}, evs per sec {}".
                          format(mun.name, mun.number_EVs, index + 1, round(mun_end - mun_start),
                                 round(mun_end - start), round(mun.number_EVs / (mun_end - mun_start))))

        # end timer for log model init
        end = timer()

        # additional logging
        logging.info("Model init completed in {} seconds".format(end - start))
        # push some stats to log file
        logging.info('MODEL CONFIGURATION')
        logging.info('EVs in model: {}'.format(len(self.EVs)))
        logging.info('Municipalities in model: {}'.format(
            len(self.municipalities)))
        logging.info('average battery volume of EVs (kWh): {}'.format(
            np.mean(list(self.EVs.battery_volume))))
        logging.info(
            'average energy rate of EVs (kWh/km): {}'.format(np.mean(list(self.EVs.energy_rate))))

    def step(self):
        #############################
        if self.t == 672:
            print('step {} EVs {}'.format(self.t,sum(self.municipalities.number_EVs)))
        # update weekend property
        if self.t % self.t_weekend == 0:
            self.weekend = True
            self.t_weekend += 672
        if self.t % 672 == 0:
            self.weekend = False
        if self.weekend:
            logging.info("{} Weekend day".format(self.t))
        else:
            logging.info("{} it's no weekend.".format(self.t))

        # for EVs
        self.fill_history()
        self.calc_ma_price_history()
        self.EVs.step()
        self.average_battery_percentage = np.mean(
            list(self.EVs.battery_percentage))
        self.total_current_power_demand = np.sum(
            list(self.EVs.current_power_demand))
        self.total_VTG_capacity = np.sum(list(self.EVs.VTG_capacity))
        self.mean_charging = np.mean(list(self.EVs.charging))
        # debug stats
        logging.debug('time {} EVs on road:{}'.format(self.model.t, len(
            self.EVs.select(self.EVs.current_location == 'onroad'))))
        logging.debug('time {} EVs at home:{}'.format(self.model.t, len(
            self.EVs.select(self.EVs.current_location == 'home'))))
        logging.debug('time {} EVs at work:{}'.format(self.model.t, len(
            self.EVs.select(self.EVs.current_location == 'work'))))

        

        # for municipalities
        self.municipalities.step()

    def update(self):
        """ Record dynamic variables """
        # model level, record and add to list for end stats (if not None and not np.nan)
        self.record('average_battery_percentage')
        if check_not_none(self.average_battery_percentage):
            self.list_average_battery_percentage.append(
                self.average_battery_percentage)
        self.record('total_current_power_demand')
        if check_not_none(self.total_current_power_demand):
            self.list_total_current_power_demand.append(
                self.total_current_power_demand)
        self.record('total_VTG_capacity')
        if check_not_none(self.total_VTG_capacity):
            self.list_total_VTG_capacity.append(self.total_VTG_capacity)
        self.record('mean_charging')
        if check_not_none(self.mean_charging):
            self.list_mean_charging.append(self.mean_charging)

        # municipality level
        self.municipalities.record('average_battery_percentage')
        self.municipalities.record('current_power_demand')
        self.municipalities.record('current_vtg_capacity')
        self.municipalities.record('current_power_demand')
        self.municipalities.record('number_EVs')

    def fill_history(self):
        '''
        Fills the memory of agents with the previous prices

        SHOULD BE DONE ON SUPERCLASS LEVEL TO SAVE DATA AND COMPUTATIONS

        '''
        index = self.t
        if self.t > len(self.Electricity_price['Electricity_price']):
            index = self.t % len(self.Electricity_price['Electricity_price'])
        self.price_history[(
            self.t % 96)-1].append(round(self.Electricity_price['Electricity_price'][self.t], 2))

    def calc_ma_price_history(self):
        '''
        From self.price_history creates avarage prices for a 24h cycle

        Could be expanded to a 4*24h cycle if wanted

        '''
        self.ma_price_history.clear()
        for i in self.price_history:
            segment = i[max(-7, -len(i)):]
            self.ma_price_history.append(round(np.mean(segment), 2))

    def end(self):
        """ report at end of the model"""
        if self.list_average_battery_percentage:
            self.report('min_average_battery_percentage', min(
                self.list_average_battery_percentage))
            self.report('mean_average_battery_percentage',
                        np.mean(self.list_average_battery_percentage))
        else:
            logging.info(
                'specified model parameters results in no records for average battery percentage')

        print(min(self.list_total_current_power_demand))

        if self.list_total_current_power_demand:
            # for some reason, storing a value of 0 gives an error in ema sobol analysis, so convert to 0.0000000001
            min_value = min(self.list_total_current_power_demand)
            if min_value == 0:
                min_value = 0.0000000001
            self.report('min_power_demand', min_value)
            self.report('mean_power_demand', np.mean(
                self.list_total_current_power_demand))
            self.report('max_power_demand', max(
                self.list_total_current_power_demand))
        else:
            logging.info(
                'specified model parameters results in no records for total current power demand')

        if self.list_total_VTG_capacity:
            # for some reason, storing a value of 0 gives an error in ema sobol analysis, so convert to 0.0000000001
            min_value = min(self.list_total_VTG_capacity)
            if min_value == 0:
                min_value = 0.0000000001
            self.report('min_VTG_capacity', min_value)
            self.report('mean_VTG_capacity', np.mean(
                self.list_total_VTG_capacity))
            self.report('max_VTG_capacity', max(self.list_total_VTG_capacity))
        else:
            logging.info(
                'specified model parameters results in no records for total VTG capacity')

        if self.list_mean_charging:
            # for some reason, storing a value of 0 gives an error in ema sobol analysis, so convert to 0.0000000001
            min_value = min(self.list_mean_charging)
            if min_value == 0:
                min_value = 0.0000000001
            self.report('min_mean_charging', min_value)
            self.report('mean_mean_charging', np.mean(self.list_mean_charging))
            self.report('max_mean_charging', max(self.list_mean_charging))
        else:
            logging.info(
                'specified model parameters results in no records for mean charging')
