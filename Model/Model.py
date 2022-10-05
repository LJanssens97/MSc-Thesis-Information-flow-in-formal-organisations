from mesa import space
from mesa.time import BaseScheduler
import random
from mesa import Model, Agent
from datetime import datetime
from Components import Source, Sink, Autonomous, NonAutonomous, Collector, Controller
import networkx as nx
import copy
import pandas as pd
from collections import defaultdict
import Networks as net


def get_final_info_pack_processed(Model):
    employee_info_pack_processed = [agent.info_package_processed for agent in Model.schedule.agents]
    #print(employee_info_pack_processed)
    return employee_info_pack_processed

class InformationFlowModel(Model):
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


        # case study graph generation (model from data)
        self.file_edge = file_edge
        self.file_node_attr = file_node_attributes

        # random network generation
        self.trophic_incoherence = tropic_incoherence
        self.controller_chance = controller_chance
        self.num_nodes = num_nodes

        #Variables necessary to collect my data
        #step, employee ID, info_pack_count
        self.employee_step_business = [[],[],[]]

        # employee ID, info_pack_processed
        self.employee_data = {}

        #controller data: employeeID, infopackageID, len, mistakes, repairs
        self.controller_data = [[],[],[],[],[]]


        # info_pack_id, generated@step, removed@step, generatedBy, removedBy, employees_visited
        self.info_pack_travel_data = [[], [], [], [], [], []]


        # info_pack_id, original, current
        self.info_pack_data_data = [[], [], [], []]


        #collecting numer and types of agents:
        self.num_empl_auto = 0
        self.num_empl_nonA = 0
        self.num_empl_cont = 0
        self.num_empl_coll = 0

        #time for labeling data export files
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

    #this function generates a model based on the randomly generated network.
    def generate_model_random(self):
        # Create Sources
        in_degrees = dict(self.G.in_degree)
        out_degrees = dict(self.G.out_degree)
        if self.debug:
            print('list of nodes: ', self.G.nodes())
            print('list of in_degrees: ', in_degrees, '\n', 'list of out_degrees: ', out_degrees)

        # placing agents in the network
        for i, node in enumerate(self.G.nodes()):

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
            self.employee_node_dict[node] = temp_name
            self.schedule.add(agent)
            self.space.place_agent(agent, node)

    #Generate the model based on the network from data
    def generate_model_from_data(self):
        for i, node in enumerate(self.G.nodes()):

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

    #Get a path between a source and a sink. The name shortest path is the old function that it had.
    def get_shortest_path(self, source, sink):
        #with random paths, the first generated path is chosen. This is due to the exponential number of paths when
        #large networks are generated
        if self.random_graph:
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

    # this function returns a random route given an info_pakc instance's source
    def get_random_route(self, source):
        sink = self.random.choice(self.sinks)
        if (source, sink) in self.path_ids_dict:

            # if yes, assign the excisting path to the info_pack
            return self.path_ids_dict[source, sink]

        else:
            while True:
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

            # add the newly-found path to the path_ids_dict
            self.path_ids_dict[path[0], path.iloc[-1]] = path
            return self.path_ids_dict[source, sink]

    #this function was created to allow for predetermined paths to be implemented.
    def get_route(self, source):
        return self.get_random_route(source)

    def step(self):
        #self.datacollector.collect(self)
        self.schedule.step()
