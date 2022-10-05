import random
import time
import TrophicAddapted as tropA
from datetime import datetime
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import copy
from pathlib import Path
import pandas as pd
from collections import defaultdict
import json

def draw_graph(G, title = 'No Title Given', scenario=None):
    title = ' ' + str(title) +' scenario{0} '.format(scenario)
    try:
        fig, ax = plt.subplots(figsize=(25/2.54, 30/2.54), dpi=120)
        pos = nx.planar_layout(G, scale=1 )
        nx.draw_networkx(G, pos = pos, with_labels=True, node_size = 400, ax=ax)
        ax.set_title(title, fontsize=25)
        ax.axis('off')

    except:
        fig, ax = plt.subplots(figsize=(25 / 2.54, 30 / 2.54), dpi=120)
        pos = nx.spring_layout(G)
        nx.draw_networkx(G, pos=pos, with_labels=True, node_size=400, ax=ax)
        ax.set_title(title, fontsize=25)
        ax.axis('off')
    plt.show()

def draw_graph(G, title = 'No Title Given', scenario=None, file_name ='None given'):
    title = ' ' + str(title) +' scenario{0} '.format(scenario)
    try:
        fig, ax = plt.subplots(figsize=(25/2.54, 30/2.54), dpi=120)
        pos = nx.planar_layout(G, scale=1 )
        nx.draw_networkx(G, pos = pos, with_labels=True, node_size = 400, ax=ax)
        ax.set_title(title, fontsize=25)
        ax.axis('off')
    except:
        fig, ax = plt.subplots(figsize=(25 / 2.54, 30 / 2.54), dpi=120)
        pos = nx.spring_layout(G)
        nx.draw_networkx(G, pos=pos, with_labels=True, node_size=400, ax=ax)
        ax.set_title(title, fontsize=25)
        ax.axis('off')

    locationstorage = '../Results/Networks/Fig_network_' + file_name+'.png'
    plt.savefig(locationstorage)



def get_network_statistics(G):
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    sink_nodes, source_nodes = count_sink_source_nodes(G)
    in_degrees = dict(G.in_degree)
    out_degrees = dict(G.out_degree)
    avg_in_degree = sum(in_degrees.values()) / float(len(G))
    avg_out_degree = sum(out_degrees.values()) / float(len(G))
    density = nx.density(G)
    trophic_incoherence_parameter = tropA.trophic_incoherence_parameter(G)
    average_shortest_path = nx.average_shortest_path_length(G)
    return num_nodes, num_edges, len(sink_nodes), len(source_nodes),avg_in_degree, avg_out_degree, density, trophic_incoherence_parameter ,average_shortest_path # , eigenvector_centrality, betweenness_centrality, avg_shortest_path

def write_results_to_file(file = '../Results/network_stats.txt', G=None, seed=None, prob = None, num_empl_auto = None,
                          num_empl_nonA = None , num_empl_cont = None, num_empl_coll = None):
    now = datetime.now()
    date = now.strftime("_date_%Y-%m-%d, %H:%M:%S")
    fle = Path(file)
    fle.touch(exist_ok=True)
    f = open(fle, 'a')

    num_nodes, num_edges, sink_nodes, source_nodes, avg_in_degree, avg_out_degree, density, trophic_incoherence_parameter,average_shortest_path = get_network_statistics(G)
    average_shortest_path = nx.average_shortest_path_length(G)
    info = '\n \nTime of attempt: '+ date +'\nNumber of Nodes: '+ str(num_nodes) + '\nNumber of Edges: '+ str(num_edges)\
           + '\nSink nodes in network: '+ str(sink_nodes)  + '\nSource nodes in network: '+ str(source_nodes) + \
           '\nAverage in Degree: '+ str(avg_in_degree) + '\nAverage out Degree: '+ str(avg_out_degree) + \
           '\nNetwork Density: '+ str(density) + '\nTrophic Incoherence: '+ str(trophic_incoherence_parameter) + \
           '\nAverage shortest path lenght: ' + str(average_shortest_path) + \
           '\nNumber of Autonomous: ' + str(num_empl_auto) +'\nNumber of Non Autonomous: ' + str(num_empl_nonA) +\
           '\nNumber of Collector: ' + str(num_empl_coll) +'\nNumber of Controller: ' + str(num_empl_cont)

    seedtxt = '\nSeed: ' + str(seed) + '\nProbability P: ' + str(prob)
    f.write(info)
    f.write(seedtxt)
    f.close()

def print_network_statistics(G):
    num_nodes, num_edges, sink_nodes, source_nodes, avg_in_degree, avg_out_degree, density, trophic_incoherence_parameter,average_shortest_path = get_network_statistics(G)
    print('Number of Nodes: ',num_nodes)
    print('Number of Edges: ', num_edges)
    print('Sink nodes in network: ', sink_nodes)
    print('Source nodes in network: ', source_nodes)
    print('Average in Degree: ', avg_in_degree)
    print('Average out Degree: ', avg_out_degree)
    print('Network Density: ', density)
    print('Trophic Incoherence: ', trophic_incoherence_parameter)

