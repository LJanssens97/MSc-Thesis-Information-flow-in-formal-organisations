import copy

from mesa import Agent
from enum import Enum
import numpy as np
import random
from scipy.stats import skewnorm

import pandas as pd
"""
    Base class for all of the Employee components.
    
    Attributes
    -------------
    info_package_count : int
        The number of info_packages that an employee still has to do
    
    work_precision: float 
        The correctness of the processing. Number is between (0<1)
    
    work_speed: int
        Time it takes the employee to process info packages
    """
class Employee(Agent):
    def __init__(self, unique_id, model, node_location = 'unknown', work_precision = 0.5 , work_speed = 1):
        super().__init__(unique_id, model) #why? this is from the example.
        self.node_location = node_location #node_id
        self.info_package_processed = 0
        self.info_package_count = 0
        self.work_precision = work_precision
        self.work_speed = work_speed
        self.work_order = []
        self.model.employee_data[self.unique_id] = self.info_package_processed

    def ready_to_send(self, package_name):
        if self.work_order[len(self.work_order)-1] == package_name:
            return True
        else:
            return False

    def determine_work_order(self, new_package_type, new_package_name):
        #print('In function DETERMINE WORK ORDER')
        if new_package_name in self.work_order:
            return
        else:

            #print('Determining work order')
            # check if work_order is empty
            if not self.work_order:
                #print('If empty workorder: ', self.work_order)
                #self.work_order.append(new_package_name)
                self.work_order.insert(0, new_package_name)


            else:
                #print('If not empty workorder')
                # check package type (priority always goes in front, normal and permission go always in back)
                if new_package_type == 'Regular':
                    #self.work_order.append(new_package_name)
                    self.work_order.insert(0, new_package_name)



                elif new_package_type == 'Priority':
                    #self.work_order.insert(0, new_package_name)
                    self.work_order.append(new_package_name)


                elif new_package_type == 'Permission':
                    #self.work_order.append(new_package_name)
                    self.work_order.insert(0, new_package_name)



    #return the time it will take for a package to be processed.
    def get_processing_time(self, work_size):
        #print('get_processing_time was called')
        processing_time = 0

        try:
            processing_time = work_size / self.work_speed

        except Exception as e:
            print('Processing time set to 0, An error has occured in getting the processing_time: ', e)
        if(self.model.debug):
            print('processing time: ', processing_time)
        return processing_time

    #get the bit_string from the data_package and change it if chance says so
    def get_new_data(self, data_string):
        #print('get_new_data was called')

        #if random value is smaller than chance of mutation e.g. work_precision
        if random.uniform(0.0, 1.0) < self.work_precision:
            new_data = copy.deepcopy(data_string)
            #print('new data: ', new_data)
            bit_to_change = random.randint(0, len(data_string)-1)
            bit = data_string[bit_to_change]
            if bit ==1:
                bit = 0
            else:
                bit = 1
            new_data[bit_to_change] = bit
            #print('\n modify data was called. old data: ', data_string, 'new data: ', new_data)
            return new_data
        else:
            return data_string


    def step(self):
        pass

    def __str__(self):
        return  type(self).__name__+str(self.unique_id) # this one is straight from the example. Might nog be necessary.



class Autonomous (Employee):
    """
    Creates delay time and incorrectness

    Attributes
    __________
    precision:
        precision  of the employee

    work_speed: int
        the work_speed (in ticks) caused by this employee

    """
    def __init__(self, unique_id, model, node_location = 'unknown', work_precision = 1, work_speed = 1):
        super().__init__(unique_id, model, node_location , work_precision, work_speed)




