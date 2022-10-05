import mesa
import time
from mesa import space
import TrophicAddapted as tropA
from mesa.time import BaseScheduler
import random
from mesa import Model, Agent
from datetime import datetime
import xml.etree.ElementTree as ET
from Components import Source, Sink, Autonomous, NonAutonomous, Collector, Controller
from Components import Info_Regular, Info_Priority
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import copy
from pathlib import Path
from mesa.datacollection import DataCollector
import pandas as pd
from collections import defaultdict
import json
from scipy.stats import rv_continuous

from collections import defaultdict
import Networks as net


def get_final_info_pack_processed(Model):
    employee_info_pack_processed = [agent.info_package_processed for agent in Model.schedule.agents]
    #print(employee_info_pack_processed)
    return employee_info_pack_processed

class InformationFlowModel(Model):
    """"
    Main simulation model.

    Time is processed in minutes at this point. #ToDo perhaps different time steps

    class Attributes:
    step_time: int

    path_ids_dictionary: defaultdict #Todo this is from old code
    key: (origin, destination)
    value: depends on random graph or chosen graph.

    sources: list

    sinks: list

    """
    step_time = 2

    # input data for the graph

    def __init__(self, seed=None, random_graph=True, num_nodes=40, controller_chance=0.1, file_edge=None, file_node_attributes = None, debug=False,
                 tropic_incoherence = 0.7, scenarios_df = None, scenario = None):
        # __init__ for the model
        self.path_ids_dict = defaultdict(lambda: pd.Series())
        self.schedule = BaseScheduler(self)
        self.scenarios_df = scenarios_df
        self.random_graph = random_graph
        self.space = None
        self.seed = seed
        self.running = True
        self.debug = debug
        self.sources = []
        self.sinks = []
        self.employee_node_dict = {}
        self.scenario = scenario


        # data graph generation
        self.file_edge = file_edge
        self.file_node_attr = file_node_attributes

        # random network generation
        self.trophic_incoherence = tropic_incoherence
        self.controller_chance = controller_chance
        self.num_nodes = num_nodes




        #Stuff necessary to collect my data

        #step, employee ID, info_pack_count
        self.employee_step_business = [[],[],[]]

        # employee ID, info_pack_processed
        self.employee_data = {}

        #controller data: employeeID, infopackageID, len, mistakes, repairs
        self.controller_data = [[],[],[],[],[]]
       # self.controller_data[0].append('employee_id')
       # self.controller_data[1].append('info_pack_id')
       # self.controller_data[2].append('len')
       # self.controller_data[3].append('mistakes')
       # self.controller_data[4].append('repairs')

        # info_pack_id, generated@step, removed@step, generatedBy, removedBy, employees_visited
        self.info_pack_travel_data = [[], [], [], [], [], []]
        #self.info_pack_travel_data[0].append('info_pack_id')
        #self.info_pack_travel_data[1].append('generated_at_step')
        #self.info_pack_travel_data[2].append('removed_at_step')
        #self.info_pack_travel_data[3].append('generated_by')
        #self.info_pack_travel_data[4].append('removed_by')
        #self.info_pack_travel_data[5].append('employees_visited')

        # info_pack_id, original, current
        self.info_pack_data_data = [[], [], [], []]
       # self.info_pack_data_data[0].append('info_pack_id')
       # self.info_pack_data_data[1].append('original')
       # self.info_pack_data_data[2].append('current')
       # self.info_pack_data_data[3].append('error_percentage')

        #collecting numer and types of agents:
        self.num_empl_auto = 0
        self.num_empl_nonA = 0
        self.num_empl_cont = 0
        self.num_empl_coll = 0
        now = datetime.now()
        date = now.strftime("_date_%Y-%m-%d_%H-%M-%S")
        # To determine what to use as input
        if self.random_graph:
            print('Generating graph randomly based on input file parameters')
            probability = self.scenarios_df.loc['Network', 'probability']
            print('probability:' , probability)
            self.G, new_seed, prob = net.create_random_graph(self.num_nodes, self.seed, self.trophic_incoherence, self.scenario, probability=probability)
            self.G_undirected = copy.deepcopy(self.G)
            self.G_undirected.to_undirected()
            self.seed = new_seed
            self.space = space.NetworkGrid(self.G_undirected)


            net.print_network_statistics(self.G)

            self.generate_model_random()
            net.write_results_to_file('../Results/Networks/network_stats.txt', seed=self.seed, G=self.G, prob=prob,
                                      num_empl_auto=self.num_empl_auto, num_empl_nonA=self.num_empl_nonA,
                                      num_empl_cont=self.num_empl_cont, num_empl_coll=self.num_empl_coll)
            G_with_employee_names = nx.relabel_nodes(self.G, self.employee_node_dict)
            title = 'Graph - N - ' + str(len(self.G.nodes))+ ', TI - '+ str(self.trophic_incoherence) + 'Date - ' + date
            net.draw_graph(G_with_employee_names, title, self.scenario, title)
            file_location = '../Results/Networks/Network_N' + str(len(self.G.nodes)) + date+'.gexf'
            nx.write_gexf(G_with_employee_names, file_location)

        else:
            print('Generating graph from data source. ')
            self.G = net.create_graph_from_source(self.file_edge, self.file_node_attr)
            self.G_undirected = copy.deepcopy(self.G)
            self.space = space.NetworkGrid(self.G_undirected)
            self.generate_model_from_data()
            G_with_employee_names = nx.relabel_nodes(self.G, self.employee_node_dict)
            title = 'Graph - N ' + str(len(self.G.nodes)) + ', Defence Network'+ 'Date - ' + date
            net.write_results_to_file('../Results/Networks/network_stats.txt', seed=self.seed, G=self.G, prob='none',
                                      num_empl_auto= self.num_empl_auto, num_empl_nonA=self.num_empl_nonA,
                                      num_empl_cont= self.num_empl_cont, num_empl_coll=self.num_empl_coll)
            net.print_network_statistics(self.G)
            net.draw_graph(G_with_employee_names, title, self.scenario, title)
            file_location = '../Results/Networks/Network_N' + str(len(self.G.nodes)) + date+'.gexf'
            nx.write_gexf(G_with_employee_names, file_location)

    def generate_model_random(self):
        # Create Sources
        in_degrees = dict(self.G.in_degree)
        out_degrees = dict(self.G.out_degree)
        if self.debug:
            print('list of nodes: ', self.G.nodes())
            print('list of in_degrees: ', in_degrees, '\n', 'list of out_degrees: ', out_degrees)

        #make new graph with the new names
        #self.G_adapted = copy.deepcopy(self.G)
        #counters for types of agents in network:

        # placing agents in the network
        for i, node in enumerate(self.G.nodes()):
            #print('node: ', node, '\n', 'in_degree[node]: ', in_degrees[node])

            # source
            if in_degrees[node] == 0:
                temp_name = 'source_'+str(node)
                self.sources.append(node)
                agent = Source(temp_name, self)

            # sink
            elif out_degrees[node] == 0:
                temp_name = 'sink_' + str(node)
                self.sinks.append(node)
                agent = Sink(temp_name, self)


            elif in_degrees[node] == 1:
                # Controller
                if self.controller_chance > random.uniform(0.0, 1.0):
                    work_speed = round(random.uniform(self.scenarios_df.loc['Empl-Cont', 'min_work_speed'],
                                                      self.scenarios_df.loc['Empl-Cont', 'max_work_speed']), 2)
                    work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-Cont', 'min_work_precission'],
                                                         self.scenarios_df.loc['Empl-Cont', 'max_work_precission']), 2)
                    #print('work speed: ', work_speed, 'work_accuracy: ', work_accuracy)
                    temp_name = 'controller_' + str(node)
                    agent = Controller(temp_name, self, work_speed=work_speed, work_precision=work_accuracy)
                    self.num_empl_cont +=1

                # Autonomous
                else:
                    temp_name = 'auto_' + str(node)
                    work_speed = round(random.uniform(self.scenarios_df.loc['Empl-auto', 'min_work_speed'],
                                                      self.scenarios_df.loc['Empl-auto', 'max_work_speed']), 2)
                    work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-auto', 'min_work_precission'],
                                                         self.scenarios_df.loc['Empl-auto', 'max_work_precission']), 2)
                    agent = Autonomous(temp_name, self, work_speed=work_speed, work_precision=work_accuracy)
                    self.num_empl_auto +=1
            # non_autonomous
            elif in_degrees[node] == 2:
                temp_name = 'non_auto_' + str(node)
                parents = [pred for pred in self.G.predecessors(node)]
                x_node = parents[0]
                y_node = parents[1]
                work_speed = round(random.uniform(self.scenarios_df.loc['Empl-nonA', 'min_work_speed'],
                                                  self.scenarios_df.loc['Empl-nonA', 'max_work_speed']), 2)
                work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-nonA', 'min_work_precission'],
                                                     self.scenarios_df.loc['Empl-nonA', 'max_work_precission']), 2)
                agent = NonAutonomous(temp_name, self, parentX= x_node , parentY= y_node,
                                      work_speed=work_speed, work_precision=work_accuracy)
                self.num_empl_nonA +=1
            # Collector
            elif in_degrees[node] >= 3:
                temp_name = 'collector_' + str(node)
                work_speed = round(random.uniform(self.scenarios_df.loc['Empl-Coll', 'min_work_speed'],
                                                  self.scenarios_df.loc['Empl-Coll', 'max_work_speed']), 2)
                work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-Coll', 'min_work_precission'],
                                                     self.scenarios_df.loc['Empl-Coll', 'max_work_precission']), 2)
                info_pack_required = random.randrange(self.scenarios_df.loc['Empl-Coll', 'min_info_pack_required'],
                                                      self.scenarios_df.loc['Empl-Coll', 'max_info_pack_required'])
                agent = Collector(temp_name, self, work_speed=work_speed, work_precision=work_accuracy, info_pack_required=info_pack_required)
                self.num_empl_coll +=1
            #add the assigned agent
            self.employee_node_dict[node] = temp_name
            #print('workspeed: ', work_speed, 'work_accuracy: ', work_accuracy)
            self.schedule.add(agent)
            self.space.place_agent(agent, node)

    def generate_model_from_data(self):
        for i, node in enumerate(self.G.nodes()):
            #print('node: ', node, '\n', 'i:', i)

            # source
            if self.G.nodes[node]['employee']=='source':
                temp_name = 'source_'+str(i)
                self.sources.append(node)
                agent = Source(node, self)

            # sink
            elif self.G.nodes[node]['employee']=='sink':
                temp_name = 'sink_' + str(i)
                self.sinks.append(node)
                agent = Sink(temp_name, self)

            # Controller
            elif self.G.nodes[node]['employee']=='controller':
                work_speed = round(random.uniform(self.scenarios_df.loc['Empl-Cont', 'min_work_speed'],
                                                  self.scenarios_df.loc['Empl-Cont', 'max_work_speed']), 2)
                work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-Cont', 'min_work_precission'],
                                                     self.scenarios_df.loc['Empl-Cont', 'max_work_precission']), 2)
                temp_name = 'controller_' + str(i)
                agent = Controller(temp_name, self, work_speed= work_speed, work_precision=work_accuracy)

            # Autonomous
            elif self.G.nodes[node]['employee']=='auto':
                work_speed = round(random.uniform(self.scenarios_df.loc['Empl-auto', 'min_work_speed'],
                                                  self.scenarios_df.loc['Empl-auto', 'max_work_speed']), 2)
                work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-auto', 'min_work_precission'],
                                                     self.scenarios_df.loc['Empl-auto', 'max_work_precission']), 2)
                temp_name = 'auto_' + str(i)
                agent = Autonomous(temp_name, self, work_speed= work_speed, work_precision=work_accuracy)

            # non_autonomous
            elif self.G.nodes[node]['employee']=='non_auto':
                work_speed = round(random.uniform(self.scenarios_df.loc['Empl-nonA', 'min_work_speed'],
                                                  self.scenarios_df.loc['Empl-nonA', 'max_work_speed']), 2)
                work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-nonA', 'min_work_precission'],
                                                     self.scenarios_df.loc['Empl-nonA', 'max_work_precission']), 2)
                temp_name = 'non_auto_' + str(i)
                parents = [pred for pred in self.G.predecessors(node)]
                x_node = parents[0]
                y_node = parents[1]
                agent = NonAutonomous(temp_name, self, parentX=x_node, parentY=y_node, work_speed= work_speed, work_precision=work_accuracy)

            # Collector
            elif self.G.nodes[node]['employee']=='collector':
                work_speed = round(random.uniform(self.scenarios_df.loc['Empl-Coll', 'min_work_speed'],
                                                  self.scenarios_df.loc['Empl-Coll', 'max_work_speed']), 2)
                work_accuracy = round(random.uniform(self.scenarios_df.loc['Empl-Coll', 'min_work_precission'],
                                                     self.scenarios_df.loc['Empl-Coll', 'max_work_precission']), 2)
                info_pack_required = random.randrange(self.scenarios_df.loc['Empl-Coll', 'min_info_pack_required'],
                                                      self.scenarios_df.loc['Empl-Coll', 'max_info_pack_required'])
                temp_name = 'collector_' + str(i)
                agent = Collector(temp_name, self, work_speed= work_speed, work_precision=work_accuracy, info_pack_required=info_pack_required)

            else:
                temp_name = 'Agent got no employee'

            self.employee_node_dict[node] = temp_name
            self.schedule.add(agent)
            self.space.place_agent(agent, node)

    def get_shortest_path(self, source, sink):
        if self.random_graph:
            #print('getting a path')
            #random path:

            path2 = next(nx.all_simple_paths(self.G, source=source, target=sink))
            path = pd.Series(path2)
            return path
        else:
            path = nx.all_simple_paths(self.G, source=source, target=sink)
            path = pd.Series(path)
            df = path.to_frame()
            temp = df.iloc[:,0].sample()
            temp2 = temp[1]
            temp3 = pd.Series(temp2)
            return temp3

    # this function will return a random route given an info_pakc instance's source
    # this function will be called by a info_pack once it is instanciated
    # (info_pack are created by a source and thus have their beginning point)
    def get_random_route(self, source):
        #first, to make sure a vehicle's source is not also his sink, their source gets removed from the sink.list
        #print('List of Sinks: ', self.sinks)
        #self.sinks.remove(source)
        sink = self.random.choice(self.sinks)
        #print('Source: ', source, 'Sinks: ', self.sinks)
        #self.sinks.append(source)
        if (source, sink) in self.path_ids_dict:
            #print("already in dict!", [source, sink])
            # if yes, assign the excisting path to the info_pack
            return self.path_ids_dict[source, sink]

        else:
            go = False
            while True:
                #print('not in dict', source, sink)
                # if no, calculate the shortest path using the get_shortest_path function
                try:
                    path = self.get_shortest_path(source, sink)
                except Exception as e:
                    path = None
                    if self.debug:
                        print('An error: ', e , ' has occured while trying to find a path between: ', source, sink)

                if path is not None:
                    #print('path should be existing :', path)
                    break

                sink = self.random.choice(self.sinks)
                #print('Randomly choose new sink: ', sink)


                # add the newly-found path to the path_ids_dict
            self.path_ids_dict[path[0], path.iloc[-1]] = path
                #print('path: ', self.path_ids_dict)
                # assign the path to the vehicle

            return self.path_ids_dict[source, sink]

    def get_route(self, source):
        return self.get_random_route(source)

    def step(self):
        #self.datacollector.collect(self)
        self.schedule.step()



# self.datacollector = mesa.DataCollector(  # ToDO Initial setup datacollector
#    model_reporters={
#        "Average Delay Time": avg_delay_time,
#        "Packets in the system": total_info_packet,
#    }
# )

# self.datacollector.collect(self)