def count_sink_source_nodes(G):
    source_nodes = []
    sink_nodes = []
    in_degrees = dict(G.in_degree)
    out_degrees = dict(G.out_degree)

    # count sink nodes
    for key, item in in_degrees.items():
        if (in_degrees[key] >= 1) and (out_degrees[key] == 0):
            sink_nodes.append(key)
            #print('key of sink', key)

        # count source nodes
        if (in_degrees[key] == 0) and (out_degrees[key] >= 1):
            #print('key of source', key)
            source_nodes.append(key)

    return sink_nodes, source_nodes

#this function checks for every source in the network if there is a path to at least one sink
def check_if_source_connected_to_one_sink(G):
    sink_nodes, source_nodes = count_sink_source_nodes(G) #get list of source and sink nodes in network
    everything_has_a_path = 0
    for i in range(len(source_nodes)):
        print('number of sources to check: ', len(source_nodes))
        for j in range(len(sink_nodes)):
            try:
                path2 = next(nx.all_simple_paths(G, source=source_nodes[i], target=sink_nodes[j]))

            except Exception as e:
                path2 = None

            if path2 is not None:
                everything_has_a_path +=1
                break
    if everything_has_a_path == len(source_nodes):
        return True
    else:
        return False


def create_graph_from_source(edgelist, nodeattributes):
    G = nx.DiGraph()
    df = pd.read_csv(edgelist)
    df2 = pd.read_csv(nodeattributes)

    #add nodes
    print(df2)
    print(df)
    for index, row in df2.iterrows():

        G.add_node(row['Node'], employee=row['Employee'])
    #add edges
    for index, row in df.iterrows():
        G.add_edge(row['Source'], row['Target'])

    print(G.nodes)

    return G

#This function generates the random graph.
def create_random_graph(num_nodes, seed, trophic_incoherence, scenario, probability):
    printing_graphs = False #if the graphs that are being generated have to be printed at every change step
    t0 = time.time()
    new_num_nodes = num_nodes
    used_seed = seed
    prob = probability
    q = trophic_incoherence

    while True:
        G = nx.fast_gnp_random_graph(new_num_nodes, p = prob, seed=used_seed, directed=True)
        # if the graph is empty, has not enough nodes, is not weakly connected or has too many sink+source: PASS
        if not nx.is_empty(G):
            if printing_graphs:
                draw_graph(G, '(1) Before connecting loose nodes', scenario)
            #CONNECT all loose nodes randomly
            # this creates basically sinks, it will be fixed in the next step
            isolates = list(nx.isolates(G))
            while len(list(nx.isolates(G))) != 0:
                rand_isolate = np.random.choice(isolates)
                isolates.remove(rand_isolate)
                rand_node = np.random.choice(G.nodes())

                while rand_isolate == rand_node:
                    rand_node = np.random.choice(G.nodes)
                G.add_edge(rand_node, rand_isolate)

            #make sure it is ONE BIG weakly connected component
            if printing_graphs:
                draw_graph(G, '(2) After connecting loose nodes', scenario)

            #check if somethin gis not weakly connected
            #then repair
            if not nx.is_weakly_connected(G):

                weakly_connect_list = list(nx.weakly_connected_components(G))
                for j in range(len(weakly_connect_list)):
                    temp_set = weakly_connect_list[j]
                    rand_node_set = np.random.choice(tuple(temp_set))
                    rand_node = np.random.choice(G.nodes())

                    while rand_node_set == rand_node or rand_node in temp_set:
                        rand_node = np.random.choice(G.nodes)
                    #adding edge:
                    if 0.5 > random.uniform(0.0, 1.0):
                        G.add_edge(rand_node, rand_node_set)
                    else:
                        G.add_edge(rand_node_set, rand_node)



            # CHECK number of source and sink
            #CECK if source > 15% of all nodes, if so connect the remaining nodes

            sink_nodes, source_nodes = count_sink_source_nodes(G)
            if printing_graphs:
                draw_graph(G, '(3) After connecting loose components', scenario)

            while len(source_nodes)/len(G.nodes) >= 0.15:
                rand_source = np.random.choice(source_nodes)
                source_nodes.remove(rand_source)
                rand_node = np.random.choice(source_nodes)
                G.add_edge(rand_node, rand_source)
            if printing_graphs:
                draw_graph(G, '(4) After connecting source nodes', scenario)

            # CECK if sink > 15% of all nodes, if so connect the remaining nodes
            while len(sink_nodes)/len(G.nodes) >= 0.15:
                rand_sink = np.random.choice(sink_nodes)
                sink_nodes.remove(rand_sink)
                rand_node = np.random.choice(sink_nodes)
                G.add_edge(rand_sink, rand_node)

            if printing_graphs:
                draw_graph(G, '(5) After connecting sink nodes', scenario)
            sink_nodes, source_nodes = count_sink_source_nodes(G)

            try:
                trop = tropA.trophic_incoherence_parameter(G)
                print('The found trop = ', trop, 'with p: ', prob)
                if ((q - 0.1) <= trop <= (q + 0.1)):
                    print('Trop was alright!, ', trop)
                    if nx.is_weakly_connected(G):
                        if check_if_source_connected_to_one_sink(G):
                            break
                        else:
                            continue
            except Exception as e:
                #raw_graph(G, 'No basal nodes', scenario)
                print('An error occured: ', e)

        used_seed = used_seed + 1

    print('found network at iteration: ', '. It  took ', t0-time.time(), ' seconds')
    draw_graph(G, 'Final network', scenario)
    return G, used_seed, prob