class NonAutonomous (Employee):
    """
    Creates delay time and incorrectness

    Attributes
    __________
    precision:
        precision  of the employee

    work_speed: int
        the work_speed (in ticks) caused by this employee

    approval: state
        if the employee is allowed to continue sending information
    """
    permission_counter = 0


    def __init__(self, unique_id, model, node_location = 'unknown', work_precision = 1, work_speed = 1,
                 parentX = None, parentY = None ):
        super().__init__(unique_id, model, node_location, work_precision, work_speed)
        self.parents_updated_flag = False
        self.parentX = parentX
        self.parentY = parentY
        #print('my parentx: ', self.parentX, 'parenty: ', self.parentY)


    def ask_permission(self, sender_of_info_pos):
        try:
            #print('sender of info',sender_of_info_pos)
            if self.parentX == sender_of_info_pos:
                receiver = self.parentY
            else:
                receiver = self.parentX
            temp = np.array([self.pos ,receiver, self.pos])
            path = pd.Series(temp)

            name = str(self.unique_id)+'_Permission_'+str(NonAutonomous.permission_counter)

            time_to_process = random.randrange(self.model.scenarios_df.loc['Info-permission', 'min_Time_to_Process'],
                                               self.model.scenarios_df.loc['Info-permission', 'max_Time_to_Process'])
            agent = Info_Permission(name, self.model,
                                    self, path_ids = path, type_of_info='Permission', POS_sender= sender_of_info_pos,
                                    time_to_process=time_to_process, permission_generated_pos = self.pos ) # do I need the final self? this is from example
            if agent:
                self.model.schedule.add(agent)
                self.model.space.place_agent(agent, sender_of_info_pos)
            NonAutonomous.permission_counter += 1
            if self.model.debug:
                print('Permission request generated: ', name, 'Path of generated request:', path, ' By:', self.unique_id, ' loc:', self.pos, ' receiver:', receiver)
            return name

        except Exception as e:
            print("An error, ", e, " has occured while atempting to create an information_permission.")

    def check_permission(self, info_permission_name):
        #print('Checking Permission for ', self.unique_id, 'info perm: ', info_permission_name, 'work order:', self.work_order)
        #check if permission has returned and is now in work_order

        if info_permission_name in self.work_order:
            #print('check permission was successfully called')
            self.work_order.remove(info_permission_name)
            return True
        else:
            return False

class Collector (Employee):
    """
    Creates delay time and incorrectness

    Attributes
    __________
    precision:
        precision  of the employee

    work_speed: int
        the work_speed (in ticks) caused by this employee

    everything_collected
        if all the information is collected
    """

    def __init__(self, unique_id, model, node_location = 'unknown', work_precision = 1,
                 work_speed = 2, info_pack_required = 4, everything_collected = False):
        super().__init__(unique_id, model, node_location, work_precision, work_speed)
        self.info_pack_required = info_pack_required
        self.info_pack_received = len(self.work_order)
        #self.collected = everything_collected

    def everything_collected(self):
        self.info_pack_received = len(self.work_order)
        if self.info_pack_required <= self.info_pack_received:
            return True

        else:
            #self.collected = False
            return False

    #checks if in the work order
    def in_collection(self, info_pack_name):
        #print('def in_collection was called')
        to_be_sent = self.work_order[:self.info_pack_required]
        #print('work order: ', self.work_order, 'required: ', to_be_sent)
        if info_pack_name in to_be_sent:
            return True
        else:
            return False

class Controller (Employee):
    """
        Creates delay time and incorrectness

        Attributes
        __________
        allow_sending
            if all the information is collected

        all_mistakes_encountered (dict)
            stores every mistake found and the error margin.


        Functions
        ---------
        check_data_pack()
            checks if data is modified

            input: current_data_pack, original_data_pack, and datapack_id
            output: new_data_pack, time it took to process (e.g. steps or something)

        """
    def __init__(self, unique_id, model, node_location = 'unknown', work_precision = 1, work_speed = 1, allow_sending = False):
        super().__init__(unique_id, model, node_location, work_precision, work_speed)
        #self.allow_sending = allow_sending
        self.repair = True #this can later be changed if we want this or not...

    def check_data_pack(self, current_data_pack, orgininal_data_pack, data_pack_id):
        #print(current_data_pack, orgininal_data_pack)
        if current_data_pack == orgininal_data_pack:
            #self.allow_sending = True
            return current_data_pack, 15

        else:
            mistakes = 0
            repairs = 0
            copy_data_pack = copy.deepcopy(current_data_pack)

            for i in range(len(current_data_pack)):
                if current_data_pack[i] != orgininal_data_pack[i]:
                    mistakes += 1
                    if self.repair and (random.uniform(0.0, 1.0) < 0.7):
                        copy_data_pack[i] = 1
                        repairs+=1

            self.model.controller_data[0].append(self.unique_id)
            self.model.controller_data[1].append(data_pack_id)
            self.model.controller_data[2].append(len(current_data_pack))
            self.model.controller_data[3].append(mistakes)
            self.model.controller_data[4].append(repairs)
        return copy_data_pack, mistakes*60


