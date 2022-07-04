import numpy as np
import agentpy as ap
import logging
import math

"""
All model compontents
"""


class EV(ap.Agent):
    """model class for electric vehicle agents. Most attributes are set to a value on the model level"""

    def setup(self):
        self.charging_speed = self.model.random.uniform(
            self.p.charging_speed_min, self.p.charging_speed_max)
        self.departure_time = int(self.model.random.triangular(
            self.model.p.l_dep, self.model.p.m_dep, self.model.p.h_dep))
        self.dwell_time = int(self.model.random.triangular(
            self.model.p.l_dwell, self.model.p.m_dwell, self.model.p.h_dwell))
        self.offset_dep = int(
            self.model.random.uniform(-self.model.p.offset_dep, self.model.p.offset_dep))
        self.offset_dwell = int(
            self.model.random.uniform(-self.model.p.offset_dwell, self.model.p.offset_dwell))
        self.current_location = 'home'
        self.arrival_time_home = None
        self.arrival_time_work = None
        self.moving = False
        self.charging = None
        self.return_time = self.departure_time + self.dwell_time
        self.battery_volume = self.model.random.triangular(
            self.model.p.l_vol, self.model.p.m_vol, self.model.p.h_vol)
        self.energy_rate = self.model.random.triangular(
            self.model.p.l_energy, self.model.p.m_energy, self.model.p.h_energy)
        if self.model.random.uniform(0,1) < self.model.p.p_pref:
            if self.model.random.uniform(0,1) < self.model.p.pref_home:
                self.charge_pref = 'home' # Home
            else:
                self.charge_pref = 'work' # Work
        else:
            self.charge_pref = None
        self.current_battery_volume = None
        self.battery_percentage = 100
        self.energy_required = None
        self.smart = self.model.random.random() < self.model.p.p_smart
        self.cheapest_timesteps = []
        self.current_power_demand = None
        self.battery_level_at_charging_start = self.battery_volume
        self.time_charging_must_finish = self.departure_time + self.offset_dep
        self.needed_battery_level_at_charging_end = self.battery_volume
        self.VTG_capacity = 0
        self.allowed_VTG_percentage = None
        self.force_charge = False
        self.plugged_in = False
        self.stick_to_pref = None

    def determine_strick_to_pref(self):
        if self.model.random.uniform(0,1) <= self.model.p.pref_strictness:
            self.stick_to_pref = True
        else:
            self.stick_to_pref = False

    def choose_cheapest_timesteps(self, starting_time, ending_time, charge_needed):
        '''This function will tell you the most economic (cheap) way of getting to a full charge within the time window, if possible
           The start and end time are ticks of 1 hour atm
           Charge needed still abstract/dimensionless, the amount of energy the car needs e.g. full or like 75% idc


           Function use:
           input starting and ending time of charge 
           function outputs cheapest predicted hours (ticks count of hour)
           hours can be set to charging? = true using this
        '''
        if starting_time % 96 < ending_time % 96:
            # e.g. charging from 1AM to 3PM is from 1:00 - 3:00
            total_time_window = self.model.ma_price_history[starting_time %
                                                            96:ending_time % 96]
        else:
            total_time_window = self.model.ma_price_history[starting_time %
                                                            96:] + self.model.ma_price_history[:ending_time % 96]
        timesteps_needed = math.ceil(charge_needed/(self.charging_speed*0.25))
        if timesteps_needed > (abs(ending_time-starting_time)):
            # charge all the available times
            logging.warning(
                'not enough timesteps for car {} to charge'.format(self.id))
            self.cheapest_timesteps = [
                i for i in range(starting_time, ending_time)]
        else:
            # give all indexes + starting_time that are cheapest
            timewindow = np.array(total_time_window.copy())
            idx = np.argpartition(timewindow, timesteps_needed - 1)
            cheapest_timesteps = idx[:timesteps_needed].tolist()
            self.cheapest_timesteps = [
                i + starting_time for i in cheapest_timesteps]

    def departure_work(self):
        self.current_location = 'onroad'  # go onroad
        self.moving = True
        self.charging = False
        self.arrival_time_work = self.model.t + self.travel_time  # ETA
        self.departure_time += 96  # update departure time
        self.plugged_in = False
        self.model.municipalities.select(
            self.model.municipalities.id == self.home_id).current_EVs.remove(self)

    def departure_home(self):
        self.current_location = 'onroad'
        self.moving = True
        self.charging = False
        self.arrival_time_home = self.model.t + self.travel_time
        self.plugged_in = False
        self.model.municipalities.select(
            self.model.municipalities.id == self.work_location_id).current_EVs.remove(self)

    def arrive_work(self):
        self.current_location = 'work'
        self.moving = False
        self.determine_strick_to_pref()
        self.return_time = self.model.t + self.dwell_time + self.offset_dwell
        self.plugged_in = True
        self.model.municipalities.select(
            self.model.municipalities.id == self.work_location_id).current_EVs.append(self)

        # related to charging
        self.battery_level_at_charging_start = self.current_battery_volume
        self.time_charging_must_finish = self.return_time
        logging.debug('In def arrive_work: \n self.energy_required {} \n self.current_battery_volume {}'.format(
            self.energy_required, self.current_battery_volume))
        if self.energy_required - self.current_battery_volume > 0:
            self.needed_battery_level_at_charging_end = self.energy_required
        else:
            self.needed_battery_level_at_charging_end = self.current_battery_volume

        if self.smart:
            self.choose_cheapest_timesteps(self.model.t, self.return_time, (max(
                0, self.energy_required - self.current_battery_volume)))

    def arrive_home(self):
        self.current_location = 'home'
        self.moving = False
        self.determine_strick_to_pref()
        self.plugged_in = True
        self.model.municipalities.select(
            self.model.municipalities.id == self.home_id).current_EVs.append(self)

        # related to charging
        self.battery_level_at_charging_start = self.current_battery_volume
        self.time_charging_must_finish = self.departure_time + self.offset_dep
        self.needed_battery_level_at_charging_end = self.battery_volume
        logging.debug('In def arrive_home: \n self.time_charging must finish {} \n self.needed_battery_level_at_charging_end {} \n self.battery_level_at_charging_start {} \n self.energy_required {} \n self.current_battery_volume {}'.format(
            self.time_charging_must_finish, self.needed_battery_level_at_charging_end, self.battery_level_at_charging_start, self.energy_required, self.current_battery_volume))
        if self.smart:
            self.choose_cheapest_timesteps(self.model.t, self.time_charging_must_finish,
                                           (self.battery_volume - self.current_battery_volume))
            logging.debug("{} cheapest timesteps are {}".format(
                self.id, self.cheapest_timesteps))  # at home, the battery will charge to full

    def charge(self):
        if self.current_battery_volume < self.battery_volume:
            increase = self.charging_speed * 0.25  # potential battery increase in 15min
            self.charging = True
            # check if potential increase does not exceed battery volume
            if self.current_battery_volume + increase < self.battery_volume:
                self.current_battery_volume += increase  # charge
            else:
                self.current_battery_volume = self.battery_volume  # set to max
        else:
            self.charging = False  # charging is false if the battery is full
    
    def discharge(self):
        self.charging = False
        logging.debug('car {} is discharging'.format(self.id))
        self.current_battery_volume -= self.energy_rate * \
            (self.model.p.average_driving_speed)  # energy consumption per 15min
    
    def determine_power_demand(self):
        if self.plugged_in:
            # variable is reset for good measure, as assurance for the adding VTG function below
            self.VTG_capacity = 0

            # if you are currently drawing power, you have a power demand
            if self.charging:
                self.current_power_demand = self.charging_speed * 0.25
            else:
                self.current_power_demand = 0

            # if the EV is plugged in and charging, but can postpone battery without falling under the latest charging moment bound
            logging.debug('current_battery_volume {} \n self.needed_battery_level_at_charging_end {} \n self.time_charging_must_finish {} \n self.energy_required {}'.format(
                self.current_battery_volume, self.needed_battery_level_at_charging_end, self.time_charging_must_finish, self.energy_required))

            # if your car has not reached the latest charging bound (lcb)
            # if there is at least one timestep worth of charging more in the battery
            if (self.current_battery_volume - self.charging_speed * 0.25) > \
                    (self.needed_battery_level_at_charging_end - (self.charging_speed * 0.25 * (self.time_charging_must_finish - self.model.t))):
                # if its smart and currently charging, you could now postpone some charging
                if self.smart:
                    # if you are smart, but not charging in this timestep, the VTG will not add
                    if any(i % self.model.t == 0 for i in self.cheapest_timesteps):
                        self.VTG_capacity = self.charging_speed * 0.25
                    else:
                        self.VTG_capacity = 0
                # if its not smart but charging, you could now postpone some charging
                else:
                    # only if your battery isnt full you can demand charge and therefore postpone that charge
                    if self.current_battery_volume < self.battery_volume:
                        self.VTG_capacity = self.charging_speed * 0.25

            # linear algebra to calculate the amount of VTG possible
            Intersection_Xcor_lcb = 0.5*(self.time_charging_must_finish + self.model.t) + (
                (2 / self.charging_speed) * (self.current_battery_volume - self.needed_battery_level_at_charging_end))
            Intersection_Ycor_lcb = 0.25*self.charging_speed * \
                (-Intersection_Xcor_lcb + self.model.t) + \
                self.current_battery_volume
            # distance lb = the amount of power you could empty until you reach the lower bound (lb)
            distance_lb = self.current_battery_volume-self.battery_level_at_charging_start
            # distance lcb = the amount of power you could empty until you reach the latest charging bound (lcb)
            distance_lcb = self.current_battery_volume-Intersection_Ycor_lcb

            self.VTG_capacity += max(min(distance_lb, distance_lcb,
                                     self.allowed_VTG_percentage*self.battery_volume), 0)

        else:
            self.current_power_demand = 0
            self.VTG_capacity = 0
            self.battery_level_at_charging_start = None
            self.time_charging_must_finish = None
            self.needed_battery_level_at_charging_end = None

    def step(self):
        """step function for EV, is called for every agent every time step"""
        # move, determine location and destination
        if (self.model.t % (self.departure_time + self.offset_dep) == 0) and (self.current_location == 'home'):
            # check if weekend
            if self.model.weekend:
                if self.model.random.uniform(0,1) < self.model.p.weekend_week_ratio:
                    depart = True
                else:
                    depart = False
                    self.departure_time += 96
            else:
                depart = True
            
            if self.current_battery_volume >= self.energy_required and depart:
                    self.departure_work()
            elif depart:
                logging.warning(
                    'charge too low to go in morning, should not happen')
                self.departure_time += 1
                self.charge()

            
        elif (self.model.t == self.arrival_time_work) and (self.current_location == 'onroad'):
            self.arrive_work()
        elif (self.model.t % self.return_time == 0) and (self.current_location == 'work'):
            # check if enough charge, else wait at work
            if self.current_battery_volume >= self.energy_required:
                self.departure_home()
            else:
                # if not enough charge, wait until enough charge is available
                self.return_time += 1
                self.charge()
        elif (self.model.t == self.arrival_time_home) and (self.current_location == 'onroad'):
            self.arrive_home()
            self.offset_dep = int(self.model.random.uniform(-self.model.p.offset_dep,
                                  self.model.p.offset_dep))  # Offset for the next day
            self.offset_dwell = int(self.model.random.uniform(
                -self.model.p.offset_dwell, self.model.p.offset_dwell))  # Offset for the next day
            logging.debug('{} a new departure offset has been caculated {}'.format(
                self.model.t, self.offset_dep))

        # Determine whether to charge or not based on pref
        if self.current_location != 'onroad':
            if self.current_battery_volume >= self.energy_required:
                if self.charge_pref != None:
                    self.plugged_in = True
                else:
                    if (self.current_location == self.charge_pref and \
                        self.stick_to_pref == True):
                        self.plugged_in = True
                    elif (self.current_location == self.charge_pref and \
                          self.stick_to_pref == False):
                        self.plugged_in = False
                    elif (self.current_location != self.charge_pref and \
                          self.stick_to_pref == False):
                        self.plugged_in = True
                    elif (self.current_location != self.charge_pref and \
                          self.stick_to_pref == True):
                        self.plugged_in = False
            else:
                self.plugged_in = True

        # discharging, idle or charging
        if self.current_location == 'onroad':
            self.discharge()
        else:
            if self.plugged_in:
                if self.smart:
                    if any(i % self.model.t == 0 for i in self.cheapest_timesteps) or self.force_charge:
                        self.charge()  # only charge on smart times
                        self.force_charge = False  # reset force charge
                        logging.debug('car {} is smart charging'.format(self.id))
                    else:
                        self.charging = False
                else:
                    self.charge()  # just go ahead and charge
                    self.force_charge = False  # reset force charge
                    logging.debug('car {} is normal charging'.format(self.id))
            else:
                self.charging = False
                self.force_charge = False

        # update current battery percentage
        self.battery_percentage = (
            self.current_battery_volume / self.battery_volume) * 100

        # determine current power demand and VTG capacity
        self.determine_power_demand()

        # final logging
        logging.debug('time {} battery_info car {} has {} percent battery, (absolute: {})'.format(
            self.model.t, self.id, self.battery_percentage, self.current_battery_volume))


class Municipality(ap.Agent):
    """model class for municipality agents. Most attributes are set to a value on the model level"""

    def setup(self):
        self.current_EVs = []
        self.current_power_demand = None
        self.current_vtg_capacity = None
        self.average_battery_percentage = None
        self.number_EVs = None

    def update_number_EVs(self):
        self.number_EVs = len(self.current_EVs)

    def update_power_demand(self):
        all_demand = [ev.current_power_demand for ev in self.current_EVs]
        self.current_power_demand = sum(all_demand)

    def update_vtg(self):
        vtg = [ev.VTG_capacity for ev in self.current_EVs]
        if vtg:
            self.current_vtg_capacity = np.mean(vtg)
    
    def update_battery_percentage(self):
        percentage = [ev.battery_percentage for ev in self.current_EVs]
        if percentage:
            self.average_battery_percentage = np.mean(percentage)

    def step(self):
        """updates all manucipality stats"""
        self.update_power_demand()
        self.update_number_EVs()
        self.update_vtg()
        self.update_battery_percentage()
