"""This module imports fixed parameters from a CSV file and performs algebra on the m x 1 column matrices (along with
    input application parameters (power, discharge time) to generate a single list of coefficients describing the
    system cost. The calculation iterates over different discharge time inputs.
    Author: Diarmid Roberts.Date: 31st July 2017"""

# import off-the-shelf modules
import pandas as pd
import matplotlib.pyplot as plt
import itertools
import math

# import raw data
raw_data = pd.read_csv('RFB_technical_database_2019.csv')

# define application parameters
app_power = 50000                                      # in kW
discharge_time = [1, 2, 4, 6, 8, 16]              # in h

# define variables assigned to slices(saving space and confusion in battery builder formulae)
sl = raw_data.ix  # shorthand for pandas indexed sliced notation

include = sl[:, 'include']  # this column in the CSV file determines whether the row is included in output

system = sl[:, 'system']

current_density = sl[:, 'current_density']
eff_sys_d = sl[:, 'eff_sys_d']
eff_coul_RT = sl[:, 'eff_coul_RT']
working_V = sl[:, 'working_V_50%_SOC']
dSOC_per_pass = sl[:, 'dSOC_per_pass']
SOC_frac = sl[:, 'SOC_frac']
min_SOC = sl[:, 'min_SOC']

an_conc = sl[:, 'an_conc']
an_Ne = sl[:, 'an_Ne']
an_stoich = sl[:, 'an_stoich']
an_CI_conc = sl[:, 'an_CI_conc']

cath_conc = sl[:, 'cath_conc']
cath_Ne = sl[:, 'cath_Ne']
cath_stoich = sl[:, 'cath_stoich']
cath_CI_conc = sl[:, 'cath_CI_conc']

an_AS_molar_cost = sl[:, 'an_AS_molar_cost']
an_CI_molar_cost = sl[:, 'an_CI_molar_cost']
an_storage_cost = sl[:, 'an_storage_cost']
cath_AS_molar_cost = sl[:, 'cath_AS_molar_cost']
cath_CI_molar_cost = sl[:, 'cath_CI_molar_cost']
cath_storage_cost = sl[:, 'cath_storage_cost']
bipol_plate_areal_cost = sl[:, 'bipol_plate_areal_cost']
electrode_areal_cost = sl[:, 'electrode_areal_cost']
memb_areal_cost = sl[:, 'memb_areal_cost']
other_areal_cost = sl[:, 'other_areal_cost']
flow_pump_cost = sl[:, 'flow_pump_cost']
base_pump_cost = sl[:, 'base_pump_cost']
weber_pump_cost = sl[:,'weber_pump_cost']
HEX_cost = sl[:, 'HEX_cost']

results_array = pd.DataFrame()  # This initiates the data frame where a row of data will be dumped for each system

markers = itertools.cycle(('D', '.', 'o', '*', 'h', 's', 'v'))  # Sets up markers for plotter to cycle through

# This loop cycles through the different battery systems
for i in range(len(system)):
    if include[i] == 'y':  # only include the data selected in column one of the CSV file

        # Stack cost calculation (repeating unit = membrane + 2 electrode felts + bipolar plate)
        stack_area = app_power*1000/(current_density[i]*10*working_V[i]*eff_sys_d[i])  # in m2
        stack_cost = stack_area*(memb_areal_cost[i]+bipol_plate_areal_cost[i]
                                 + 2*electrode_areal_cost[i]+other_areal_cost[i])  # in $

        # Pump cost calculation (pump is sized to meet current demand at lower SOC boundary
        current = (stack_area*current_density[i]*10)                                  # Amperes
        an_C_per_L = (an_Ne[i]/an_stoich[i])*96485*an_conc[i]                         # L/coulomb
        max_an_flow = current*60/(an_C_per_L*min([min_SOC[i], dSOC_per_pass[i]])*math.sqrt(eff_coul_RT[i]))      # L/min
        cath_C_per_L = (cath_Ne[i]/cath_stoich[i])*96485*cath_conc[i]                         # L/coulomb
        max_cath_flow = current*60/(cath_C_per_L*min([min_SOC[i], dSOC_per_pass[i]])*math.sqrt(eff_coul_RT[i]))  # L/min

        pump_cost = (max_an_flow+max_cath_flow)*weber_pump_cost[i]

        hex_cost = HEX_cost[i] * app_power

        print("Stack Cost:", int(stack_cost/app_power), "$/kW", "Pump cost:", int(pump_cost/app_power), "$/kW")
        # The for loop below iterates the energy component calculations through the list "discharge_time"
        # and combines the results with power basis costs (which do not vary with discharge time) to give
        # a total cost for each discharge time.

        results_wrt_t = []        # This initiates the results wrt discharge time list to be filled by the loop below

        # For each battery system, this loop cycles through the discharge times and returns cost per kWh
        for t in range(len(discharge_time)):

            # Chemical inventory cost
            an_chem_moles = (current*discharge_time[t]*3600) / \
                        ((an_C_per_L/an_conc[i])*SOC_frac[i]*eff_coul_RT[i])
            an_chem_cost = an_chem_moles*an_AS_molar_cost[i]
            cath_chem_moles = (current * discharge_time[t]*3600) / \
                          ((cath_C_per_L/cath_conc[i]) * SOC_frac[i] * eff_coul_RT[i])
            cath_chem_cost = cath_chem_moles * cath_AS_molar_cost[i]
            an_CI_cost = (an_chem_cost/an_AS_molar_cost[i])*(an_CI_conc[i]/an_conc[i])*an_CI_molar_cost[i]
            cath_CI_cost = (cath_chem_cost/cath_AS_molar_cost[i])*(cath_CI_conc[i]/an_conc[i])*cath_CI_molar_cost[i]

            # Storage tank cost
            an_storage_vol = an_chem_moles/an_conc[i]
            cath_storage_vol = cath_chem_moles / cath_conc[i]
            vessel_cost = (an_storage_vol*an_storage_cost[i])+(cath_storage_vol*cath_storage_cost[i])

            # Total cost per kWh
            system_cost = stack_cost + pump_cost + hex_cost + cath_chem_cost \
                + cath_CI_cost + an_chem_cost + an_CI_cost + vessel_cost
            cost_per_kWh = [system_cost/(current*working_V[i] *
                                        eff_sys_d[i]*discharge_time[t]/1000)]  # Square brackets allow list ops

            results_wrt_t = results_wrt_t + cost_per_kWh  # Adds new entry to list

        plt.plot(discharge_time, results_wrt_t, marker=next(markers),
                 markersize=8, label=system[i])  # generate graph data series for each system.
        # The following two lines collate the loop output in DataFrame format
        int_results_wrt_t = pd.DataFrame([[int(x) for x in results_wrt_t]])  # Outer square brackets return m = 1 array
        results_array = pd.concat([results_array, int_results_wrt_t])

    else:
        continue

# Output in tabular form
print(results_array)

# NMC LIB materials cost 2014, from 2016 Clean Energy Manufacturing centre

NMC = ['180' for x in discharge_time[2:]]
plt.plot(discharge_time[2:], NMC, label='Li-ion (NMC) 2014 NREL', color='k', linestyle="--")

# Output in graphic form
plt.xlabel('System specification, Energy/Power (h)')
plt.ylabel('System component cost ($.kWh-1)')
axes = plt.gca()
axes.set_ylim([0, 700])
plt.legend()
plt.show()
