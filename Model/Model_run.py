from Model import InformationFlowModel
import random
import pandas as pd
import time
from datetime import datetime
import Networks as net

# run time 1 x 24 hours; 1 tick 1 minute
now = datetime.now()
date = now.strftime("_date_%Y-%m-%d %H-%M-%S")
random_modelling = False #random data or from files

#basic paramters for model

run_lenght = 28 * 8 * 60
file_edgelist = '../Data/updated-graph-edges.csv'
file_nodeattr = '../Data/node_data.csv'

#set scenarios
file_scenarios = '../Data/Scenarios - N150 priority experiments.csv'
scenarios_df = pd.read_csv(file_scenarios, delimiter=';', na_values='-')
num_scenarios = 9 #number of scenarios in the scenario file
iterations = 1 #number of runs per scenario

random.seed(2)
seed = random.randint(1, 1000000000) #generate initial seed, might be changed by network function

#create empty dataframes
df_networks = pd.DataFrame(columns=['scenario','iteration','num_nodes', 'num_edges', 'sink_nodes', 'source_nodes','avg_in_degree',
                                    'avg_out_degree', 'density', 'trophic_incoherence_parameter' ,'average_shortest_path',
                                    'auto', 'non_auto', 'controller', 'collector', 'seed'])
df_business = pd.DataFrame(columns=['Scenario', 'Iteration','step','EmployeeID','business' ])
df_employee = pd.DataFrame(columns=['Scenario', 'Iteration','EmployeeID', 'InfoPackProc'])
df_controll = pd.DataFrame(columns=['Scenario', 'Iteration','EmpID', 'InfoID', 'dataLen', 'mistakes', 'repairs'])
df_infopack = pd.DataFrame(columns=['Scenario', 'Iteration','InfoID', 'generatedAt', 'removedAt', 'generatedBy', 'removedBy', 'EmployeesVisited'])
df_infodata = pd.DataFrame(columns=['Scenario', 'Iteration','InfoID', 'original', 'current', 'error_percentage'])

#This functions takes the results from a model run and stores them in a csv. It adds them to the bottom of an existing df
def store_data_in_csv(df = None, lists = None, data_name= None, headers = None, scenario = 1, iteration = 0):
    print("\nStoring ", data_name, "in a csv")
    df1 = df

    #some of the output is a lists of lists
    if isinstance(lists, list):
        df_temp = pd.DataFrame(lists)
        df_temp = df_temp.transpose()

    #some of the output is a dict
    else:
        df_temp = pd.DataFrame.from_dict(lists, orient='index')

    df_temp = df_temp.rename(columns=headers)

    df_temp.insert(0, 'Scenario', scenario)
    df_temp.insert(1, 'Iteration', iteration)
    df_modified = pd.concat([df1, df_temp])

    if data_name == 'employee_step_business':
        # df_temp = df_temp.rename(columns=headers)
        df_modified = df_modified[df_modified["EmployeeID"].str.contains("source") == False]
    print('head\n',df_modified.head())
    print('tail\n',df_modified.tail())
    return df_modified

row = 0 #variable is used to keep track to what df line of the network_stats file to add
for scenario in range(num_scenarios):
    t0 = time.time()
    for iteration in range(iterations):
        row+=1
        seed = random.randint(1, 1000000000)
        print('Running scenario: ', scenario + 1,' Running iteration: ', iteration)
        df = scenarios_df.loc[scenarios_df['Scenario'] == scenario + 1]
        df = df.drop('Scenario', axis=1)
        df = df.set_index('ID')

        num_nodes = df.loc['Network', 'nodes']
        tropic_coherence = df.loc['Network', 'tropic_coherence']
        cont_chance = df.loc['Network', 'collect_chance']
        sim_model = InformationFlowModel(seed=seed, debug=False, file_edge=file_edgelist, file_node_attributes=file_nodeattr,
                                         random_graph=random_modelling, scenarios_df=df, tropic_incoherence=tropic_coherence,
                                         num_nodes=int(num_nodes), controller_chance=cont_chance, scenario = scenario)

        for i in range(run_lenght):
            sim_model.step()
            print("MODEL STEP HAS BEEN TAKEN. WE ARE ON STEP: ", i)

        #storing data
        df_business = store_data_in_csv(df = df_business,lists=sim_model.employee_step_business, data_name="employee_step_business", headers= {0: 'step', 1:'EmployeeID', 2:'business'},scenario= scenario, iteration = iteration)
        df_employee = store_data_in_csv(df = df_employee,lists= sim_model.employee_data, data_name='employee_data', headers= {0: 'EmployeeID', 1: 'InfoPackProc'}, scenario=scenario, iteration = iteration)
        df_controll = store_data_in_csv(df = df_controll,lists= sim_model.controller_data, data_name='controller_data', headers= {0: 'EmpID', 1: 'InfoID', 2: 'dataLen', 3: 'mistakes', 4: 'repairs'}, scenario=scenario, iteration = iteration)
        df_infopack = store_data_in_csv(df = df_infopack,lists= sim_model.info_pack_travel_data, data_name='info_pack_travel_data', headers= {0: 'InfoID', 1: 'generatedAt', 2:'removedAt', 3: 'generatedBy', 4: 'removedBy', 5: 'EmployeesVisited'}, scenario=scenario, iteration = iteration)
        df_infodata = store_data_in_csv(df = df_infodata,lists= sim_model.info_pack_data_data, data_name='info_pack_data_data', headers= {0: 'InfoID', 1: 'original', 2: 'current', 3:'error_percentage'}, scenario=scenario, iteration = iteration)

        g = sim_model.G
        network_results = net.get_network_statistics(g)
        print('type: ' , type(network_results), network_results)
        #add to networks dataframe
        df_networks.loc[row] = [scenario] + [iteration] + list(network_results) + [sim_model.num_empl_auto] + \
                           [sim_model.num_empl_nonA] + [sim_model.num_empl_cont] + [sim_model.num_empl_coll] + [sim_model.seed]

    t1 = time.time()
    duration = t1-t0
    print("\nTime elapsed in scenario ", scenario,': ', duration,'seconds')

#saving the data to a csv file.
if random_modelling:
    df_business.to_csv("../results/"+ "random_modelled-employee_step_business" + date + ".csv", index = False)
    df_employee.to_csv("../results/"+ "random_modelled-employee_data" + date + ".csv", index = False)
    df_controll.to_csv("../results/"+ "random_modelled-controller_data" + date + ".csv", index = False)
    df_infopack.to_csv("../results/"+ "random_modelled-info_pack_travel_data" + date + ".csv", index = False)
    df_infodata.to_csv("../results/"+ "random_modelled-info_pack_data_data" + date + ".csv", index = False)
    df_networks.to_csv("../results/" + "random_modelled-df_networks" + date + ".csv", index=False)

else:
    df_business.to_csv("../results/data_modelled/employee_step_business" + date + ".csv", index = False)
    df_employee.to_csv("../results/data_modelled/employee_data" + date + ".csv", index = False)
    df_controll.to_csv("../results/data_modelled/controller_data" + date + ".csv", index = False)
    df_infopack.to_csv("../results/data_modelled/info_pack_travel_data" + date + ".csv", index = False)
    df_infodata.to_csv("../results/data_modelled/info_pack_data_data" + date + ".csv", index = False)
    df_networks.to_csv("../results/data_modelled/info_df_networks" + date + ".csv", index = False)
