import sys
import pandas as pd
import numpy as np
from shutil import copyfile
from datetime import datetime,timedelta

input_files = {}

if len(sys.argv) > 1:
    
    input_files['model_data'] = sys.argv[1]
    print("Model-Data-File: %s"%input_files['model_data'])
    
    input_files['unit'] = sys.argv[2]
    print("Unit-Data-File: %s"%input_files['unit'] )
    
    input_files['time_series'] = sys.argv[3]
    print("Time-Series-File: %s"%input_files['time_series'])
    
    # Output Files
    output_files = {'time_series':"time_series_spine.csv",
                    'model_data':'model_data_spine.xlsx'}

# sys.argv[1] is empty if script is not called from Spine
else:

    input_files['model_data'] = "model_data.xlsx"
    input_files['unit'] = "unit_parameters.csv"
    input_files['time_series'] = "time_series.csv"

    # Output Files
    output_files = {'time_series':'manuel/time_series_spine.csv',
                    'model_data':'manuel/model_data_spine.xlsx'}



def convert_model_data(input_files,output_files):
    # Read Time series values
    time_series = pd.read_csv(input_files['time_series'],sep=";",header=0,index_col=None)
    
    # times = time_series['Time'].tolist()
    power_load_raw = time_series['Load'].to_numpy()
    heat_load_raw = time_series['Heat'].to_numpy()
    wind_power_raw = time_series['Wind'].to_numpy()
    
    
    # Read unit capacities
    units = pd.read_csv(input_files['unit'],sep=";",header=0,index_col=0)
    max_powers = units['power_max'].to_numpy()
    power_cap = sum(max_powers[~np.isnan(max_powers)])
    heat_cap = sum(g['heat_max'] for idx,g in units.iterrows())

    print(power_cap)
    print('Power Capacity:\t%.2f MW_el'%power_cap)
    print('Heat Capacity:\t%.2f MW_th'%heat_cap)



    # Read model data parameter
    model_data = pd.read_excel(input_files['model_data'], sheet_name='model')
    storage_data = pd.read_excel(input_files['model_data'], sheet_name='storage')
    cost_data = pd.read_excel(input_files['model_data'], sheet_name='costs')
    
    t_max =             int(model_data['t_max'])
    power_load_max =    float(model_data['power_load_max'])
    heat_load_max =     float(model_data['heat_load_max'])
    wind_supply =       float(model_data['wind_supply'])
    
    print('Time Steps: \t%i'%t_max)
    t_end = min(t_max+1,len(time_series))

    # Create times
    start_date = model_data['start_date'].to_list()
    date = start_date[0].to_pydatetime()
    times = [date]
    for ii in range(1,t_end):
        date += timedelta(hours=1)
        times.append(date)

    time_start = times[0]
    time_end = times[-1]
    print('Time Start:\t%s'%time_start)
    print('Time End: \t%s'%time_end)


    # Find inital state of units
    units_on = pd.DataFrame()

    units_before = []
    times_before = []
    values_before = []
    for idx,g in units.iterrows():
        t_before_end = max(g['t_down_0'],g['t_up_0'])
        atime = time_start
        for ii in range(1,t_before_end):
            atime = atime-timedelta(hours=1)
            units_before.append(g['name'])
            times_before.append(atime)
            if g['t_up_0'] == 0: # unit was down
                values_before.append(0)
            else: #unit was up
                values_before.append(1)

    units_on['Unit'] = units_before
    units_on['Time'] = times_before
    units_on['Status'] = values_before

    #Save start time-1 in storage
    storage_data['t-1'] = [start_date[0] -timedelta(hours=1)]

    # Normalize power load time series
    power_load_norm = power_load_raw/max(power_load_raw)
    max_load = power_load_max/100*power_cap
    power_load = max_load*power_load_norm

    # Normalize heat load time series
    heat_load_norm = heat_load_raw/max(heat_load_raw)
    max_load = heat_load_max/100*heat_cap
    heat_load = max_load*heat_load_norm

    # Taking only part untill t_end
    power_load = power_load[0:t_end-1]
    heat_load = heat_load[0:t_end-1]
    wind_power_raw = wind_power_raw[0:t_end-1]
    print(sum(wind_power_raw))

    # Normalize wind time series
    wind_power_norm = wind_power_raw/sum(wind_power_raw)
    wind_annual = wind_supply/100*sum(power_load)
    wind_power = wind_annual*wind_power_norm
    
    # Save time series in dataframe
    time_series_out = pd.DataFrame()
    time_series_out['Time'] = times[0:-1]
    time_series_out['Load'] = power_load
    time_series_out['Heat'] = heat_load
    time_series_out['Wind'] = wind_power

    # Set new model parameters
    spine_parameter = pd.DataFrame()
    spine_parameter['time_start'] = [time_start]
    spine_parameter['time_end'] = [time_end]

    #Save output files ---------------------------------------------------------------------
    
    time_series_out.to_csv(output_files['time_series'],sep=";",index=False)

    with pd.ExcelWriter(output_files['model_data']) as writer:  
        storage_data.to_excel(writer, sheet_name='storage',index=False)
        model_data.to_excel(writer, sheet_name='model',index=False)
        cost_data.to_excel(writer, sheet_name='costs',index=False)
        spine_parameter.to_excel(writer, sheet_name='spine_parameter',index=False)
        units_on.to_excel(writer, sheet_name='units_on',index=False)
    
    print("\nModel Parameter Convertion successfull! \n")



convert_model_data(input_files,
                   output_files)