class Source (Employee):

    """
    Source creates new information packages and sends them

    Attributes
    ------------
    info_frequency: int
        Number of information packages created

    info_pack_created: bool
        True if created
    """

    info_pack_created_flag = False
    counter = 0

    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.priority_chance = self.model.scenarios_df.loc['Network', 'priority_chance']
        self.generation_frequency = self.model.scenarios_df.loc['Network', 'info_pack_gen']

    def step(self):
        if self.model.schedule.steps % self.generation_frequency == 0:
            self.generate_info_pack()

        else:
            self.info_pack_created_flag = False

    def generate_info_pack(self):
        numValues = 10000
        maxValue = 240
        skewness = 8  # Negative values are left skewed, positive values are right skewed.
        distribution = skewnorm.rvs(a=skewness, loc=maxValue, size=numValues, scale=60)  # Skewnorm function
        distribution = distribution - 180  # Shift the set so the minimum value is equal to zero.
        distribution = distribution / max(distribution)  # Standadize all the vlues between 0 and 1.
        distribution = distribution * maxValue  # Multiply the standardized values by the maximum value.
        temp_time_process = int(np.random.choice(distribution))
        #print('time to process: ', temp_time_process, 'type: ', type(temp_time_process))
        #print('priority chance: ', self.priority_chance, 'type: ', type(self.priority_chance))
        try:

            if random.uniform(0.0, 1.0) < self.priority_chance:
                agent = Info_Priority('Info_priority_' + str(Source.counter), self.model, self, type_of_info='Priority',
                                      time_to_process= temp_time_process)
            else:

                agent = Info_Regular('Info_regular_' + str(Source.counter), self.model, self, type_of_info='Regular',
                                     time_to_process=temp_time_process)
            #print(agent)
            if agent:

                self.model.schedule.add(agent)
                self.model.space.place_agent(agent, self.pos)
                agent.set_path()
                Source.counter += 1
                self.info_pack_created_flag = True
                # self.employee_count += 1

        except Exception as e:
            print("Something went wrong, ", e.__class__, "occurred while generating an info pack.", e)
            print(e)

class Sink (Employee):
    """
        Removes information packages from the network

        Attributes
        __________
        info_pack_removed: bool
            True if removed
    """
    info_pack_removed = False

    def remove(self, info_package):

        try:
            #print('pos: ', info_package.pos)
            #print('1', info_package.pos)
            self.model.space.remove_agent(info_package)
            #print('2')
            self.model.schedule.remove(info_package)
            if self.model.debug:
                print('Removed info_package, ', info_package.unique_id, 'from: ', info_package.pos)
            self.info_pack_removed = not self.info_pack_removed #Maybe make this a toggle?
        except Exception as e:
            print('Something went wrong while removing agent', info_package.unique_id, ' : ', e, 'Happened')



#TODO Change order of and wording of the text below.
"""
    Attributes
    __________
    step_time: int
        the number of minutes (or seconds) a tick represents
        Used as a base to change unites

    state: Enum (CONTINUE | WAIT)
        state of the information

    location: Employee
        reference to the Infra where the information is located

    path_ids: Series
        the whole path (origin and destination) where the info shall go to
        It consists the Infras' uniques IDs in a sequential order

    location_index: int
        a pointer to the current Infra in "path_ids" (above)
        i.e. the id of self.location is self.path_ids[self.location_index]

    waiting_time: int
        the time the information needs to wait

    generated_at_step: int
        the timestamp (number of ticks) that the information is generated

    removed_at_step: int
        the timestamp (number of ticks) that the information is removed
    
    included_info_original: bit string
        The data that is originally sent
    
    included_info: bit string
        The current data set
    ...

    """
