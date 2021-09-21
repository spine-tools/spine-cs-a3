import sys
import os
import pandas as pd
from datetime import datetime

if len(sys.argv) > 1:
    
    input_file_results = sys.argv[1]
    input_file_units = sys.argv[2]
    input_file_series = sys.argv[3]

    now = datetime.now()
    root_folder = '..\..\Solution'
    if not os.path.exists(root_folder):
        os.mkdir(root_folder)
        print("New Folder:", root_folder)
    root_folder = "%s\SpineModel"%root_folder
    if not os.path.exists(root_folder):
        os.mkdir(root_folder)
        print("New Folder:", root_folder)
    new_folder = "%s\Solution_%s-%s-%s-H%s"%(root_folder,now.year,now.month,now.day,now.hour)
    if not os.path.exists(new_folder):
        os.mkdir(new_folder)
        print("New Folder:", new_folder)
    output_folder = new_folder

# sys.argv[1] is empty if script is not called from Spine
else:

    input_file_results = "manuel/results.xlsx"
    input_file_units = "unit_parameters.csv"
    input_file_series = "input_series.xlsx"
    output_folder = 'solution'


''' Read Files '''
flow_to_node = pd.read_excel(input_file_results, sheet_name='to_node')
flow_from_node = pd.read_excel(input_file_results, sheet_name='from_node')
units_on = pd.read_excel(input_file_results, sheet_name='units_on')
start_up = pd.read_excel(input_file_results, sheet_name='start_up')
shut_down = pd.read_excel(input_file_results, sheet_name='shut_down')
storage = pd.read_excel(input_file_results, sheet_name='storage')
slack = pd.read_excel(input_file_results, sheet_name='slack')

units = pd.read_csv(input_file_units,sep=";",header=0,index_col=0)

wind_serie = pd.read_excel(input_file_series, sheet_name='wind')
heat_load_serie = pd.read_excel(input_file_series, sheet_name='heat_load')
el_load_serie = pd.read_excel(input_file_series, sheet_name='el_load')



''' Only takes the last exported Datas '''

def latest_datas(frame):
    alternatives = frame['Alternative'].unique()
    dates_alt = []
    for a in alternatives: 
        # date_string = a.replace('Run SpineOpt 1@','')
        date = datetime.strptime(a, 'Run SpineOpt 1@%Y-%m-%dT%H:%M:%S')
        dates_alt.append(date)

    # Find youngest alternative
    max_date = max(dates_alt)
    max_date_idx = dates_alt.index(max_date)
    max_alt = alternatives[max_date_idx]

    frame = frame[frame['Alternative']==max_alt]
    return frame

flow_to_node = latest_datas(flow_to_node)
flow_from_node = latest_datas(flow_from_node)
units_on = latest_datas(units_on)
storage = latest_datas(storage)
slack = latest_datas(slack)

''' Get time series '''
times = flow_to_node['Time'].apply(lambda x: x.replace('T',' ')).unique()
# times = times.to_list()


''' Find input time series '''
wind_power = wind_serie['Value'].to_list()[0:len(times)]
heat_load = heat_load_serie['Value'].to_list()[0:len(times)]
el_load = el_load_serie['Value'].to_list()[0:len(times)]



''' Convert Storage '''
heat_storage = storage['Value'].to_list()
heat_storage_diff = [0] + [heat_storage[n]-heat_storage[n-1] for n in range(1,len(heat_storage))]
heat_loss = [h*0.02 for h in heat_storage]

''' Convert Units On '''
head_uc = units_on.drop(columns=['Alternative','Time','Value'])
head_uc = head_uc.drop_duplicates()
head_uc = head_uc.sort_values(by=['Unit'])

sol_uc = pd.DataFrame();   sol_uc['Time'] = times

for idx,row in head_uc.iterrows():
    unit = str(row['Unit'])
    
    # Get Values
    part = units_on[units_on['Unit'] == unit]
    values = part['Value'].to_list()
    
    sol_uc[unit] = values


''' Convert start up '''
head_su = start_up.drop(columns=['Alternative','Time','Value'])
head_su = head_su.drop_duplicates()
head_su = head_su.sort_values(by=['Unit'])

sol_start = pd.DataFrame();   sol_uc['Time'] = times

for idx,row in head_su.iterrows():
    unit = str(row['Unit'])
    
    # Get Values
    part = start_up[start_up['Unit'] == unit]
    values = part['Value'].to_list()
    
    sol_start[unit] = values



''' Convert start up '''
head_stop = shut_down.drop(columns=['Alternative','Time','Value'])
head_stop = head_stop.drop_duplicates()
head_stop = head_stop.sort_values(by=['Unit'])

sol_stop = pd.DataFrame();   sol_uc['Time'] = times

for idx,row in head_stop.iterrows():
    unit = str(row['Unit'])
    
    # Get Values
    part = shut_down[shut_down['Unit'] == unit]
    values = part['Value'].to_list()
    
    sol_stop[unit] = values




''' Inizialize output Frames'''
sol_heat_single = pd.DataFrame();   sol_heat_single['Time'] = times
sol_power_single = pd.DataFrame();  sol_power_single['Time'] = times
sol_fuel_single = pd.DataFrame();   sol_fuel_single['Time'] = times


''' Convert to-node flow '''
print("\nFlow to-node:")
head_to = flow_to_node.drop(columns=['Alternative','Time','Value'])
head_to = head_to.drop_duplicates()
head_to = head_to.sort_values(by=['Unit'])
print(head_to)


