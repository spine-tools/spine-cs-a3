import sys
import pandas as pd
from openpyxl import load_workbook, Workbook

# Parameter to make the ramping constraints binding
use_ramp = 0.05

pd.options.mode.chained_assignment = None  # default='warn'

if len(sys.argv) > 1:

    input_filepath = sys.argv[1]
    print("Input-File: %s"%input_filepath)

    output_filepath = "unit_parameters_spine.xlsx"

# sys.argv[1] is empty if script is not called from Spine
else:
    input_filepath = "unit_parameters.csv"
    output_filepath = "manuel/unit_parameters_spine.xlsx"


def convert_units(input_file,output_file):
    units = pd.read_csv(input_filepath,sep=";",header=0,index_col=0)

    units['power_min_percent'] = units['power_min']/units['power_max']
    units['heat_min_percent'] = units['heat_min']/units['heat_max']
    units['ramp_up_percentage'] = 60*units['ramp_up']/units['power_max']*use_ramp
    units['ramp_down_percentage'] = 60*units['ramp_down']/units['power_max']*use_ramp
    t_up_durations = []
    t_down_durations = []
    for idx,g in units.iterrows():
        t_up_durations.append('%ih'%g['t_up'])
        t_down_durations.append('%ih'%g['t_down'] )
    units['t_up_duration'] = t_up_durations
    units['t_down_duration'] = t_down_durations


    # Distribute the units in their different technologies

    # Back presure Turbines
    BP = units[units['type']=='BP']
    names_chp_mode = []
    names_hb_mode = []
    names_mode_comm = []
    names_start_comm = []
    for idx,g in BP.iterrows():
        names_hb_mode.append('%s_HBmode'%g['name'])
        names_chp_mode.append('%s_CHPmode'%g['name'])
        names_mode_comm.append('%s_uc_mode'%g['name'])
        names_start_comm.append('%s_uc_start'%g['name'])
    BP['name_HB_mode'] = names_hb_mode
    BP['name_CHP_mode'] = names_chp_mode
    BP['name_mode_commitment'] = names_mode_comm
    BP['name_start_commitment'] = names_start_comm

    # Extraction condensing steam turbine
    EC = units[units['type']=='EC']
    # -1 because it appears on the left side of the constraint
    EC['pmax*fuel_cons_el'] = -1*EC['power_max']*EC['fuel_cons_el']
    EC['pmin*fuel_cons_el'] = -1*EC['power_min']*EC['fuel_cons_el']
    
    names_complex_relation_max = []
    names_complex_relation_min = []
    names_fuel_heat = []
    names_fuel_el = []
    for idx,g in EC.iterrows(): 
        names_complex_relation_max.append('cplx_realtion_max_%s'%g['name'])
        names_complex_relation_min.append('cplx_realtion_min_%s'%g['name'])
        names_fuel_heat.append('%s_heat'%g['fuel'])
        names_fuel_el.append('%s_el'%g['fuel'])
    EC['name_cplx_relation_max'] = names_complex_relation_max
    EC['name_cplx_relation_min'] = names_complex_relation_min

    EC['fuel_cons_el/efficiency'] = EC['fuel_cons_el']/EC['efficiency']
    EC['fuel_cons_th/efficiency'] = EC['fuel_cons_th']/EC['efficiency']
    
    EC['fuel_heat'] = names_fuel_heat
    EC['fuel_el'] = names_fuel_el

    # Gas turbine
    GT = units[units['type']=='GT']

    gt_fuel_power_ratio = 1/GT['efficiency']*(GT['el_th_ratio']+1)/GT['el_th_ratio']
    GT['fuel_power_ratio'] = gt_fuel_power_ratio

    # Heat only boiler
    HB = units[units['type']=='HB'] 

    # Electric boiler
    EB = units[units['type']=='EB']

    # Heat pump
    HP = units[units['type']=='HP']

    print('Found %i Back Pressure Turbines'%len(BP))
    print('Found %i Extraction Turbines'%len(EC))
    print('Found %i Gas Turbines'%len(GT))
    print('Found %i Heat only Boilers'%len(HB))
    print('Found %i Electric Boilers'%len(EB))
    print('Found %i Heat Pumps'%len(HP))


    # Save the different unit as sheets in the output file
    with pd.ExcelWriter(output_file) as writer:  
        BP.to_excel(writer,sheet_name="BP")
        EC.to_excel(writer,sheet_name="EC")
        GT.to_excel(writer,sheet_name="GT")
        HB.to_excel(writer,sheet_name="HB")
        EB.to_excel(writer,sheet_name="EB")
        HP.to_excel(writer,sheet_name="HP")

    print("\nUnit Parameter Convertion successfull! \n")


convert_units(input_filepath,output_filepath)