class Info_package (Agent):
    step_time = 1

    class State(Enum):
        CONTINUE = 1
        WAIT = 2

    def __init__(self, unique_id, model, generated_by, path_ids=None, time_to_process = 10,
                 type_of_info = 'No type given'):
        super().__init__(unique_id, model)
        self.waiting_time = 0
        self.data_pack_size = 20
        self.generated_by = generated_by
        self.generated_at_step = model.schedule.steps
        self.location = generated_by
        self.path_ids = path_ids
        self.type_of_info = type_of_info
        self.permission_request_name = 'No Name Given'
        self.permission_granted = False
        self.employees_visited = 0

        self.time_to_process = time_to_process
        self.data_pack = [1] * self.data_pack_size
        self.data_pack_original = self.data_pack

        # default values
        self.state = Info_package.State.CONTINUE
        self.location_index = 0
        self.waiting_time = 0
        self.removed_at_step = None

        #stuff to collect my data




    def __str__(self):
        return "Info_pack: " + str(self.unique_id) + '\n'+ \
               " +" + str(self.generated_at_step) + " -" + str(self.removed_at_step) + '\n'+ \
               " " + str(self.state) + '(' + str(self.waiting_time) + ') ' + '\n'+ \
               str(self.location) + '(' + str(self.location.info_package_processed) + ') '+'\n'+\
                'current time step: ' + str(self.model.schedule.steps)+'\n'

    def set_path(self):
        self.path_ids = self.model.get_route(self.generated_by.pos)


    def step(self):

        #print('Employee: ', self.location.unique_id, ' , Work order: ', self.location.work_order)
        #print('ID: ', self.unique_id, 'pos: ', self.pos)
        self.location.determine_work_order(self.type_of_info, self.unique_id)

        #storing data
        self.model.employee_step_business[0].append(self.model.schedule.steps)
        self.model.employee_step_business[1].append(self.location.unique_id)
        self.model.employee_step_business[2].append(self.location.info_package_count)

        #if self.state == Info_package.State.CONTINUE:
        #    self.move_to_next()

        # check if it's a collector
        if isinstance(self.location, Collector):
            #print('collector was found')
            if self.location.everything_collected():
                #print('why do I not get here?')
                # check if you're in the everything collected or outside
                if self.location.in_collection(self.unique_id):
                    #print(self.unique_id, 'I was in collection and I am being sent')
                    self.state = Info_package.State.CONTINUE
                else:
                    self.state = Info_package.State.WAIT
            else:
                self.state = Info_package.State.WAIT

        # if location is non_auto, continue when permission has returned!
        if isinstance(self.location, NonAutonomous):
            if not isinstance(self, Info_Permission):
                # if self.employees_visited <= 1:
                #    print('current location', self.location.unique_id)
                #    print('I havent visited much')
                #    self.State= Info_package.State.CONTINUE
                if not self.permission_granted:
                    self.state = Info_package.State.WAIT
                    #print('check permission for package: ', self.unique_id, 'permision request name: ',
                    #      self.permission_request_name)
                    self.permission_granted = self.location.check_permission(self.permission_request_name)

                    # print('do i get here???????????????????')
                    # self.permission_granted = self.location.check_permission(self.permission_request_name)
                if self.permission_granted:
                    #print(self)
                    # print('\n agents: ', self.schedule._agents)
                    if self.waiting_time < 1:
                        #print('do i get here?')
                        self.state = Info_package.State.CONTINUE
                        self.permission_granted = False
                    else:
                        self.waiting_time = max(self.waiting_time - 1, 0)
                        self.state = Info_package.State.WAIT
        #for other employees types, check if it's the infopacks turn
        elif self.location.ready_to_send(self.unique_id):
            #if it is auto or controller's turn
            if self.state == Info_package.State.WAIT:
                #print('Type: ', self.type_of_info)
                self.waiting_time = max(self.waiting_time -1, 0)
                if self.waiting_time == 0:
                    self.state = Info_package.State.CONTINUE

        if self.state == Info_package.State.CONTINUE:
            self.move_to_next()
        #print(self)

    def move_to_next(self):
        if self.model.debug:
            print('Current info_package : ', self.unique_id, 'moving to next, path_ids: ', self.path_ids, 'at location: ', self.pos)
        self.location_index +=1
        next_node = self.path_ids[self.location_index]#removed the -1, cause it is strange
        next_node_agent = self.model.employee_node_dict[next_node]
        next_employee = self.model.schedule._agents[next_node_agent]

        if self.model.debug:
            print('\n Information package type: ', self.type_of_info, ', ID: ', self.unique_id, '\n',
                  'At position: ', self.pos, ', Employee: ', self.location.unique_id, ', Next Employee: ', next_employee,
                  ', pos', next_node, ', index: ', self.location_index, '\n',
                  'Current Data: ', self.data_pack, ', Original data: ', self.data_pack_original, '\n',
                  'My path: ', self.path_ids)
            print('PATH TYPE: ', type(self.path_ids))


        # when at sink
        if isinstance(next_employee, Sink):
            #print('\n Package going to be removed: ', self.unique_id, 'Removed at pos: ', self.pos, 'by employee: ', next_employee.unique_id)
            #print('sink so send to next')
            self.arrive_at_next(next_employee)
            #self.removed_at_step = self.model.schedule.steps
            #self.location.remove(self)
            return

        if isinstance(next_employee, Autonomous):
            self.data_pack = next_employee.get_new_data(self.data_pack)
            self.waiting_time = next_employee.get_processing_time(self.time_to_process)

            if self.waiting_time > 0:
                #wait at the next employee
                self.arrive_at_next(next_employee)
                self.State = Info_package.State.WAIT
                return

        #Non Autonomous Agent
        if isinstance(next_employee, NonAutonomous):
            self.data_pack = next_employee.get_new_data(self.data_pack)
            self.waiting_time = next_employee.get_processing_time(self.time_to_process)
            if self.type_of_info != 'Permission':

                self.permission_request_name = next_employee.ask_permission(self.location.pos)
                #print('permission request name', self.permission_request_name)

            if self.waiting_time > 0:
                # wait at the next employee
                self.arrive_at_next(next_employee)
                self.State = Info_package.State.WAIT
                return

        #Collector Agent
        if isinstance(next_employee, Collector):
            self.data_pack = next_employee.get_new_data(self.data_pack)
            self.waiting_time = next_employee.get_processing_time(self.time_to_process)


            if self.waiting_time > 0:
                # wait at the next employee
                self.arrive_at_next(next_employee)
                self.State = Info_package.State.WAIT
                return

        #controller does not modify data by making it incorrect, it checks and adds time if it is incorrect
        if isinstance(next_employee, Controller):
            self.waiting_time = next_employee.get_processing_time(self.time_to_process)
            new_data, addedwaiting_time = next_employee.check_data_pack(self.data_pack, self.data_pack_original,
                                                                        self.unique_id)
            self.data_pack = new_data
            self.waiting_time += addedwaiting_time

            if self.waiting_time > 0:
                # wait at the next employee
                self.arrive_at_next(next_employee)
                self.State = Info_package.State.WAIT
                return


    def arrive_at_next(self, next_employee):
        next_node = self.path_ids[self.location_index]
        #print(self.unique_id, ' is moving to next', next_node)

        self.location.work_order.remove(self.unique_id)
        self.employees_visited +=1
        self.location.info_package_processed += 1
        self.model.employee_data[self.location.unique_id] = self.location.info_package_processed
        self.model.space.move_agent(self, next_node)
        self.location.info_package_count -= 1
        self.location = next_employee
        self.location.info_package_count += 1

        if isinstance(next_employee, Sink):
            if self.model.debug:
                print('\n Package going to be removed: ', self.unique_id, 'Removed at pos: ', self.pos, 'by employee: ', next_employee.unique_id)
            #print('sink so send to next')
            #self.arrive_at_next(next_employee)

            self.removed_at_step = self.model.schedule.steps
            #print("REMOVED", self.unique_id, "at sink: ", self.location.unique_id)
            self.model.info_pack_travel_data[0].append(self.unique_id)
            self.model.info_pack_travel_data[1].append(self.generated_at_step)
            self.model.info_pack_travel_data[2].append(self.removed_at_step)
            self.model.info_pack_travel_data[3].append(self.generated_by)
            self.model.info_pack_travel_data[4].append(self.location.unique_id)
            self.model.info_pack_travel_data[5].append(self.employees_visited)

            temp_mistakes = 0
            for i in range(len(self.data_pack_original)):
                if self.data_pack[i] != self.data_pack_original[i]:
                    temp_mistakes += 1
            error_percentage = (temp_mistakes/len(self.data_pack_original))*100
            self.model.info_pack_data_data[0].append(self.unique_id)
            self.model.info_pack_data_data[1].append(self.data_pack_original)
            self.model.info_pack_data_data[2].append(self.data_pack)
            self.model.info_pack_data_data[3].append(error_percentage)

            self.location.remove(self)

        next_employee.determine_work_order(self.type_of_info, self.unique_id)
        if self.model.debug:
            print('Work order of next employee: ', next_employee.unique_id, next_employee.work_order)

        #print(self)
        if isinstance(self, Info_Permission):
            #print('next_employee.pos: ', next_employee.pos, self.permission_generated_pos)
            if next_employee.pos == self.permission_generated_pos:

                if self.model.debug:
                    print('\n Permission info pack : ', self.unique_id, 'Removed at pos: ', self.pos, 'by employee: ', next_employee.unique_id)

                try:
                    self.model.space.remove_agent(self)
                    self.model.schedule.remove(self)
                    #self.location.work_order.remove(self.unique_id)
                    if self.model.debug:
                        print('Removed info_package, ', self.unique_id, 'from: ', self.pos)

                except Exception as e:
                    print('Something went wrong while removing agent', self.unique_id, ' : ', e, 'Happened')
        #move to the next node in the graph from the path
#test

class Info_Regular (Info_package):
    pass

class Info_Priority (Info_package):
    pass

class Info_Permission( Info_package):
    def __init__(self, unique_id, model, generated_by, path_ids=None, time_to_process = 10, type_of_info = 'No type given', POS_sender = None, permission_generated_pos = None):
        self.POS_sender = POS_sender
        self.permission_generated_pos = permission_generated_pos
        super().__init__(unique_id, model, generated_by, path_ids, time_to_process, type_of_info)