#Aggregated Units
x = {}
x['BP_CHP','heat']  = [0]*len(times);     x['BP_CHP','electricity'] = [0]*len(times)
x['BP_HB','heat']   = [0]*len(times)
x['EC','heat']      = [0]*len(times);     x['EC','electricity'] = [0]*len(times)
x['GT','heat']      = [0]*len(times);     x['GT','electricity'] = [0]*len(times)
x['HB','heat']      = [0]*len(times)         
x['EB','heat']      = [0]*len(times)
x['HP','heat']      = [0]*len(times)
x['wind_use','electricity'] = [0]*len(times) 

for idx,row in head_to.iterrows():
    unit = str(row['Unit'])
    node = str(row['Node'])
    if '_CHPmode' in unit:
        unit_type = 'BP_CHP'
    elif '_HBmode' in unit:
        unit_type = 'BP_HB'
    elif unit == 'wind':
        unit_type = 'wind_use'
    else:
        unit_type_list = units[units['name']=='%s'%unit]['type'].to_list()
        unit_type  = unit_type_list[0]
    
    # Get Values
    part = flow_to_node[flow_to_node['Unit'] == unit]
    part = part[part['Node'] == node]
    values = part['Value'].to_list()
    
    # Save single
    if node == 'heat':
        sol_heat_single[unit] = values
    elif node == 'electricity':
        sol_power_single[unit] = values
    else:
        print("Unexpected to-node flow: %s"%node)

    # Save aggregated
    x[unit_type,node] = [x + y for x, y in zip(x[unit_type,node], values)]



''' Convert from-node flow '''
print("\nFlow from-node:")
head_from = flow_from_node.drop(columns=['Alternative','Time','Value'])
head_from = head_from.drop_duplicates()
head_from = head_from.sort_values(by=['Unit'])
print(head_from)

x['EB','electricity'] = [0]*len(times)
x['HP','electricity'] = [0]*len(times)

for idx,row in head_from.iterrows():
    unit = str(row['Unit'])
    node = str(row['Node'])
    if node == 'electricity':
        unit_type_list = units[units['name']=='%s'%unit]['type'].to_list()
        unit_type  = unit_type_list[0]
    
        # Get Values
        part = flow_from_node[flow_from_node['Unit'] == unit]
        part = part[part['Node'] == node]
        values = part['Value'].to_list() 
        
        values = [-1*x for x in values]  # -1 because consumption
        
        # Save single
        sol_power_single[unit] = values

        # Save aggregated
        x[unit_type,node] = [x + y for x, y in zip(x[unit_type,node], values)]

    else:
        # Get Values
        part = flow_from_node[flow_from_node['Unit'] == unit]
        part = part[part['Node'] == node]
        values = part['Value'].to_list()

        sol_fuel_single[unit] = values


''' Convert Slack '''
neg = slack[slack["Parameter"]=="node_slack_neg"] 
neg_el      = neg[neg["Node"]=="electricity"]
neg_heat    = neg[neg["Node"]=="heat"]
pos         = slack[slack["Parameter"]=="node_slack_pos"] 
pos_el      = pos[pos["Node"]=="electricity"]
pos_heat    = pos[pos["Node"]=="heat"]

slack_el = [x-y for x,y in zip(pos_el["Value"], neg_el["Value"])]
slack_heat = [x-y for x,y in zip(pos_heat["Value"], neg_heat["Value"])]
    




''' Save aggregations '''
# Power
sol_power = pd.DataFrame()
sol_power['Time'] = times             
sol_power['power_load'] = el_load     
sol_power['power_load_shed'] = slack_el
# sol_power['self'] = Res_self
sol_power['wind'] = wind_power
sol_power['wind_use']   = x['wind_use','electricity']    
sol_power['wind_spil']  = [-(x - y) for x, y in zip(wind_power, x['wind_use','electricity'])]
sol_power['BP']         = x['BP_CHP','electricity']        
sol_power['EC']         = x['EC','electricity']                 
sol_power['GT']         = x['GT','electricity']                 
sol_power['EB']         = x['EB','electricity']                 
sol_power['HP']         = x['HP','electricity']             

# Heat
sol_heat = pd.DataFrame()
sol_heat['Time'] = times
sol_heat['storage'] = heat_storage
sol_heat['delta_storage'] = heat_storage_diff
sol_heat['heat_loss'] = heat_loss
sol_heat['heat_load'] = heat_load
sol_heat['heat_load_shed'] = slack_heat
# sol_heat['heat_loss'] = Res_heat_loss
sol_heat['BP'] = [x + y for x, y in zip(x['BP_CHP','heat'], x['BP_HB','heat'])]
sol_heat['BP_CHP'] = x['BP_CHP','heat']
sol_heat['BP_HB'] = x['BP_HB','heat']
sol_heat['EC'] = x['EC','heat']
sol_heat['GT'] = x['GT','heat']
sol_heat['HB'] = x['HB','heat']
sol_heat['EB'] = x['EB','heat']
sol_heat['HP'] = x['HP','heat']



''' Export Results '''
sol_power_single.to_csv('%s/sol_power_single.csv'%output_folder,sep=';',index=False)
sol_heat_single.to_csv('%s/sol_heat_single.csv'%output_folder,sep=';',index=False)
sol_fuel_single.to_csv('%s/sol_fuel_single.csv'%output_folder,sep=';',index=False)
sol_power.to_csv('%s/sol_power.csv'%output_folder,sep=';',index=False)
sol_heat.to_csv('%s/sol_heat.csv'%output_folder,sep=';',index=False)
sol_uc.to_csv('%s/sol_unit_commitment.csv'%output_folder,sep=';',index=False)
sol_start.to_csv('%s/sol_start_up.csv'%output_folder,sep=';',index=False)
sol_stop.to_csv('%s/sol_shut_down.csv'%output_folder,sep=';',index=False)

print('\nResult Conversion successfully!')
print('Saved in: %s'%output_folder)




